import unittest
from restjson.client import Client


class TestClient(unittest.TestCase):

    def test_simple_call(self):
        client = Client('http://localhost/')
        client.get_entries('blah')
