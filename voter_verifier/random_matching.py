import re
from logging import getLogger, INFO

from pyelasticsearch import ElasticSearch
from voter_verifier.matching import es_client, statsd
from voter_verifier.config import (ES_HOSTS, TIMEOUT, RETRIES, INDEX,
    DOC_TYPE, VERIFIER_MAX_RESULTS)


logger = getLogger(__name__)

MAX_OFFSET = 50000

def from_elasticsearch_mapping_address_only(hit):
  """
  Converts a response from ElasticSearch into a dict() suitable for returning
  to an API consumer.
  """
  _source = hit['_source']

  return {
    'address': _source['address'] or _source['ts_address'],
    'address_street_number': _source['address_street_number'] or _source['ts_address_street_number'],
    'address_unit_designator': _source['address_unit_designator'] or _source['ts_address_unit_designator'],
    'address_apt_number': _source['address_apt_number'],
    'city': _source['city'] or _source['ts_city'],
    'state': _source['st'] or _source['ts_st'],
    'zip_code': _source['zip_code'] or _source['ts_zip_code'],
    '_debug_score': hit['_score']
    }

def raw_elastic_random_voters(state,
                              seed=0,
                              limit=None):
  """
  Return random voters from ES matching the given information.

  Return the raw ES results, not APIVoter objects.
  """

  if not limit:
    limit = VERIFIER_MAX_RESULTS

  query = {
    "size": limit,
    "from": seed % MAX_OFFSET,
    "query": {
      "match": {
        "st": {
          "query": state,
          "type": "phrase"
        }
      }
    }
  }

  return es_client.search(query,
                          index=INDEX,
                          doc_type=DOC_TYPE)


def match_random_addresses(state, seed=0, **kwargs):
  """
  Returns a random list of voter IDs based on the state.

  See ``raw_elastic_random_voters()`` for more argument documentation.
  """

  results = raw_elastic_random_voters(state, seed, **kwargs)
  hits = results['hits']['hits']
  took = results['took']
  statsd.histogram('verifier.es_query_time.match_random_addresses', took / 1000.0)

  logger.info('match_random found %s matches for \n'
              '    state=%s\n'
              '    seed=%s',
              len(hits), state, seed)

  return [from_elasticsearch_mapping_address_only(hit) for hit in hits]
