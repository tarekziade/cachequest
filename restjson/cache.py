import ujson as json


def cache_key(name, params=None):
    if params is None:
        params = {}
    params = json.dumps(sorted(params.items()))
    return name, params


class MemoryCache(dict):
    pass
