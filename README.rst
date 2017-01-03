restjson
========

A Client for flask_restless-based RESTful HTTP services.

Based on Requests, restjson implements a few extra features:

- uses ultrajson for encoding/decoding data
- local disk cache based on the ETag and If-None-Match header
- replay queries on networks errors
- Automatic If-Match support on PUT, DELETE & PATCH queries



