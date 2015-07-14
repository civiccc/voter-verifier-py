================
***REMOVED***
================

This is the elasticsearch-based system which resolves buckets of fuzzy contact
info to one or more voter registration records. The most interesting
entrypoints are the ``match_one`` and ``match_many`` routines in
``matching.py``.


Deployment
==========

For production, we used a cluster of 8 elasticsearch nodes, each with 8GB RAM.
This allowed us to keep the entire index in RAM, which gives us several orders
of magnitude more speed (especially on EC2, with its slow EBS volumes), since a
large and different segment of the corpus is scanned for each verification. (By
nature, the algorithm filters rather little and ranks rather much.)

In ``indexing.INDEX_SETTINGS``, the ``number_of_replicas`` is presently 0. This
is an artifact of our gradual spin-down after the election. For production,
this was 1 to avoid downtime in the event that we lost a node and to provide
more parallelization.


Indexing
==========
Here's the command I ran to kick off the indexing:

```bash
  export TARGETSMART_PASSWORD=[foobar] # note the leading space, it prevents history
docker run -ti -v /etc/yum.repos.d/epel.repo:/etc/yum.repos.d/epel.repo \
***REMOVED***
    -e TARGETSMART_PASSWORD=$TARGETSMART_PASSWORD \
***REMOVED***
        /bin/bash -c "yum install --enablerepo=epel \
                                  -y gzip pv wget &&
                      source env/bin/activate &&
                      ./index_all.sh"
```

JSON Schema
==========
To generate a new version of the schema.json file:
prmd combine --meta schema/meta.json schema/voters.json > schema.json
