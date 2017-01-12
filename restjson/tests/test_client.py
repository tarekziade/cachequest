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

        for tag in ('1', '2', '3'):
            client.create_entry('tag', {'name': tag})

        tags = [{'id': '1'},
                {'id': '2'},
                {'id': '3'}]

        project = client.get_entry('project', 1)
        try:
            self.assertEquals(project.tags, [])
            client.update_relation('project', 1, 'tags', tags)
            project = client.get_entry('project', 1)
            self.assertEquals(len(project.tags), 3)
        finally:
            client.delete_relation('project', 1, 'tags', tags)
