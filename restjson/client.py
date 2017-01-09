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

    def _modify(self, collection, data, method='POST', entry_id=None):

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

        method = getattr(self.session, method.lower())
        req_data = {'data': req_data}
        res = method(url, data=json.dumps(req_data), headers=headers)

        if res.status_code == 204:
            # the data was modified as expected
            pass
        elif res.status_code in (200, 201):
            # the data was changed by the server as well
            data = res.json()['data']
            data = objdict(data)
        else:
            # unexpected result
            data = res.json()
            raise ResourceError(res.status_code,
                                errors=data.get('errors'))

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
        return self._get(endpoint)['data']
