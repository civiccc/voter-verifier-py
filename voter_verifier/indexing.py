from contextlib import contextmanager
from logging import getLogger
import os
import time

from more_itertools import chunked
from pyelasticsearch import ElasticHttpNotFoundError
from verifier_date_utils import day_of_year
***REMOVED***
***REMOVED***


logger = getLogger(__name__)


INDEX_SETTINGS = {
  'index': {
    'number_of_shards': 4,
    'number_of_replicas': 2,  # 1 replica = 2 copies total
    'analysis': {
      'analyzer': {
        # Let's not use stopwords or stemming for addresses. It would
        # be nice if there were a way to make things like NE, NW, N, S,
        # and such weighted heavily. I want to strip the "ST" off "21ST
        # AVE" (but not the C off "APT 2C"); could probably do that by
        # having the pattern analyzer split on "ST" but using a
        # lookbehind assertion to say there was a number behind it.
        'address_analyzer': {
          'type': 'custom',
          # Break on spaces, dots, number signs, and commas but not
          # numbers, for things like "0 RD#2 BX 157B":
          'tokenizer': 'address_tokenizer',
          'filter': ['lowercase', 'address_synonym'],
        },
        # Break on space and hyphen and dot. Then we can do text phrase
        # queries against it, and it might match ann-marie or hern-
        # hertzfeld no matter what delimiter is used.
        'name_analyzer': {
          'type': 'custom',
          'tokenizer': 'name_tokenizer',
          'filter': ['lowercase'],
        },
        'name_compact_analyzer': {
          'type': 'custom',
          'tokenizer': 'keyword',
          'filter': ['lowercase', 'alphanumeric']
        },
        'first_name_analyzer': {
          'type': 'custom',
          'tokenizer': 'name_tokenizer',
          'filter': ['lowercase', 'first_name_synonym'],
        },
      },
      'filter': {
        'address_synonym': {
          'type': 'synonym',
            'synonyms': ADDRESS_SYNONYMS,
            'expand': False
          },
          'first_name_synonym': {
            'type': 'synonym',
            'synonyms': FIRST_NAME_SYNONYMS,
            # Since we are doing this only on the query (not on the
            # corpus), this has to be True. That way, Zack in the query
            # matches both Zack and Zachary in the corpus:
            'expand': True
          },
            'alphanumeric': {
            'type': 'pattern_replace',
            'pattern': '[^a-zA-Z0-9]',
            'replacement': ''
          }
      },
      'tokenizer': {
        'address_tokenizer': {
          'type': 'pattern',
          'pattern': r'[^a-zA-Z0-9]+'
        },
        'name_tokenizer': {
          'type': 'pattern',
          # FIXME: O'Brien. Maybe just don't make O a known prefix,
          # and let the slop deal with it. It's only a distance of 1.
          'pattern': r"[^a-zA-Z0-9']+"
        }
      }
    }
  }
}


# Mapping shortcuts:
UNANALYZED_STRING = {'type': 'string', 'index': 'not_analyzed'}
NAME = {'type': 'string', 'analyzer': 'name_analyzer'}
NAME_COMPACT = {'type': 'string', 'analyzer': 'name_compact_analyzer'}
# A horrible ES mapping type for enums stored as strings:
# FIXME: Find a better one.
STRING_ENUM = UNANALYZED_STRING
INT = {'type': 'integer'}  # < ~2B.
# Tried using some SHORTs and BYTEs just for economy, but they caused test
# failures. Maybe pyes maps them to some horrible types.
DATE = {'type': 'date'}
BOOL = {'type': 'boolean'}


PROPERTIES = {
  'id': UNANALYZED_STRING,
  'source_id': INT,
  'identifier_scope_id': INT,

  # Scope ID, then a space, then the identifier:
  'scope_and_identifier': UNANALYZED_STRING,

  'type_flag': STRING_ENUM,
  'status_flag': STRING_ENUM,
  'effective_date': UNANALYZED_STRING,
  'registration_date': UNANALYZED_STRING,

  # FIXME: Think about concatting all name components and searching them all
  # at once, either as the only query bit or as a subquery.
  'first_name': NAME,
  'first_name_compact': NAME_COMPACT,
  'middle_name': NAME,
  'middle_name_compact': NAME_COMPACT,
  'last_name': NAME,
  'last_name_compact': NAME_COMPACT,
  'suffix': NAME,

  'address': {'type': 'string', 'analyzer': 'address_analyzer'},
  'ts_address': {'type': 'string', 'analyzer': 'address_analyzer'},

  'address_street_name': {'type': 'string', 'analyzer': 'address_analyzer'},
  'ts_address_street_name': {'type': 'string', 'analyzer': 'address_analyzer'},

  # We think that we can omit this field from the indexed properties, as we
  # will never search for it.
  # 'address_street_number': UNANALYZED_STRING,

  # Normalize dashes and such in the query string to spaces:
  'city': {'type': 'string', 'analyzer': 'simple'},
  'ts_city': {'type': 'string', 'analyzer': 'simple'},

  'st': UNANALYZED_STRING,  # always uppercase
  'ts_st': UNANALYZED_STRING,  # always uppercase

  # String so we can fuzzy-match entry errors
  'zip_code': UNANALYZED_STRING,
  'ts_zip_code': UNANALYZED_STRING,

  'plus_four': UNANALYZED_STRING,

  'county': UNANALYZED_STRING,

  # Break up to support null parts:
  'dob_year': INT,
  'dob_month': INT,
  'dob_day': INT,

  # Born on the nth day of the year, assuming not a leap year:
  'dob_day_of_year': INT,

  'phone': UNANALYZED_STRING,
  'reg_date': DATE,
  'party': STRING_ENUM,
  'ts_lat_lng_location': {'type': 'geo_point'},
  'lat_lng_location': {'type': 'geo_point'},
  'is_permanent': BOOL,
  'is_certified': BOOL,
  'create_ts': DATE,
  'update_ts': DATE,

  'general_2014': BOOL,
  'general_2012': BOOL,
  'general_2010': BOOL,
  'general_2008': BOOL,
  'general_2006': BOOL,
  'general_2004': BOOL,
  'general_2002': BOOL,
  'general_2000': BOOL}


def create_mapping(index_name, es_client, mappings):
  """
  Create the ElasticSearch index and install the mapping.
  """
  # Installing the mapping in the same request as creating the index
  # fails silently in pyes.
  es_client.create_index(index_name, settings=INDEX_SETTINGS)
  es_client.put_mapping(index_name, DOC_TYPE, mappings)


def ensure_mapping_exists(index_name, es_client, force_delete=False, should_update_settings=False):
  """
  Checks for the mapping in ES and will create it if it doesn't exist.
  """
  # Create or merge in new mappings:
  mappings = {
    DOC_TYPE: {
      # Votizen disabled _source to save space. We might want to do that
      # too if performance is not sufficient or disk space is too
      # out-of-control. They claimed it dropped index size from 240 GB ->
      # 45 GB. For the TargetSmart sample 50,000 records, enabling this
      # results in an increase from 3.5 Kb -> 11.6 Mb.
      #
      # If we disable _source, we will need to find a new key-value store
      # to keep the raw value of the records, as they will be impossible
      # to retrieve from ES.
      '_source': {'enabled': True},
      '_all': {'enabled': False},  # save some space

      'properties': PROPERTIES}}

  if force_delete:
    # FIXME: Delete only if we have new rolls and we can't think of a
    # cleverer way to delete ppl who disappeared since the old rolls
    try:
      es_client.delete_index(index_name)
    except ElasticHttpNotFoundError:
      pass
    create_mapping(index_name, es_client, mappings)
  elif should_update_settings:
    # TODO: This doesn't update PROPERTIES that are part of the mapping, but
    # probably should.
    es_client.close_index(index_name)
    es_client.update_settings(index_name, settings=INDEX_SETTINGS)
    es_client.open_index(index_name)
  else:
    # Create the mapping if it doesn't exist
    try:
      es_client.send_request('GET', [index_name])
    except ElasticHttpNotFoundError:
      create_mapping(index_name, es_client, mappings)

  # I suspect our 8-node farm takes a moment to get the new index up during
  # tests:
  es_client.health(index_name, level='indices', wait_for_status='yellow')


def index_voters(index_name,
                 voters,
                 es_client):
  """
  Return an iterator that, as it is exhausted, indexes an iterable of voter
  mappings into the named ES index.

  Yields a series of "number of documents done so far" counts so the caller
  can indicate progress.
  """
  # Index the stuff:
  i = 0
  for chunk in chunked(voters, 1000):
    docs = [_document_from_mapping(voter) for voter in chunk]
    es_client.bulk_index(index_name, DOC_TYPE, docs)
    i += len(chunk)
    yield i


def _document_from_mapping(mapping):
  """Given a map of voter attributes, return an indexable ES document.

  Mostly, this just derives derivable fields.

  Map keys, most of which must be omitted if unknown:

    id: The ES document ID to use--typically the primary key to the full
        voter object so you can fetch it when the match routines return an
        ID
    first_name
    middle_name
    last_name
    suffix: Space-separated list of suffixes, like JR, SR, II, III, etc.
    address: One-line residence street address
    city: Residence city
    st: Residence state
    zip_code: First 5 digits of residence ZIP code
    dob_year: Year of birth
    dob_month: Month of birth
    dob_day: Day of birth
    status_flag: 'A'=Active, 'I'=Inactive, 'P'=Purged, 'D'=Deleted

  Indexed but not used in match routines:

    create_ts: The creation time of this voter record in your system.
    identifier: The registrar-provided identifier for this voter
    identifier_scope_id: The ID of the scope that the ``id`` value belongs
        to. For example, NY State could be one scope, and Santa Clara
        County could be another. ``id`` values must be unique within a
        scope.
    is_certified: Whether the residence address is CASS-formatted.
    is_permanent: Whether the voter's address is a permanent (residence)
        one.
    party: 'D'=Democrat, 'G'=Green, 'I'=Independent, 'L'=Libertarian,
        'R'=Republican, 'O'=Other, 'U'=Unknown
    phone: Voter's phone number
    plus_four: The last 4 digits of the 9-digit extended residence ZIP code
    record_id: Deprecated and unused
    reg_date: Date the voter registered to vote
    source_id: ID of the batch import which last updated this voter
    type_flag: 'M'=Manual (not found in registrar records), 'R'=Rolls
    update_ts: Last-updated timestamp.

  The intention was for these to be returned from ES to avoid hitting the DB,
  but we ended up being very aggressive about turning off _source to save
  RAM. It certainly saves disk, but we never did establish whether it saves
  RAM as well.
  """
  document = mapping.copy()
  if mapping.get('identifier_scope_id') and mapping.get('identifier'):
    document['scope_and_identifier'] = (
        '%s %s' % (mapping['identifier_scope_id'], mapping['identifier']))

  if document.get('dob_month') and document.get('dob_day'):
    document['dob_day_of_year'] = day_of_year(document['dob_month'],
                                              document['dob_day'])

  return document


@contextmanager
def aliased_index(es_client, index_name):
  """
  Creates a namespaced version of the index and then swaps out the alias
  after the with block completes.
  """

  new_index = os.environ.get('VERIFIER_NEW_INDEX_NAME', index_name + "_" + time.strftime("%Y%m%d%H%M%S"))
  ensure_mapping_exists(new_index, es_client, force_delete=True)

  yield new_index

  cleanup_actions = []
  try:
    old_index = es_client.send_request('GET', (index_name, '/_alias')).keys()[0]
    cleanup_actions.append({ "remove": { "index": old_index, "alias": index_name } })
  except IndexError:
    pass
  except ElasticHttpNotFoundError:
    pass

  cleanup_actions.append({ "add": { "index": new_index, "alias": index_name } })
  es_client.send_request('POST', ('_aliases',), body={"actions": cleanup_actions })
