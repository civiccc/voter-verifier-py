import sys
from pyelasticsearch import ElasticSearch
from progressbar import ProgressBar, Percentage, Bar, ETA, RotatingMarker, Counter

***REMOVED***
***REMOVED***


PII_map = {}     # key: voterbase_id,  value: the row
es_client = ElasticSearch(ES_HOSTS, TIMEOUT, RETRIES)

***REMOVED***
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
    # TargetSmart provides a couple different addresses that we might want to
    # use:
***REMOVED***
    #    This seems to be TargetSmart's best effort to provide a mailable address.
    #  vb.vf_reg*:
    #    The unparsed "registered" address; the voter's description of where
    #    they live, used for districting.
    #  vb.vf_reg_cass*:
    #    The "registered" address parsed by CASS (Coding Accuracy Support
    #    System)
    #  vb.vf_mail*:
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
    # We are choosing to use the CASS processed "registered" address, as this
    # seems most likely to provide good matches.
    #
    # The 'county' field doesn't explicitly belong to any of these addresses:
    # it is simply listed as the "Voter File County Name".
    return {
        'address': row[header_map['vb.vf_reg_cass_address_full']],
        'city': row[header_map['vb.vf_reg_cass_city']],
        'st': row[header_map['vb.vf_reg_cass_state']],
        'zip_code': row[header_map['vb.vf_reg_cass_zip']],
        'county': row[header_map['vb.vf_county_name']],
        'address_street_number': row[header_map['vb.vf_reg_cass_street_num']],
        'address_unit_designator': row[header_map['vb.vf_reg_cass_unit_designator']],
        'address_apt_number': row[header_map['vb.vf_reg_cass_apt_num']],
    }


***REMOVED***
    dob = row[header_map['vb.vf_dob']] or "{0:>04}0000".format(row[header_map['vb.vf_yob']] or 0)

    data = {
        'id': row[header_map['voterbase_id']],
***REMOVED***
***REMOVED***
***REMOVED***
        # Space-separated list of suffixes, like JR, SR, II, III, etc.
        # Not provided by votersmart
        'suffix': None,
        'dob_year': int(dob[0:4]) or None,  # Year of birth
        'dob_month': int(dob[4:6]) or None,  # Month of birth
        'dob_day': int(dob[6:8]) or None,  # Day of birth
        # 'A'=Active, 'I'=Inactive, 'P'=Purged, 'D'=Deleted
        # TODO[tdooner]: Look for a way to get the other statuses in there
        'status_flag': 'A' if row[header_map['vb.vf_voter_status']] == 'Active' else 'I',
***REMOVED***
        'registration_date': row[header_map['vb.vf_registration_date']] or None
    }

***REMOVED***
    return data


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
