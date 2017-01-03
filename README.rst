========
restjson
========

**NOT RELEASED YET**

A Client for flask_restless-based RESTful HTTP services.

Based on Requests, restjson implements a few extra features:

- uses ultrajson for encoding/decoding data
- local disk cache based on the ETag and If-None-Match header
- replay queries on networks errors
- Automatic If-Match support on PUT, DELETE & PATCH queries

Quick Start
===========


Getting one entry::

    >>> from restjson.client import Client
    >>> c = Client('http://localhost:5001/api/')
    >>> import pprint
    >>> pprint.pprint(c.get_entry('user', 2))
    {'editor': True,
    'email': 'tarek@mozilla.com',
    'firstname': 'Tarek',
    'github': 'tarekziade',
    'id': 2,
    'last_modified': None,
    'lastname': 'Ziade',
    'mozqa': True}



