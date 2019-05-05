# Verifier

This is the Elasticsearch-based system which resolves buckets of fuzzy contact
info to one or more voter registration records. The most interesting
entrypoints is the `match_many` routines in `matching.py`.

By nature, the algorithm filters rather little and ranks rather much.

In `indexing.INDEX_SETTINGS`, the `number_of_replicas` is presently 2.

## Development
TODO: The dock integration broke when forked and opensourced, and needs to be fixed.

To get started with development for the verifier, you need to install
Docker and our `dock` utility:

You can then get started by running `dock` in the root of the repository:

```bash
$ dock
```

You'll see additional instructions after running `dock`.

## Deployment
TODO

## Testing

You can run tests in a container with:

```bash
$ make test
```

## JSON Schema

To generate a new version of the schema.json file:

```
prmd combine --meta schema/meta.json schema/voters.json > schema.json
```

## Ruby client for the Brigade repo

To create the ruby client for Brigade:

```
heroics-generate VerifierAPI schema.json http://127.0.0.1:10012  > verifier_api.rb
```
