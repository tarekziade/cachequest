import unittest
from restjson.client import Client, ResourceError


class TestClient(unittest.TestCase):

    def test_simple_call(self):
        client = Client('http://localhost:5001/api/')
        for model in client.models:
            if model['name'] == 'user':
                break

        name = model['name']
        key = model['primary_key'][0]
        entries = client.get_entries(name)
        for entry in entries[-2:-1]:
            # exercising local cache
            client.get_entry(name, entry[key])
            last_entry = client.get_entry(name, entry[key])
            cache_size = len(client.cache)
            client.bust_cache(name, entry[key])
            self.assertTrue(len(client.cache) == cache_size - 1)
            last_entry = client.get_entry(name, entry[key], bust_cache=True)
            self.assertEqual(len(client.cache), cache_size)

        last_entry['firstname'] = 'Bam'
        client.update_entry(name, last_entry)
        v = client.get_entry(name,  last_entry['id'])
        self.assertEqual(v['firstname'], 'Bam')
        new = dict(v)
        new['firstname'] = 'new'
        new.pop('id')
        new.pop('last_modified')
        new_entry_id = client.create_entry(name, new)['id']
        v = client.get_entry(name, new_entry_id)
        self.assertEqual(v['firstname'], 'new')
        client.delete_entry(name, new_entry_id)

        try:
            client.get_entry(name, new_entry_id)
            raise AssertionError()
        except ResourceError as e:
            self.assertEqual(e.code, 404)

    def test_filters(self):
        client = Client('http://localhost:5001/api/')
        filters = [{'name': 'github',
                    'op': 'eq',
                    'val': 'tarekziade'}]
        entries = client.get_entries('user', filters=filters)
        self.assertEqual(len(entries), 1)

    def test_sort(self):
        client = Client('http://localhost:5001/api/')
        client.get_entries('project', sort='name')

    def test_relations(self):
        client = Client('http://localhost:5001/api/')

        new_tags = []
        for tag in ('1', '2', '3'):
            entry = client.create_entry('tag', {'name': tag})
            new_tags.append(entry)

        project = client.get_entry('project', 1)
        try:
            curlen = len(project.tags)
            project.tags.extend(new_tags)
            client.update_entry('project', project)
            project = client.get_entry('project', 1)
            self.assertEquals(len(project.tags), 3 + curlen)
        finally:
            client.delete_relation('project', 1, 'tags', new_tags)

    def test_cache(self):
        client = Client('http://localhost:5001/api/', cache=False)
        for model in client.models:
            if model['name'] == 'user':
                break

        name = model['name']
        key = model['primary_key'][0]
        entries = client.get_entries(name)
        for entry in entries[-2:-1]:
            client.get_entry(name, entry[key])
            client.get_entry(name, entry[key])
            client.get_entry(name, entry[key], bust_cache=True)
