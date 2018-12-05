# Verifier

This is the Elasticsearch-based system which resolves buckets of fuzzy contact
info to one or more voter registration records. The most interesting
entrypoints is the `match_many` routines in `matching.py`.

For further documentation and rationale see:
***REMOVED***

By nature, the algorithm filters rather little and ranks rather much.

In `indexing.INDEX_SETTINGS`, the `number_of_replicas` is presently 2.

## Development

To get started with development for the verifier, you need to install
Docker and our `dock` utility:

***REMOVED***

You can then get started by running `dock` in the root of the repository:

```bash
dock
```

You'll see additional instructions after running `dock`.

## Deployment

The verifier is deployed to staging after every commit merged:

***REMOVED***

You can manually deploy by running:

```
jenkins/deploy [staging | production]
```

To deploy an image tag that has already been pushed, specify
the `DEPLOY_TAG` environment variable:

```
DEPLOY_TAG=2016-12-27_23-18-47_7970879 jenkins/deploy production
```

This avoids building and pushing the image (which can take time).
See ***REMOVED*** for a list of
available tags.

## Testing

You can run tests in a container with:

```bash
jenkins/test
```

This is the same script that Jenkins would run.

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
