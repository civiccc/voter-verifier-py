from datetime import datetime
from flask import Flask, request
from functools import wraps
from jsonschema import Draft4Validator
from pyelasticsearch import ElasticHttpNotFoundError
from raven import Client as RavenClient
from sets import Set
import json
import os

import traceback


from verifier_date_utils import NullableDate
from voter_verifier.matching import from_elasticsearch_mapping, match_many, lookup_by_email, lookup_by_phone, es_client, statsd
from voter_verifier.random_matching import match_random_addresses, es_client
from voter_verifier.config import INDEX, SENTRY_DSN, DOC_TYPE

app = Flask(__name__)
sentry = RavenClient(SENTRY_DSN)
validator = None


def validate_api_request(response_continuation):
  global validator
  if not validator:
    validator = Draft4Validator(json.loads(open('schema.json', 'r').read()))

  @wraps(response_continuation)
  def with_validation():
    method = request.method
    path = request.path

    for chunk in validator.schema["definitions"].values():
      if "links" not in chunk:
        continue
      link_matches = lambda l: l["href"] == path and l["method"] == method
      request_schema = next((l for l in chunk["links"] if link_matches(l)), {}).get('schema')

    params = request.get_json()

    if request_schema is None:
      print "Couldn't find request schema for {0} {1}".format(method, path)
      return response_continuation()

    errors = list(validator.iter_errors(params, request_schema))

    if not errors:
      return response_continuation(params)

    return json.dumps({"errors": [{
                       "message": error.message,
                       "context": ".".join(error.absolute_path)
        } for error in errors]}), 422

  return with_validation


"""
Register an error handler for any exception - we should report them to Sentry!

See: http://flask.pocoo.org/docs/0.10/api/#flask.Flask.errorhandler
"""
@app.errorhandler(Exception)
def handle_error(e):
  # We don't need to pass `e` into captureException() because sentry calls
  # `sys.exc_info()` which examines the thread's stack and gets exception
  # information "from the calling stack frame, or its caller, and so on until
  # a stack frame is found that is handling an exception."
  #
  # See: https://docs.python.org/2/library/sys.html#sys.exc_info
  #
  sentry.captureException()
  traceback.print_exc()
  return "An exception occurred: %s" % (e,), 500

@app.route('/')
def home():
  return """
  <form id="test-form" method='POST' action='/match'>
    <input name='first_name' value='Jane' placeholder='First Name' /><br />
    <input name='last_name' value='Smith' placeholder='Last Name' /><br />
    <input name='dob' value='1984-00-00' placeholder='DOB (yyyy-mm-dd)' /><br />
    <input name='zip_code' value='12345' placeholder='Zip Code' /><br />
    <input name='city' value='Anytown' placeholder='City (Euclid)' /><br />
    <input name='state' value='ST' placeholder='State (e.g. CA)' /><br />
    <input name='max_matches' value='3' placeholder='Maximum Number of Matches' />
    <input type='submit' />
  </form>
  <hr />

  <div id="result">No results.</div>

  <script src="https://code.jquery.com/jquery-2.1.3.min.js"></script>
  <script type="text/javascript">
    $("#test-form").on('submit', function(e) {
      e.preventDefault();
      var query = {
        "first_name": $("input[name=first_name]").val(),
        "last_name": $("input[name=last_name]").val(),
        "dob": $("input[name=dob]").val()
      };

      var zipCode = $("input[name=zip_code]").val();
      if (zipCode.length) {
        query["zip_code"] = zipCode;
      }

      var city = $("input[name=city]").val();
      if (city.length) {
        query["city"] = city;
      }

      query["search_type"] = "ADMIN";

      var state = $("input[name=state]").val();
      if (state.length) {
        query["state"] = state;
      }

      $("#result").html("");

      $.ajax({
        "url": "/v1/voters/search",
        "type": "POST",
        "contentType": "application/json",
        "data": JSON.stringify({
          "user": query,
          "max_matches": parseInt($("input[name=max_matches]").val())
        }),
      }).done(function(resp, status, xhr) {
        $("#result").html("<ul></ul>");

        var results = resp["data"];
        for (var i in results) {
          $("#result ul").append("<li>" + JSON.stringify(results[i]) + "</li>");
        }
      }).fail(function(xhr, status, error) {
        $("#result").html("<b>Error:</b> " + error);
        $("#result").append(xhr.responseText);
      });
    });
  </script>
  """

@app.route('/match_random_address')
def match_random_address():
  return """
  <form id="test-form" method='POST' action='/match'>
    <input name='state' value='MI' placeholder='State (MI)' /><br />
    <input name='seed' value='0' placeholder='seed value' />
    <input type='submit' />
  </form>
  <hr />

  <div id="result">No results.</div>

  <script src="https://code.jquery.com/jquery-2.1.3.min.js"></script>
  <script type="text/javascript">
    $("#test-form").on('submit', function(e) {
      e.preventDefault();
      var query = {
        "state": $("input[name=state]").val(),
        "seed": parseInt($("input[name=seed]").val())
      };

      $("#result").html("");

      $.ajax({
        "url": "/v1/voters/random_address",
        "type": "POST",
        "contentType": "application/json",
        "data": JSON.stringify({
          "address": query
        })
      ).done(function(resp, status, xhr) {
        $("#result").html("<ul></ul>");

        var results = resp["data"];
        for (var i in results) {
          $("#result ul").append("<li>" + JSON.stringify(results[i]) + "</li>");
        }
      }).fail(function(xhr, status, error) {
        $("#result").html("<b>Error:</b> " + error);
        $("#result").append(xhr.responseText);
      });
    });
  </script>
  """

@app.route('/v1/voters/<id>', methods=['GET'])
@statsd.timed('verifier.response_time.voters_find_voter', tags=['revision:v1'])
def find_voter(id):
  """
  Find a voter by voterbase ID.
  """
  try:
    hit = es_client.get(INDEX, DOC_TYPE, id)
  except ElasticHttpNotFoundError:
    return json.dumps({}), 404, {'Content-Type': 'application/json'}

  rec = hit['_source']
  if request.args.get('format', 'false').lower() == 'true':
      hit['_score'] = 0
      rec = from_elasticsearch_mapping(hit)

  return json.dumps(rec), 200, {'Content-Type': 'application/json'}


@app.route('/v1/voters/contact_search', methods=['POST'])
@statsd.timed('verifier.response_time.contact_search')
@validate_api_request
def contact_search(params):
  """ Match voter records by name, phone and email """
  max_matches = params.get('max_matches', 100)
  email = params.get('email', '')
  phone = params.get('phone', '')

  email_hits = lookup_by_email(email, max_matches) if email else []
  phone_hits = lookup_by_phone(phone, max_matches) if phone else []

  hits = []
  if not phone:
    hits = email_hits
  elif not email:
    hits = phone_hits
  else:
    # both email and phone were specified - take the intersection of their matches
    phone_ids = Set([hit['id'] for hit in phone_hits])
    hits = [ hit for hit in email_hits if hit['id'] in phone_ids]

  resp = json.dumps({'data': hits, 'num_results': len(hits), 'max_matches': max_matches},
                    sort_keys=True,
                    indent=4,
                    separators=(',', ': '))

  return resp, 200, {'Content-Type': 'application/json'}


@app.route('/v1/voters/search', methods=['POST'])
@statsd.timed('verifier.response_time.voters_search', tags=['revision:v1'])
@validate_api_request
def search(params):
  """
  Match a chunk of user-inputted information (name, address, dob, etc.) to an
  entry in a voter roll.
  """
  if 'dob' in params['user']:
    year, month, day = params['user']['dob'].split("-")
    params['user']['dob'] = NullableDate(year=int(year),
    month=int(month), day=int(day))

  kwargs = params['user']
  if 'max_matches' in params:
    kwargs['max_matches'] = int(params['max_matches'])
  if 'search_type' in params:
    kwargs['search_type'] = params['search_type']

  matches = match_many(**kwargs)
  resp = json.dumps({'data': matches, 'num results': len(matches)}, sort_keys=True, indent=4, separators=(',', ': '))

  return resp, 200, {'Content-Type': 'application/json'}

@app.route('/v1/voters/random_address', methods=['POST'])
@statsd.timed('verifier.response_time.voters_random_address', tags=['revision:v1'])
@validate_api_request
def random_address(params):
  """
  Submit a state to get random addresses in that state
  """

  address = params['address']
  matches = match_random_addresses(state=address['state'], seed=address['seed'])
  resp = json.dumps({'data': matches}, sort_keys=True, indent=4, separators=(',', ': '))

  return resp, 200, {'Content-Type': 'application/json'}

@app.route('/health', methods=['GET'])
@app.route('/health/<kind>', methods=['GET'])
@statsd.timed('verifier.response_time.health')
def health(kind=None):
  """
  Does a simple health-check of this service's ability to do real work.
  """

  status = es_client.status(INDEX)['indices']
  # We use index aliases to map "voter_verifier" ->
  # "voter_verifier_1234...". The real name is returned by the status
  # endpoint, so we'll just assume that if an index is returned here, it is
  # the correct one.
  status = status[status.keys()[0]]
  if status['docs']['num_docs'] > 0:
    es_status = 'OK'
    code = 200
  else:
    es_status = 'ERROR Cluster status: {0}'.format(status)
    code = 503

  if kind == 'status':
    return json.dumps({
      'elasticsearch': es_status,
      'revision': open('REVISION').read().strip()
    }), code, {'Content-Type': 'application/json'}
  else:
    return es_status, code


if __name__ == '__main__':
  app.debug = os.environ.get('FLASK_ENV', 'development') == 'development'

  app.run(host='0.0.0.0')
