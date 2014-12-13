from datetime import datetime
from flask import Flask, request
from functools import wraps
from jsonschema import Draft4Validator
import json
import os

***REMOVED***
***REMOVED***

app = Flask(__name__)
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


@app.route('/')
def home():
    return """
    <form method='POST' action='/match'>
      ***REMOVED***
      ***REMOVED***
      <input name='dob' value='1991-01-01' placeholder='DOB (yyyy-mm-dd)' />
      <input type='submit' />
    </form>
    """


@app.route('/v1/voters/<id>', methods=['GET'])
def find_voter(id):
    """
    Find a voter by voterbase ID.

    TODO: Implement this.
    """
    return str(id)


@app.route('/v1/voters/search', methods=['POST'])
@validate_api_request
def search(params):
    """
    Match a chunk of user-inputted information (name, address, dob, etc.) to an
    entry in a voter roll.
    """
    if 'dob' in params['user']:
        params['user']['dob'] = datetime.strptime(params['user']['dob'], "%Y-%m-%d")

    return json.dumps({'data': match_many(**params['user'])})


@app.route('/health', methods=['GET'])
@app.route('/health/<kind>', methods=['GET'])
def health(kind=None):
    """
    Does a simple health-check of this service's ability to do real work.
    """

    status = es_client.status(INDEX)
    if status['indices'][INDEX]['docs']['num_docs'] > 0:
        es_status = 'OK'
        code = 200
    else:
        es_status = 'ERROR Cluster status: {0}'.format(status)
        code = 503

    if kind == 'status':
        return json.dumps({
            'elasticsearch': es_status,
            'revision': open('REVISION').read().strip()
        }), code
    else:
        return es_status, code


if __name__ == '__main__':
    app.debug = os.environ.get('FLASK_ENV', 'development') == 'development'

    app.run(host='0.0.0.0')
