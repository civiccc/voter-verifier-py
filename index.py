import csv
import sys
from pyelasticsearch import ElasticSearch
from progressbar import ProgressBar, Percentage, Bar, ETA, RotatingMarker, Counter

***REMOVED***
***REMOVED***


PII_map = {}     # key: voterbase_id,  value: the row
es_client = ElasticSearch(ES_HOSTS, TIMEOUT, RETRIES)


***REMOVED***
    private_row = row

    if not private_row:
        print 'WARN: Missing private row for voterbase_id: ' + row['voterbase_id']
        return {}

***REMOVED***
    return {
        'id': row['voterbase_id'],
***REMOVED***
***REMOVED***
***REMOVED***
        # Space-separated list of suffixes, like JR, SR, II, III, etc.
        # Not provided by votersmart
        'suffix': None,
        # One-line residence street address
***REMOVED***
        # Residence city
***REMOVED***
        # Residence state
***REMOVED***
        # First 5 digits of residence ZIP code
***REMOVED***
        'dob_year': int(dob[0:4]) or None,  # Year of birth
        'dob_month': int(dob[4:6]) or None,  # Month of birth
        'dob_day': int(dob[6:8]) or None,  # Day of birth
        # 'A'=Active, 'I'=Inactive, 'P'=Purged, 'D'=Deleted
        # TODO[tdooner]: Look for a way to get the other statuses in there
        'status_flag': 'A' if row['vb.vf_voter_status'] == 'Active' else 'I'
    }


if __name__ == '__main__':
    total_records = int(sys.argv[1])

    sys.stderr.write("Loading data...\n")

    headers = sys.stdin.readline().strip().split("\t")
    reader = csv.DictReader(sys.stdin, delimiter="\t", fieldnames=headers)
    voters = []

    for i, row in enumerate(reader):
        if all(row[x] == x for x in row):
            sys.stderr.write("Found header row.\n")
            continue

***REMOVED***

        if len(voters) >= 100000:
            progress = ProgressBar(widgets=[
                Counter(), Percentage(), Bar(marker=RotatingMarker()), ETA()],
                maxval=len(voters)).start()

            print "Indexing {0} voters...".format(len(voters))
            for i in index_voters(INDEX, voters, es_client, should_delete=True):
                progress.update(i)

            voters = []
