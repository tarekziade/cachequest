import requests
import ujson as json

from requests import compat, models
compat.json = json
models.complexjson = json


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
    pass


class Client(object):
    def __init__(self, endpoint):
        self.endpoint = endpoint
        self.session = requests.Session()
        headers = {'Content-Type': 'application/json'}
        self.session.headers.update(headers)

    def _delete(self, api, entry_id):
        url = self.endpoint + api + '/%d' % entry_id
        return self.session.delete(url)

    def _get(self, api, params=None):
        return self.session.get(self.endpoint + api, params=params).json()

    def _post(self, api, data):
        url = self.endpoint + api
        res = self.session.post(url, data=json.dumps(data))
        if res.status_code != 201:
            try:
                raise ResourceError(res.json()['message'])
            except (json.decoder.JSONDecodeError, KeyError):
                raise ResourceError(res.content)
        return res

    def _patch(self, api, entry_id, data):
        url = self.endpoint + api + '/%d' % entry_id
        res = self.session.patch(url, data=json.dumps(data))
        if res.status_code != 200:
            try:
                raise ResourceError(res.json()['message'])
            except (json.decoder.JSONDecodeError, KeyError):
                raise ResourceError(res.content)

        return res

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

    def get_entry(self, table, entry_id, entry_field='id'):
        filters = [{'name': entry_field, 'op': 'eq', 'val': entry_id}]
        query = json.dumps({'filters': filters})
        params = {'q': query}
        res = self._get(table, params=params)
        return objdict(res['objects'][0])
