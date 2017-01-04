import requests
import ujson as json

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
    def __init__(self, code, msg):
        self.code = code
        super(ResourceError, self).__init__(msg)


class Client(object):
    def __init__(self, endpoint):
        self.endpoint = endpoint
        self.session = requests.Session()
        headers = {'Content-Type': 'application/json'}
        self.session.headers.update(headers)
        self.cache = MemoryCache()

    def _delete(self, api, entry_id):
        url = self.endpoint + api + '/%d' % entry_id
        return self.session.delete(url)

    def _get(self, api, params=None):
        headers = {}
        key = cache_key(self.endpoint + api, params)
        if key in self.cache:
            etag, cached = self.cache[key]
            headers['If-None-Match'] = etag

        resp = self.session.get(self.endpoint + api, params=params,
                                headers=headers)

        if resp.status_code == 304:
            return self.cache[key][1]

        if resp.status_code > 399:
            raise ResourceError(resp.status_code, resp.content)

        data = objdict(resp.json())

        if 'Etag' in resp.headers:
            self.cache[key] = resp.headers['Etag'], data

        return data

    def _post(self, api, data):
        return self._modify(self.endpoint + api, data, expected=201,
                            method='POST')

    def _patch(self, api, entry_id, data):
        url = self.endpoint + api + '/%d' % entry_id
        return self._modify(url, data, expected=200, method='PATCH')

    def _modify(self, endpoint, data, expected=200, method='POST'):
        key = cache_key(endpoint)
        if key in self.cache:
            headers = {'If-Match': self.cache[key][0]}
        else:
            headers = {}

        method = getattr(self.session, method.lower())
        res = method(endpoint, data=json.dumps(data), headers=headers)

        if res.status_code != expected:
            raise ResourceError(res.status_code,
                                'Expected %d, got %d' % (expected,
                                                         res.status_code))

        data = objdict(res.json())

        if 'Etag' in res.headers:
            self.cache[key] = res.headers['Etag'], data

        return data

    def get_entries(self, table, filters=None, order_by=None):
        query = {}

        if filters is not None:
            query['filters'] = filters

        query['limit'] = 99
        if order_by is not None:
            query['order_by'] = [{'field': order_by}]

        params = {'q': json.dumps(query)}
        res = self._get(table, params=params)
        res['objects'] = [objdict(ob) for ob in res['objects']]
        return res

    def create_entry(self, table, data):
        res = self._post(table, data)
        return res.json()

    def update_entry(self, table, data):
        entry_id = data.pop('id')
        return self._patch(table, entry_id, data)

    def delete_entry(self, table, entry_id):
        return self._delete(table, entry_id)

    def get_entry(self, table, entry_id):
        endpoint = table + '/%s' % str(entry_id)
        return self._get(endpoint)
