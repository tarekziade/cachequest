restjson
========

A Client for RESTful HTTP services that talk JSON.

Based on Requests, restjson implements a few extra features:

- uses ultrajson for encoding/decoding data
- local disk cache based on the ETag and If-None-Match header
- replay queries on networks errors
- Automatic If-Match support on PUT, DELETE & PATCH queries



