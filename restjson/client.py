import requests
import ujson as json
import pprint

from requests import compat, models     # noqa
compat.json = json                      # noqa
models.complexjson = json               # noqa

from restjson.cache import MemoryCache, cache_key


class objdict(dict):
    def __getattr__(self, name):
        if name in self:
            return self[name]
        raise AttributeError(name)

    def __setattr__(self, name, value):
        self[name] = value

    def __delattr__(self, name):
        if name in self:
            del self[name]

        raise AttributeError(name)


class ResourceError(Exception):
    def __init__(self, code, errors=None, msg=''):
        super(ResourceError, self).__init__(msg)
        self.msg = msg
        self.errors = errors is not None and errors or {}
        self.code = code

    def __str__(self):
        display = ['ResourceError', 'HTTP Status %d' % self.code]
        errors = pprint.pformat(self.errors)
        display += errors.split('\n')
        display.append(self.msg)
        return '\n'.join(display)


class Client(object):
    def __init__(self, endpoint):
        self.endpoint = endpoint
        self.session = requests.Session()
        headers = {'Content-Type': 'application/vnd.api+json'}
        self.session.headers.update(headers)
        self.cache = MemoryCache()
        self._models = None

    @property
    def models(self):
        if self._models is None:
            self._models = self._get('')['models']
        return self._models

    def _get_model(self, name):
        for model in self.models:
            if model['name'] == name:
                return model
        raise KeyError(name)

    def _get_relations(self, collection):
        return self._get_model(collection)['relationships'].keys()

    def _get_relation_target(self, collection, relation_name):
        relations = self._get_model(collection)['relationships']
        return relations[relation_name]['target']

    def _delete(self, collection, entry_id):
        url = self.endpoint + collection + '/%d' % entry_id
        key = cache_key(url)
        if key in self.cache:
            headers = {'If-Match': self.cache[key][0]}
        else:
            headers = {}

        resp = self.session.delete(url, headers=headers)

        if resp.status_code > 399:
            raise ResourceError(resp.status_code, resp.content)
        return resp

    def _get(self, resource, params=None):
        headers = {}
        key = cache_key(self.endpoint + resource, params)
        if key in self.cache:
            etag, cached = self.cache[key]
            headers['If-None-Match'] = etag

        resp = self.session.get(self.endpoint + resource, params=params,
                                headers=headers)

        if resp.status_code == 304:
            return self.cache[key][1]

        if resp.status_code > 399:
            raise ResourceError(resp.status_code, resp.content)

        data = objdict(resp.json())

        if 'Etag' in resp.headers:
            self.cache[key] = resp.headers['Etag'], data

        return data

    def _post(self, collection, data):
        return self._modify(collection, data, method='POST')

    def _patch(self, collection, entry_id, data):
        return self._modify(collection, data, method='PATCH',
                            entry_id=entry_id)

    def _patch_relation(self, collection, entry_id, relation_name, data):
        return self._modify_relation(collection, entry_id, relation_name,
                                     data, method='PATCH')

    def delete_relation(self, collection, entry_id, relation_name, data):
        url = self.endpoint + collection + '/%d/relationships/%s'
        url = url % (entry_id, relation_name)
        key = cache_key(url)
        if key in self.cache:
            headers = {'If-Match': self.cache[key][0]}
        else:
            headers = {}

        target = self._get_relation_target(collection, relation_name)
        for item in data:
            if 'type' not in item:
                item['type'] = target

        req_data = {'data': data, 'type': collection}
        resp = self.session.delete(url, data=json.dumps(req_data),
                                   headers=headers)

        if resp.status_code > 399:
            raise ResourceError(resp.status_code, resp.content)

        # invalidate the entry cache if any
        # XXX we shoud propagate on the server the last_modified field
        # of the entry instead of doing this here
        entry_url = self.endpoint + collection + '/%s' % str(entry_id)
        key = cache_key(entry_url)
        if key in self.cache:
            del self.cache[key]

        return resp

    def _modify_relation(self, collection, entry_id, relation_name, data,
                         method='PATCH'):
        url = self.endpoint + collection + '/%s/relationships/%s'
        url = url % (str(entry_id), relation_name)

        target = self._get_relation_target(collection, relation_name)
        for item in data:
            if 'type' not in item:
                item['type'] = target

        req_data = data
        key = cache_key(url)

        if key in self.cache:
            headers = {'If-Match': self.cache[key][0]}
        else:
            headers = {}

        req_method = getattr(self.session, method.lower())
        req_data = {'data': req_data}
        res = req_method(url, data=json.dumps(req_data), headers=headers)

        if res.status_code == 204:
            # the data was modified as expected
            pass
        else:
            # unexpected result
            try:
                data = res.json()
            except ValueError:
                data = {'errors': [res.content]}

            raise ResourceError(res.status_code,
                                errors=data.get('errors'))

        if 'Etag' in res.headers:
            if 'last_modified' in data:
                data['last_modified'] = res.headers['Etag']
            self.cache[key] = res.headers['Etag'], data

        # invalidate the entry cache if any
        # XXX we shoud propagate on the server the last_modified field
        # of the entry instead of doing this here
        entry_url = self.endpoint + collection + '/%s' % str(entry_id)
        key = cache_key(entry_url)
        if key in self.cache:
            del self.cache[key]

        return data

    def _modify(self, collection, data, method='POST', entry_id=None):
        # XXX modifying relationships - is that sane ?
        modify_relations = []
        if entry_id is not None:
            relations = self._get_relations(collection)
            for field in list(data.keys()):
                if field not in relations:
                    continue
                # XXX what about one-one
                rel_data = data.pop(field)
                if not isinstance(rel_data, list):
                    continue
                modify_relations.append((field, rel_data))

        req_data = {'attributes': data, 'type': collection}

        if entry_id is not None:
            url = self.endpoint + collection + '/%s' % str(entry_id)
        else:
            url = self.endpoint + collection

        if 'id' in data:
            req_data['id'] = str(data['id'])

        key = cache_key(url)
        if key in self.cache:
            headers = {'If-Match': self.cache[key][0]}
        else:
            headers = {}

        req_method = getattr(self.session, method.lower())
        req_data = {'data': req_data}
        res = req_method(url, data=json.dumps(req_data), headers=headers)

        if res.status_code == 204:
            # the data was modified as expected
            pass
        elif res.status_code in (200, 201):
            # the data was changed by the server as well
            data = res.json()['data']
            data = objdict(data)
        else:
            # unexpected result
            try:
                data = res.json()
            except ValueError:
                data = {'errors': [res.content]}

            raise ResourceError(res.status_code,
                                errors=data.get('errors'))

        # XXX modifying relationships - is that sane ?
        for rel_name, rel_data in modify_relations:
            self._modify_relation(collection, entry_id, rel_name,
                                  rel_data, method=method)

        if 'Etag' in res.headers:
            if 'last_modified' in data:
                data['last_modified'] = res.headers['Etag']
            self.cache[key] = res.headers['Etag'], data

        return data

    def get_entries(self, table, filters=None, sort=None):
        params = {}

        if filters is not None:
            params['filter[objects]'] = json.dumps(filters)

        params['limit'] = 99

        if sort is not None:
            params['sort'] = sort

        res = self._get(table, params=params)['data']
        return [objdict(ob) for ob in res]

    def create_entry(self, table, data):
        return self._post(table, data)

    def update_entry(self, table, data):
        # XXX what about tables that uses another name
        entry_id = data['id']
        return self._patch(table, entry_id, data)

    def delete_entry(self, table, entry_id):
        return self._delete(table, entry_id)

    def get_entry(self, table, entry_id):
        endpoint = table + '/%s' % str(entry_id)
        return objdict(self._get(endpoint)['data'])

    def update_relation(self, table, entry_id, relation_name, data):
        return self._patch_relation(table, entry_id, relation_name, data)

    def bust_cache(self, table, entry_id):
        url = self.endpoint + table + '/%d' % entry_id
        key = cache_key(url)
        if key in self.cache:
            del self.cache[key]
            return True
        return False
