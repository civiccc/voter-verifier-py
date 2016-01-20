verifier
================

This is the elasticsearch-based system which resolves buckets of fuzzy contact
info to one or more voter registration records. The most interesting
entrypoints are the `match_one` and `match_many` routines in
`matching.py`.

By nature, the algorithm filters rather little and ranks rather much.

In `indexing.INDEX_SETTINGS`, the `number_of_replicas` is presently 2.

Deployment
==========

```bash
***REMOVED***
bli deploy [env]
```

Indexing
==========
Indexing happens monthly in a Chronos job:

***REMOVED***

Tests
==========
```bash
docker run --publish 9200:9200 -d elasticsearch:1.7.3 elasticsearch --action.write_consistency=one
***REMOVED***
```

JSON Schema
==========
To generate a new version of the schema.json file:
prmd combine --meta schema/meta.json schema/voters.json > schema.json
