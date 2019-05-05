import re
from datetime import date, datetime
from logging import getLogger, INFO
from numbers import Number

from pyelasticsearch import ElasticSearch
from datadog.dogstatsd import statsd

from voter_verifier.zip_to_lat_lng import ZipToLatLng
from verifier_date_utils import years_ago, NullableDate
from voter_verifier.config import (ES_HOSTS, TIMEOUT, RETRIES, INDEX,
    DOC_TYPE, VERIFIER_MAX_RESULTS, STATSD_HOST, STATSD_PORT,
    DEFAULT_SEARCH_TYPE, SEARCH_TYPE_DISCOVER, SEARCH_TYPE_TOP,
    SEARCH_TYPE_AUTO_VERIFY,CONFIDENCE_INTERVAL_FOR_AUTO_VERIFICATION,
    MIN_SCORE_AUTO_VERIFY_WITH_DOB, MIN_SCORE_AUTO_VERIFY_WITHOUT_DOB,
    MIN_SCORE_TOP, MIN_SCORE_DISCOVER)

logger = getLogger(__name__)

es_client = ElasticSearch(ES_HOSTS, TIMEOUT, RETRIES)
zip_to_lat_lng = ZipToLatLng()
es_client.logger.setLevel(INFO)
statsd.host = STATSD_HOST
statsd.port = STATSD_PORT


# Exception Declaration
class TooYoungToVote(Exception):
  """Raised when someone isn't old enough to vote"""

class NotEnoughData(Exception):
  """Raised when we're trying to auto verify or get top results,
  but did not receive sufficient data
  """

# Utility Functions
def from_elasticsearch_mapping(hit):
  """
  Converts a response from ElasticSearch into a dict() suitable for returning
  to an API consumer.
  """
  _source = hit['_source']

  dob = "{0:04}-{1:02}-{2:02}".format(
          _source['dob_year'] or 0,
          _source['dob_month'] or 0,
          _source['dob_day'] or 0
        )

  return {
    'id': hit['_id'],
***REMOVED***
***REMOVED***
    'first_name': _source['first_name'],
    'last_name': _source['last_name'],
    'middle_name': _source['middle_name'],
    'dob': dob,
    'address': _source['address'] or _source['ts_address'],
    'address_street_name': _source['address_street_name'] or _source['ts_address_street_name'],
    'address_street_number': _source['address_street_number'] or _source['ts_address_street_number'],
    'address_unit_designator': _source['address_unit_designator'] or _source['ts_address_unit_designator'],
    'address_apt_number': _source['address_apt_number'] or _source['ts_address_apt_number'],
    'city': _source['city'] or _source['ts_city'],
    'state': _source['st'] or _source['ts_st'],
    'zip_code': _source['zip_code'] or _source['ts_zip_code'],
    'location': _source['lat_lng_location'],
    'alternative_location': _source['ts_lat_lng_location'],
    'party': _source['party'],
    'registration_date': _source['registration_date'],
    'general_2014': _source['general_2014'],
    'general_2012': _source['general_2012'],
    'general_2010': _source['general_2010'],
    'general_2008': _source['general_2008'],
    'general_2006': _source['general_2006'],
    'general_2004': _source['general_2004'],
    'general_2002': _source['general_2002'],
    'general_2000': _source['general_2000'],
    '_debug_score': hit['_score'],
    '_index_name': hit['_index'],
    'auto_verify': hit.get('_auto_verify', False)
  }

def format_contact(hit):
  """ Format an elasticsearch hit, including the email and phone fields"""
  email_fields = ['email', 'email_append_level', 'email_match_type']
  phone_fields = ['phone', 'vb_phone', 'vb_phone_type', 'vb_phone_wireless', 'ts_wireless_phone']
  score_fields = ['voter_score', # only score that is not a float
                  'activist_score',
                  'campaign_finance_score',
                  'catholic_score',
                  'children_present_score',
                  'climate_change_score',
                  'college_funding_score',
                  'college_graduate_score',
                  'evangelical_score',
                  'govt_privacy_score',
                  'gun_control_score',
                  'gunowner_score',
                  'high_school_only_score',
                  'ideology_score',
                  'income_rank_score',
                  'local_voter_score',
                  'marriage_score',
                  'midterm_general_turnout_score',
                  'minimum_wage_score',
                  'moral_authority_score',
                  'moral_care_score',
                  'moral_equality_score',
                  'moral_equity_score',
                  'moral_loyalty_score',
                  'moral_purity_score',
                  'non_presidential_primary_turnout_score',
                  'nonchristian_score',
                  'offyear_general_turnout_score',
                  'otherchristian_score',
                  'paid_leave_score',
                  'partisan_score',
                  'path_to_citizen_score',
                  'presidential_general_turnout_score',
                  'presidential_primary_turnout_score',
                  'prochoice_score',
                  'tax_on_wealthy_score',
                  'teaparty_score',
                  'trump_resistance_score',
                  'trump_support_score',
                  'veteran_score']
  race_scores = ['race_white_score', 'race_afam_score', 'race_hisp_score', 'race_natam_score', 'race_asian_score']
  voting_fields = ['vf_g2016', 'vf_g2014', 'vf_g2012', 'vf_p2016', 'vf_p2014', 'vf_p2012']
  et_al = ['num_general_election_votes', 'num_primary_election_votes'] #integers

  source = hit['_source']
  rec = from_elasticsearch_mapping(hit)

  for field in email_fields + phone_fields + score_fields + race_scores + voting_fields + et_al:
    rec[field] = source.get(field, None)

  return rec

def get_five_digit_zip_code(zip_code):
  """Strip main 5 zip digits, returns None if zip_code malformed."""
  if not zip_code:
    return None
  if len(zip_code) == 5:
    return zip_code
  re_match = re.match('(\d{5})-\d{4}', zip_code)
  if re_match:
    return re_match.group(1)
  return None

def normalize_dob(dob):
  """
  Turn a datetime, date, None or NullableDate into a NullableDate.

  If a person with that birthday is too young to vote, raise
  TooYoungToVote.
  """
  if isinstance(dob, NullableDate):
      return dob
  ret = NullableDate(dob)
  if ret and years_ago(date.today(), 18) < ret:
      raise TooYoungToVote
  return ret


SUFFIX_RE = re.compile(r'\b(JR|SR|JUNIOR|SENIOR|II|III|IV|V)\b', flags=re.I)


def extract_suffixes(name, suffixes):
  """Find any recognized suffixes in a name part, and return it without them.

  Add the suffixes to the ``suffixes`` list. We don't bother to strip any
  whitespace, because ES does that for us.

  """
  def remember_suffix(match):
    """Close of ``suffixes`` to hang onto the suffix that was replaced."""
    suffixes.append(match.group(1))
    return ''
  return SUFFIX_RE.sub(remember_suffix, name)


def suffix_normalized_name(first, middle, last, suffix):
  """Return a map of various name parts, with common suffixes moved into the
  suffix field and whitespace stripped.

  We append any recognized suffixes to the existing suffix, if any.

  """
  # JR is never in the beginning or middle of last_name; always at the end.
  # It's usually at the end of middle_name, sometimes in the beginning, never in the middle.
  # It's rarely (1 in 770K) in first_name.
  suffixes = suffix.split()
  return dict(first_name=extract_suffixes(first, suffixes).strip(),
              middle_name=extract_suffixes(middle, suffixes).strip(),
              last_name=extract_suffixes(last, suffixes).strip(),
              suffix=' '.join(suffixes))

def get_name_parts(first, middle, last, suffix):
  """Strip out suffixes. If no middle name exists, and first name
  Is two word, treat the first as first and the second as middle.
  """
  name_parts = suffix_normalized_name(first, middle, last, suffix)
  if not name_parts['middle_name']:
    first_name_split = name_parts['first_name'].split(' ')
    if len(first_name_split) == 2:
      name_parts['first_name'] = first_name_split[0]
      name_parts['middle_name'] = first_name_split[1]
  return name_parts

def get_lat_lng_str_for_zip_code(zip_code):
  return zip_to_lat_lng.get_lat_lng_str(zip_code) if zip_code else None

def wrap_query_list_if_needed(query_list, operator):
  """Wraps a list a query using a single operator. If list includes a single
  element, return the element.
  """
  if len(query_list) > 1:
    return \
        {
          operator: query_list
        }
  elif len(query_list) == 1:
    return query_list[0]
  else:
    return None

def get_last_name_or_compact_last_name_queries(last_name, name_parts):
  return [
    {
      "query": {
        "match": {
          "last_name": name_parts['last_name'] or last_name
        }
      }
    },
    {
      "query": {
        "match": {
          "last_name_compact": {
            "query": name_parts['last_name'] or last_name,
            "analyzer": "name_compact_analyzer"
          }
        }
      }
    }
  ]

def get_last_name_query(last_name, alternative_last_name,
                               name_parts, alternative_name_parts):
  last_name_filter_query = get_last_name_or_compact_last_name_queries(
      last_name, name_parts)
  if alternative_last_name or alternative_name_parts['last_name']:
    last_name_filter_query.extend(get_last_name_or_compact_last_name_queries(
        alternative_last_name, alternative_name_parts))
  return wrap_query_list_if_needed(last_name_filter_query, "or")

# Filter Queries
def get_last_name_filter_query(last_name, alternative_last_name,
                               name_parts, alternative_name_parts):
  """We filter out documents that do not match last name.
  This is a hard constraint for all search types. Expected to be used by
  AUTO_VERIFY, TOP, and DISCOVER
  """
  return get_last_name_query(last_name, alternative_last_name,
                             name_parts, alternative_name_parts)

def get_state_filter_query(state):
  """ This is a filtering function to be used by the admin tool. Expected to
      be used by DISCOVER only.
  """
  return \
      {
        "query": {
          "multi_match": {
            "query": state,
            "fields": ['st', 'ts_st']
          }
        }
      }

def get_dob_within_range_filter_query(dob_year, delta):
  """ Make sure the date year is missing or in the closed interval
          [dob_year-delta, dob_year+delta]
  """
  dob_within_range_filter_query = []
  dob_within_range_filter_query.append(
    {
      "missing": {
        "field": "dob_year"
      }
    }
  )
  dob_within_range_filter_query.append(
    {
      "range" : {
        "dob_year" : {
          "gte" : dob_year - delta,
          "lte" : dob_year + delta
        }
      }
    }
  )
  return wrap_query_list_if_needed(dob_within_range_filter_query, "or")

def get_location_or_dob_filter_query(dob, zip_code):
  """For auto-verification a user needs to have either a dob.year match, or
  live within 10 miles of voter on record. Expected to be used by
  AUTO_VERIFY only.
  """
  auto_verify_location_or_dob_filter_query = []
  if dob:
    auto_verify_location_or_dob_filter_query.append(
      {
        "missing": {
          "field": "dob_year"
        }
      })
    auto_verify_location_or_dob_filter_query.append(
      {
        "term": {
          "dob_year": dob.year
        }
      })
  lat_lng_str = get_lat_lng_str_for_zip_code(zip_code)
  if lat_lng_str:
    auto_verify_location_or_dob_filter_query.extend(
      [
        {
          "geo_distance": {
            "distance": "16km",
            "ts_lat_lng_location": lat_lng_str
          }
        },
        {
          "geo_distance": {
            "distance": "16km",
            "lat_lng_location": lat_lng_str
          }
        }
      ])
  result = wrap_query_list_if_needed(auto_verify_location_or_dob_filter_query, "or")
  if not result:
    raise NotEnoughData # Flag that we cannot auto verify without either zip or dob
  return result

def get_name_filter_query(name_parts, alternative_name_parts):
  """A user must have a fuzzy first or middle name match.  Expected to be used by
  AUTO_VERIFY and TOP.
  """
  def get_auto_verify_name_filter_sub_query(name):
    return [
      {
        "query": {
          "multi_match": {
            "type": "phrase",
            "query": name,
            "analyzer": "first_name_analyzer",
            "fields": ['first_name', 'middle_name']
          }
        }
      },
      {
        "query": {
          "multi_match": {
            "type": "phrase",
            "query": name,
            "analyzer": "name_compact_analyzer",
            "fields": ['first_name_compact', 'middle_name_compact']
          }
        }
      }]
  auto_verify_name_filter_query = []
  if name_parts['first_name']:
    auto_verify_name_filter_query.extend(
        get_auto_verify_name_filter_sub_query(name_parts['first_name']))
  if name_parts['middle_name']:
    auto_verify_name_filter_query.extend(
        get_auto_verify_name_filter_sub_query(name_parts['middle_name']))
  if alternative_name_parts['first_name']:
    auto_verify_name_filter_query.extend(
        get_auto_verify_name_filter_sub_query(alternative_name_parts['first_name']))
  if alternative_name_parts['middle_name']:
    auto_verify_name_filter_query.extend(
        get_auto_verify_name_filter_sub_query(alternative_name_parts['middle_name']))

  result = wrap_query_list_if_needed(auto_verify_name_filter_query, "or")
  if not result:
    # We cannot auto-verify this user as we do not have any first/middle name
    # support query.
    raise NotEnoughData
  return result

def get_auto_verify_filter_query(name_parts, alternative_name_parts, dob, zip_code):
  """Filter query for auto verification. Expected to be used by
  AUTO_VERIFY only.
  """
  return \
    {
      "and" : [
        get_name_filter_query(name_parts, alternative_name_parts),
        get_location_or_dob_filter_query(dob, zip_code)
      ]
    }

# Scoring queries - Used for scoring for all search types.

def get_location_match_scoring_queries(address, city, state, zip_code):
  """Return scoring queries based on user location

  Maximal possible location score: 10

  Exact zip_code match +1
  Zip_code within 10miles +6
  Exact address (address, city, state) +3
  """
  location_match_scoring_queries = []
  if zip_code:
    location_match_scoring_queries.append(
      {
        "filter": {
          "query": {
            "multi_match": {
              "query": zip_code,
              "fields": ["zip_code", "ts_zip_code"]
            }
          }
        },
        "boost_factor": "1"
      }
    )
    lat_lng_str = get_lat_lng_str_for_zip_code(zip_code)
    if lat_lng_str:
      location_match_scoring_queries.append(
        {
          "filter": {
            "or": [
              {
                "geo_distance": {
                  "distance": "16km",
                  "ts_lat_lng_location": lat_lng_str
                }
              },
              {
                "geo_distance": {
                  "distance": "16km",
                  "lat_lng_location": lat_lng_str
                }
              }
            ]
          },
          "boost_factor": "6"
        })
  elif city and state:
    location_match_scoring_queries.append(
      {
        "filter": {
          "and": [
            {
              "query": {
                "multi_match": {
                  "type": "phrase",
                  "query": city,
                  "fields" :["city", "ts_city"]
                }
              }
            },
            {
              "query": {
                "multi_match": {
                  "query": state,
                  "fields" :["st", "ts_st"]
                }
              }
            }
          ]
        },
        "boost_factor": "2"
      })
  if address and city and state:
    location_match_scoring_queries.append(
      {
        "filter": {
          "and": [
            {
              "query": {
                "match": {
                  "address": {
                    "type": "phrase",
                    "query": address,
                    "slop": 2,
                  }
                }
              }
            },
            {
              "query": {
                "multi_match": {
                  "type": "phrase",
                  "query": city,
                  "fields" :["city", "ts_city"]
                }
              }
            },
            {
              "query": {
                "multi_match": {
                  "query": state,
                  "fields" :["st", "ts_st"]
                }
              }
            }
          ]
        },
        "boost_factor": "3"
      })
  return location_match_scoring_queries


def get_dob_scoring_queries(dob):
  """Return scoring queries based on user DoB

  Maximal possible location score: 10

  Exact year match +5
  Exact month match +3
  Exact day match +2
  """
  dob_scoring_queries = \
      [
        {
          "filter": {
            "missing": {
              "field": "dob_year"
            }
          },
          "boost_factor": "1"
        }
      ]

  if dob.year:
    dob_scoring_queries.append(
      {
        "filter": {
          "term": {
            "dob_year": dob.year
          }
        },
        "boost_factor": "5"
      })

  if dob.month:
    dob_scoring_queries.append(
      {
        "filter": {
          "term": {
            "dob_month": dob.month
          }
        },
        "boost_factor": "2"
      })
    dob_scoring_queries.append(
      {
        "filter": {
          "or": [
            {
              "missing": {
                "field": "dob_month"
              }
            },
            {
              "and": [
                {
                  "term": {
                    "dob_month": 1
                  }
                },
                {
                 "term": {
                   "dob_day": 1
                  }
                }
              ]
            }
          ]
        },
        "boost_factor": "1"
      })

  if dob.day:
    dob_scoring_queries.append(
      {
        "filter": {
          "term": {
            "dob_day": dob.day
            }
        },
        "boost_factor": "2"
      })
    dob_scoring_queries.append(
      {
        "filter": {
          "or": [
            {
              "missing": {
                "field": "dob_day"
              }
            },
            {
             "term": {
               "dob_day": 1
              }
            }
          ]
        },
        "boost_factor": "1"
      })
  return dob_scoring_queries

def get_last_name_match_scoring_query(name_parts, alternative_name_parts,
                                      last_name, alternative_last_name):
  return get_last_name_query(last_name, alternative_last_name,
                             name_parts, alternative_name_parts)

def get_exact_name_match_scoring_query(field, name, alternative_name):
  exact_name_match_scoring_query = []
  def get_exact_name_match_scoring_query_helper(field, name):
    if name:
      exact_name_match_scoring_query.append(
        {
          "query": {
            "match_phrase": {
              field: {
                "query": name,
              }
            }
          }
        })
  get_exact_name_match_scoring_query_helper(field, name)
  get_exact_name_match_scoring_query_helper(field, alternative_name)
  return wrap_query_list_if_needed(exact_name_match_scoring_query, "or")

def get_non_exact_name_match_scoring_query(field, name, alternative_name):
  non_exact_name_match_scoring_query = []
  def get_non_exact_name_match_scoring_query_helper(field, name):
    if name:
      non_exact_name_match_scoring_query.append(
        {
          "query": {
            "match_phrase": {
              field: {
                "query": name,
                "analyzer": "first_name_analyzer"
              }
            }
          }
        })
      non_exact_name_match_scoring_query.append(
        {
          "query": {
            "match_phrase": {
              field: {
                "query": name,
                "analyzer": "name_compact_analyzer"
              }
            }
          }
        })
  get_non_exact_name_match_scoring_query_helper(field, name)
  get_non_exact_name_match_scoring_query_helper(field, alternative_name)
  return wrap_query_list_if_needed(non_exact_name_match_scoring_query, "or")

def get_middle_match_scoring_query(name, alternative_name):
  def get_middle_match_scoring_query_helper(name):
    if not name:
      return []
    middle_match_scoring_query = []
    # Only got initial, run prefix query
    if len(name) == 1:
      middle_match_scoring_query.append(
        {
          "query": {
            "prefix": {
              # we need to lowercase the initial, as prefix queries
              # are not analyzed.
              "middle_name": name.lower()
            }
          }
        })
    # we have full name to match
    else:
      # try to hit name with middle name (include synonyms)
      middle_match_scoring_query.append(
        {
          "query": {
            "match": {
              "middle_name" : {
                "type": "phrase",
                "query": name,
                "analyzer": "first_name_analyzer",
              }
            }
          }
        })
      # try to hit name with middle name (compact form)
      middle_match_scoring_query.append(
        {
          "query": {
            "match": {
              "middle_name_compact" : {
                "type": "phrase",
                "query": name,
                "analyzer": "name_compact_analyzer",
              }
            }
          }
        })
      middle_match_scoring_query.append(
        {
          "query": {
            "multi_match": {
              "query": name[0],
              "fields": ['middle_name', 'middle_name_compact']
            }
          }
        })
    return middle_match_scoring_query
  middle_match_scoring_query = get_middle_match_scoring_query_helper(name)
  middle_match_scoring_query.extend(get_middle_match_scoring_query_helper(alternative_name))
  return wrap_query_list_if_needed(middle_match_scoring_query, "or")

def get_name_match_scoring_queries(name_parts, alternative_name_parts,
                                   last_name, alternative_last_name):
  """Return scoring queries based on user name

  Maximal possible location score: 10

  Non-exact first name match (synonyms and/or compact) +5
  Exact first name match +2
  Fuzzy middle name match +2
  Last name match +1 (all users should get it, as it a filter condition)
  """
  name_scoring_queries = []
  last_name_match_scoring_query = \
      get_last_name_match_scoring_query (name_parts, alternative_name_parts,
                                         last_name, alternative_last_name)
  if last_name_match_scoring_query:
    name_scoring_queries.append(
      {
        "filter" : last_name_match_scoring_query,
        "boost_factor": "1"
      })
  first_name_non_exact_match_scoring_query = \
      get_non_exact_name_match_scoring_query(
          "first_name", name_parts["first_name"],
          alternative_name_parts["first_name"])
  if first_name_non_exact_match_scoring_query:
    name_scoring_queries.append(
      {
        "filter" : first_name_non_exact_match_scoring_query,
        "boost_factor": "5"
      })
  first_name_exact_match_scoring_query = \
      get_exact_name_match_scoring_query(
          "first_name", name_parts["first_name"],
          alternative_name_parts["first_name"])
  if first_name_exact_match_scoring_query:
    name_scoring_queries.append(
      {
        "filter" : first_name_exact_match_scoring_query,
        "boost_factor": "2"
      })
  first_name_non_exact_middle_match_scoring_query = \
      get_non_exact_name_match_scoring_query(
          "middle_name", name_parts["first_name"],
          alternative_name_parts["first_name"])
  if first_name_non_exact_middle_match_scoring_query:
    name_scoring_queries.append(
      {
        "filter" : first_name_non_exact_middle_match_scoring_query,
        "boost_factor": "2"
      })
  if not name_parts['middle_name']:
    name_scoring_queries.append(
      {
        "filter" : {
          "missing": {
            "field": "middle_name"
          }
        },
        "boost_factor": "1"
      })
  else:
    middle_match_scoring_query = \
      get_middle_match_scoring_query(
          name_parts["middle_name"], alternative_name_parts["middle_name"])

    if middle_match_scoring_query:
      name_scoring_queries.append(
      {
        "filter" : middle_match_scoring_query,
        "boost_factor": "1"
      })
  return name_scoring_queries


# FIXME - These numbers are very magic-y.
# Minimal score for auto verification is much higher than admin since admin
# has no precision considerations.
def get_min_score(search_type, dob):
  if search_type == SEARCH_TYPE_AUTO_VERIFY:
    if dob:
      return MIN_SCORE_AUTO_VERIFY_WITH_DOB
    else:
      return MIN_SCORE_AUTO_VERIFY_WITHOUT_DOB
  elif search_type == SEARCH_TYPE_TOP:
    return MIN_SCORE_TOP
  elif search_type == SEARCH_TYPE_DISCOVER:
    return MIN_SCORE_DISCOVER
  else:
    # We should never get here, but just in case.
    return 0


def raw_elastic_voters(first_name='',
                       middle_name=None,
                       last_name='',
                       alternative_first_name='',
                       alternative_middle_name=None,
                       alternative_last_name='',
                       dob=None,
                       search_type=DEFAULT_SEARCH_TYPE,
                       address=None,
                       city=None,
                       state=None,
                       zip_code=None,
                       exclude=None,
                       limit=None,
                       confident_only=True,
                       index=INDEX,
                       doc_type=DOC_TYPE):
  """
  Return the voters from ES matching the given information.

  Return the raw ES results, not APIVoter objects.

  If last name, DOB, or state are given, anything returned is *required*
  to match them (with some fuzz on DOB). This is for performance reasons
  (so we don't have to scan and rank the whole corpus), but there might
  be accuracy fallout from removing this requirement, too.

  :arg dob: A NullableDate
  :arg confident_only: If True, restrict the result set to matches we're
      reasonably confident of.
  :arg dob_day_of_year_must_match: If True, filter results down to ones
      that match (with the applicable fuzziness) the ``dob_day_of_year``.
      This provides a performance boost. Note that results will not
      include voters whose DOB is unknown.
  :arg index: The name of the ES index where voters are stored
  :arg doc_type: The doctype of voter documents in ES
  """
  if not limit:
    limit = VERIFIER_MAX_RESULTS

  name_parts = get_name_parts(first_name, middle_name or '', last_name, '')
  alternative_name_parts = get_name_parts(alternative_first_name,
                                          alternative_middle_name or '',
                                          alternative_last_name, '')

  last_name_for_query = name_parts['last_name'] or last_name or \
      alternative_name_parts['last_name'] or alternative_last_name

  # regardless of search type, search should not run without a last name,
  # as it can hang es (location search for the entire voter base is expensive)
  if not last_name_for_query:
    raise NotEnoughData

  if state:
    state = state.upper()
  zip_code = get_five_digit_zip_code(zip_code)

  # The things that MUST be true of returned results:
  filters = []
  filters.append(get_last_name_filter_query(
      last_name, alternative_last_name,
      name_parts, alternative_name_parts))
  if search_type == SEARCH_TYPE_AUTO_VERIFY:
    filters.append(get_auto_verify_filter_query(
        name_parts, alternative_name_parts, dob, zip_code))
  if search_type == SEARCH_TYPE_TOP:
    filters.append(get_name_filter_query(name_parts, alternative_name_parts))
  if search_type == SEARCH_TYPE_DISCOVER and state:
    # We do not filter AUTO_VERIFY using state, as people sometimes move
    # close by but over state lines.
    filters.append(get_state_filter_query(state))
  if dob and dob.year and isinstance(dob.year, Number):
    filters.append(get_dob_within_range_filter_query(dob.year, 1))

  if exclude:
    filters.append({
      "not": {
        "ids": {
          "values": exclude
        }
      }
    })

  # This is the scoring function. Handwavey magic happens here.
  # Generally, socre is composed of 3 diffent aspects, each contributes
  # up to 10 points:
  # 1. Name Match
  # 2. DoB match
  # 3. Location match
  scoring_query = []
  scoring_query.extend(get_name_match_scoring_queries(name_parts,
                                                      alternative_name_parts,
                                                      last_name,
                                                      alternative_last_name))
  if dob:
    scoring_query.extend(get_dob_scoring_queries(dob))
  location_match_scoring_queries = \
      get_location_match_scoring_queries(address, city, state, zip_code)
  if location_match_scoring_queries:
    scoring_query.extend(location_match_scoring_queries)

  query = {
    "size": limit,
    "query": {
      # A "filtered" query lets us do fuzzy matching (the "query" part)
      # against a ilmited subset of the corpus (the "filter" part).
      "filtered": {
        "filter": {
          # Here are the things that MUST be true. We match them exactly.
          # Maybe think about adding a little Levenshtein slop.
          "and": filters
        },
        "query": {
          # After we've matched the required stuff above, give bonus
          # points for matching any of this other stuff.
          #
          # This "custom_filters_score" query starts with the full corpus
          # ("match_all") and then essentially sorts them by the number
          # of filters that match, weighted by the given boost factors.
          "function_score": {
            "query": {
              # Start with everything. We don't match the address
              # here because we want it to be a peer with the other
              # "bonus points" items like date of birth. I'm not sure
              # how it would behave if we put it here.
              "match_all": {}
            },
            # Increase the score for each of these things that matches:
            "functions": scoring_query,
            # FIXME: Think about using "multiply" instead plus some
            # fractional boosts to implement punishment for mismatches.
            # (We'd have to differentiate between nulls and mismatches
            # explicitly.)
            #
            # An alternate way to model this query would be to use the
            # "first" score_mode and just put ANDs of sets of matchers
            # in order. First, have a set that demands a match on
            # everything. Next, have one with less. Etc.
            "score_mode": "sum"
          }
        }
      }
    }
  }
    #if confident_only:
    # FIXME: Make matching more intelligent, and raise this.
    # Conceptually, this is 5.0, but either ES treats this as "greater
    # than", or the float compare is fiddly.
    #
    # This is lowered if we're requiring dob_day_of_year to match,
    # giving those voters the same effective boost as if this criterion
    # had been a "might".
  query['min_score'] = 1.0
  return es_client.search(query,
                          index=index,
                          doc_type=doc_type)


def match_many(first_name='', middle_name=None, last_name='', contact_id=None, user_id=None,
               politician_id=None, dob=None, max_matches=None, search_type=DEFAULT_SEARCH_TYPE, **kwargs):
  """
  Return a list of voter IDs matching the criteria as well as possible,
  [] if none matches.

  Only results over a certain confidence level will be returned.

  For further documentation and rationale please see -
***REMOVED***

  See ``raw_elastic_voters()`` for more argument documentation.
  """
  # If search_type is unknown, revert to default.
  if search_type not in [SEARCH_TYPE_DISCOVER,
                         SEARCH_TYPE_TOP,
                         SEARCH_TYPE_AUTO_VERIFY]:
    search_type = DEFAULT_SEARCH_TYPE

  try:
    dob = normalize_dob(dob)
  except TooYoungToVote:
    return []

  # Get ES results:
  try:
    results = raw_elastic_voters(
        first_name, middle_name, last_name,
        search_type=search_type, dob=dob, limit=max_matches, **kwargs)
  except NotEnoughData:
    return []
  hits = results['hits']['hits']
  took = results['took']
  statsd.histogram('verifier.es_query_time.match_many', took / 1000.0)

  if search_type == SEARCH_TYPE_AUTO_VERIFY:
    min_score_for_verfication = get_min_score(search_type, dob)
    hits = filter_lower_confidence_for_auto_verification(
        hits, min_score_for_verfication)
  if max_matches:
    hits = filter_match_groups(hits, max_matches)
  logger.info('match_many found %s matches for \n'
              '    first_name=%s\n'
              '    middle_name=%s\n'
              '    last_name=%s\n'
              '    dob=%s\n'
              '    address=%s\n'
              '    city=%s\n'
              '    state=%s\n'
              '    zip_code=%s\n'
              '    exclude=%s\n'
              '    contact_id=%s\n'
              '    user_id=%s\n'
              '    politician_id=%s',
              len(hits), first_name, middle_name, last_name, dob,
              kwargs.get('address'), kwargs.get('city'),
              kwargs.get('state'), kwargs.get('zip_code'),
              kwargs.get('exclude'), contact_id, user_id, politician_id)

  return [from_elasticsearch_mapping(hit) for hit in hits]


def match_one(first_name='', middle_name=None, last_name='', dob=None, **kwargs):
  """
  Return the ID of the closest-matching voter.

  Return None if we can't decide, we can't match any, or the passed-in date
  of birth is too young to vote. Compare scores of top 2 results and make
  sure there's a decent spread between them. Otherwise, we cannot confidently
  say that the first one is better than the second.

  See ``raw_elastic_voters()`` for more argument documentation.
  """
  # It might be nice to raise TooYoungToVote to the outside someday.
  hits = match_many(first_name, middle_name, last_name, **kwargs)
  return hits[0] if hits and len(hits) == 1 else []


def lookup_by_email(email, max_hits):
  """ find voter records for a given email address """
  if not email:
    return []

  query = {
    'size': max_hits,
    'query': { 'constant_score': { 'filter' : { 'term' : { 'email': email } } } }
  }
  results = es_client.search(query, index=INDEX, doc_type=DOC_TYPE)
  took = results['took']
  statsd.histogram('verifier.es_query_time.lookup_by_email', took / 1000.0)

  return [format_contact(hit) for hit in results['hits']['hits']]

def lookup_by_phone(input_phone, max_hits):
  """ find voter records for a given phone number
       US phone numbers are 10 numeric digits
      Strips any leading "+1"
  """
  phone = input_phone.replace('+', '')[-10:] if input_phone else ''
  if not phone:
    return []

  query = {
    'size': max_hits,
    'query': {
      "constant_score":{
        "filter": {
          "bool" : {
            "should": [
              { "term": { "phone": phone } },
              { "term": { "vb_phone": phone } },
              { "term": { "vb_phone_wireless": phone } },
              { "term": { "ts_wireless_phone": phone } }
            ]
          }
        }
      }
    }
  }
  results = es_client.search(query, index=INDEX, doc_type=DOC_TYPE)
  took = results['took']
  statsd.histogram('verifier.es_query_time.lookup_by_phone', took / 1000.0)

  return [format_contact(hit) for hit in results['hits']['hits']]

def filter_lower_confidence_for_auto_verification(
    hits, min_score_for_verification):
  """Return a single result if we have high confidence with the match.

  If no result meets the minimal score bar return no results.
  If a result meets the minimal bar, but the following result has
  a similar score, return both results.

  Clients should auto verify only if a single result is returned and
  the auto_verify response param is set to "true".

  """
  # Zero results back from ES
  if not hits:
    return []

  # Top result does not reach the bar. Return nothing.
  if hits[0]['_score'] < min_score_for_verification:
    return []

  # Either single good result or large enough gap from second result.
  # Return list containing first result only.
  if len(hits) == 1 or \
      hits[0]['_score'] - hits[1]['_score'] >= CONFIDENCE_INTERVAL_FOR_AUTO_VERIFICATION:
    hits[0]['_auto_verify'] = True
    return [hits[0]]

  # In all other cases, return empty list.
  return []


def filter_match_groups(hits, max_hits):
  """
  This method filters a list of hits (sorted by _score, descending) into a
  smaller set of matches that we can be confident about.

  This generalizes the original notion present in the match_one method to
  only return a match if it is more than a CONFIDENCE_INTERVAL better-scored
  than the next result. To support returning multiple results, this method
  groups the results with all results within a CONFIDENCE_INTERVAL of the
  first result in the first group, all results within a CONFIDENCE_INTERVAL
  of the next result in the second group, and so on.

  If we cannot be confident about fewer than max_hits hits, we will return an
  empty array.
  """

  # Require this much score difference to pick one result over another:
  CONFIDENCE_INTERVAL = 2

  if len(hits) <= max_hits:
    return hits

  current_score = hits[0]['_score']
  return_hits = []

  # a group is a set of matches where no two matches differ by more than
  # CONFIDENCE_INTERVAL, e.g. [15, 15, 14, 7, 7, 3] would be separated into
  # groups:
  # [15, 15, 14], [7, 7], [3]
  current_group = []

  for hit in hits:
    score_diff = current_score - hit['_score']
    if score_diff < CONFIDENCE_INTERVAL:
      current_group.append(hit)
    else:
      # append the current group to the "max_hits" results only if it keeps
      # us under the threshhold
      if len(return_hits) + len(current_group) <= max_hits:
        return_hits = return_hits + current_group
      else:
        break
    current_score = hit['_score']

  # we intentionally ignore the possibly-nonempty current_group array, since
  # it would have been appendend to the result set if we were more confident
  # in those results than the next set

  return return_hits
