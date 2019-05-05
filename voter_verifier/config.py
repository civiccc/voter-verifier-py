"""
Config settings that are hard-coded constants or from the application's
environment.
"""
import os

VERIFIER_MAX_RESULTS = 10
INDEX = os.environ.get('VERIFIER_INDEX_NAME', 'voter_verifier')
TIMEOUT = 15
RETRIES = 1
DOC_TYPE = 'voters'
ES_HOSTS = os.environ.get('ELASTICSEARCH_HOSTS', 'http://localhost:9200/').split(",")
STATSD_HOST = os.environ.get('STATSD_HOST', '127.0.0.1')
STATSD_PORT = 18125
SENTRY_DSN = os.environ.get('SENTRY_DSN', 'http://username:password@127.0.0.1/id')
ZIP_TO_LAT_LNG_FILE_NAME = 'voter_verifier/resources/zip_to_lat_lng.csv'

CONFIDENCE_INTERVAL_FOR_AUTO_VERIFICATION = 3

# Min scores for top result
MIN_SCORE_AUTO_VERIFY_WITH_DOB = 14.9
MIN_SCORE_AUTO_VERIFY_WITHOUT_DOB = 11.9
MIN_SCORE_TOP = 7.0
MIN_SCORE_DISCOVER = 0.9

# Optional search types
SEARCH_TYPE_DISCOVER = "DISCOVER"
SEARCH_TYPE_TOP = "TOP"
SEARCH_TYPE_AUTO_VERIFY = "AUTO_VERIFY"

# This is the default search type used when no search type,
# or unknown search type, is specified
DEFAULT_SEARCH_TYPE = SEARCH_TYPE_TOP
