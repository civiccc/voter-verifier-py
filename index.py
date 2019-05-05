import os
import sys
import time
from pyelasticsearch import ElasticSearch
from progressbar import ProgressBar, Percentage, Bar, ETA, RotatingMarker, Counter

***REMOVED***
***REMOVED***


PII_map = {}     # key: voterbase_id,  value: the row
es_client = ElasticSearch(ES_HOSTS, TIMEOUT, RETRIES)

def address_mapping(row, header_map):
  """
  Extract address fields from the row.

  {
    'address': '123 S. FAKE ST. APT 456',
    'city': 'BEVERLY HILLS',
    'st': 'CA',
    'zip_code': '90210',
    'county': 'LOS ANGELES',
    'address_street_number': '123',
    'address_unit_designator': 'APT',
    'address_apt_number': '456',
  }

  We return 'address_street_number', 'address_unit_designator', and
  'address_apt_number' for use in anonymizing addresses during the
  verification flow.
  """
  # There are a couple different addresses that we might want to
  # use:
  #  ts_*:
  #    This is a best effort to provide a mailable/current address.
  #  unprefixed:
  #    The mailing address the voter listed on their registration. May be a PO
  #    Box, or "General Delivery".
  #
  # Each address includes the following fields, although they often call the
  # fields different names, so you should consult the "data dictionary" to get
  # these right in each case. Using the keys above as a prefix:
  #   (prefix)_full_address       The first line of an address ("123 S. Fake St.")
  #   (prefix)_city
  #   (prefix)_state
  #   (prefix)_zip                The 5 digit zip code
  #   (prefix)_zip4               The 4 digit zip code extension
  #   (prefix)_street_number      The street / house number.
  #   (prefix)_pre_directional
  #   (prefix)_street_name
  #   (prefix)_street_suffix      DR, AVE, RD, ...
  #   (prefix)_post_directional
  #   (prefix)_unit_designator    Apt, Unit, Ste, ...
  #   (prefix)_secondary_number   The apt/unit number.
  #
  # The 'county' field doesn't explicitly belong to any of these addresses:
  # it is simply listed as the "Voter File County Name".
  return {
    'address': row[header_map[]],
    'ts_address': row[header_map[]],
    'city': row[header_map[]],
    'ts_city': row[header_map[]],
    'st': row[header_map[]],
    'ts_st': row[header_map[]],
    'zip_code': row[header_map[]],
    'ts_zip_code': row[header_map[]],
    'county': row[header_map[]],
    'address_street_number': row[header_map[]],
    'ts_address_street_number': row[header_map[]],
    'address_unit_designator': row[header_map[]],
    'ts_address_unit_designator': row[header_map[]],
    'address_apt_number': row[header_map[]],
    'ts_address_apt_number': row[header_map[]],
  }


def input_mapping(row, header_map):
  dob = row[header_map[]] or "{0:>04}0000".format(row[header_map[<YEAR OF BIRTH ALONE>]] or 0)

  data = {
    'id': row[header_map[]],
    'first_name': row[header_map[]],
    'middle_name': row[header_map[]] or None,
    'last_name': row[header_map[]],
    'suffix': row[header_map[]],
    'dob_year': int(dob[0:4]) or None,  # Year of birth
    'dob_month': int(dob[4:6]) or None,  # Month of birth
    'dob_day': int(dob[6:8]) or None,  # Day of birth
    'registration_date': row[header_map[]] or None
    'party': row[header_map[]]
  }

***REMOVED***
  return data


def index_records(index_name, voters):
  progress = ProgressBar(widgets=[
      Counter(), Percentage(), Bar(marker=RotatingMarker()), ETA()],
      maxval=len(voters)).start()

  sys.stderr.write("Indexing {0} voters...\n".format(len(voters)))
  for i in index_voters(index_name, voters, es_client):
    progress.update(i)


if __name__ == '__main__':
  with aliased_index(es_client, INDEX) as index:
    sys.stderr.write("Loading data into index {0}...\n".format(index))
    sys.stderr.write("Set VOTER_VERIFIER_NEW_INDEX_NAME=[...] to override default index name.\n")

    voters = []
    for row in sys.stdin:
      row = row.decode("utf-8-sig").split("\t")
      header_map = {header: i for i, header in enumerate(row)}

      voters.append(input_mapping(row, header_map))

      if len(voters) >= 100000:
        index_records(index, voters)
        voters = []

    index_records(index, voters)
