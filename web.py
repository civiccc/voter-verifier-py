from flask import Flask, request
from functools import wraps
import json
from jsonschema import Draft4Validator

***REMOVED***

app = Flask(__name__)


def validate_api_request(response_continuation):
    @wraps(response_continuation)
    def with_validation():
        schema = json.loads(open('schema.json', 'r').read())
        method = request.method
        path = request.path
        params = request.get_json()

        request_schema = None
        for chunk_name, chunk in schema["definitions"].items():
            if "links" not in chunk:
                continue
            for endpoint in chunk["links"]:
                if endpoint["href"] == path and endpoint["method"] == method:
                    request_schema = endpoint["schema"]

        if request_schema is None:
            print "Couldn't find request schema for {0} {1}".format(method, path)
            return response_continuation(params)

        errors = list(Draft4Validator(schema).iter_errors(params, request_schema))

        if not errors:
            return response_continuation(params)
        else:
            error_str = json.dumps([{
                "message": error.message,
                "context": ".".join(error.absolute_path)} for error in errors])
            return error_str, 422

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


@app.route('/v1/voters/info', methods=['POST'])
@validate_api_request
def match(valid_api_params):
    return str(valid_api_params['id'])


@app.route('/v1/voters/search', methods=['POST'])
@validate_api_request
def search(valid_api_params):
    res = match_one(**valid_api_params['user'])

    return str(res)

if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0')
