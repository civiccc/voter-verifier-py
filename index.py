import sys
from pyelasticsearch import ElasticSearch
from progressbar import ProgressBar, Percentage, Bar, ETA, RotatingMarker, Counter

***REMOVED***
***REMOVED***


PII_map = {}     # key: voterbase_id,  value: the row
es_client = ElasticSearch(ES_HOSTS, TIMEOUT, RETRIES)


***REMOVED***
    dob = row[header_map['vb.vf_dob']] or "{0:>04}0000".format(row[header_map['vb.vf_yob']] or 0)

    return {
        'id': row[header_map['voterbase_id']],
***REMOVED***
***REMOVED***
***REMOVED***
        # Space-separated list of suffixes, like JR, SR, II, III, etc.
        # Not provided by votersmart
        'suffix': None,
        # One-line residence street address
        'address': row[header_map['vb.vf_reg_cass_address_full']],
        # The street number part of the address, which the client will remove
        # for anonymizing matches
        'address_street_number': row[header_map['vb.vf_reg_cass_street_num']],
        # Residence city
***REMOVED***
        # Residence state
***REMOVED***
        # First 5 digits of residence ZIP code
***REMOVED***
        'county': row[header_map['vb.vf_county_name']],
        'dob_year': int(dob[0:4]) or None,  # Year of birth
        'dob_month': int(dob[4:6]) or None,  # Month of birth
        'dob_day': int(dob[6:8]) or None,  # Day of birth
        # 'A'=Active, 'I'=Inactive, 'P'=Purged, 'D'=Deleted
        # TODO[tdooner]: Look for a way to get the other statuses in there
        'status_flag': 'A' if row[header_map['vb.vf_voter_status']] == 'Active' else 'I',
***REMOVED***
        'registration_date': row[header_map['vb.vf_registration_date']] or None
    }


def index_records(voters):
    progress = ProgressBar(widgets=[
        Counter(), Percentage(), Bar(marker=RotatingMarker()), ETA()],
        maxval=len(voters)).start()

    sys.stderr.write("Indexing {0} voters...\n".format(len(voters)))
    for i in index_voters(INDEX, voters, es_client):
        progress.update(i)


if __name__ == '__main__':
    ensure_mapping_exists(INDEX, es_client)

    sys.stderr.write("Loading data...\n")

    voters = []
    for row in sys.stdin:
        row = row.decode("utf-8-sig").split("\t")

        if row[0] == 'voterbase_id':
            sys.stderr.write("Found header row.\n")
            headers = row
            header_map = {header: i for i, header in enumerate(headers)}
            continue

***REMOVED***

        if len(voters) >= 1000000:
            index_records(voters)
            voters = []

    index_records(voters)
