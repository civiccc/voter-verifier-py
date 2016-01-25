from datetime import datetime
from flask import Flask, request
from functools import wraps
from jsonschema import Draft4Validator
from raven import Client as RavenClient
import json
import os

***REMOVED***
***REMOVED***
***REMOVED***
***REMOVED***

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
    return "An exception occurred: %s" % (e,), 500

@app.route('/')
def home():
    return """
    <form id="test-form" method='POST' action='/match'>
      ***REMOVED***
      ***REMOVED***
      <input name='dob' value='1991-01-01' placeholder='DOB (yyyy-mm-dd)' /><br />
      ***REMOVED***
      ***REMOVED***
      ***REMOVED***
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

        var city = $("input[name=city]").val();
        if (city.length) {
          query["city"] = city;
        }

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

    TODO: Implement this.
    """
    return str(id)


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
        params['user']['dob'] = NullableDate(year=int(year), month=int(month), day=int(day))

    kwargs = params['user']
    if 'max_matches' in params:
        kwargs['max_matches'] = int(params['max_matches'])

    matches = match_many(**kwargs)
    resp = json.dumps({'data': matches}, sort_keys=True, indent=4, separators=(',', ': '))

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
***REMOVED***
***REMOVED***
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
