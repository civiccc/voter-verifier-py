from flask import Flask, request
from datetime import datetime

***REMOVED***

app = Flask(__name__)


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


@app.route('/match', methods=['POST'])
def match():
    match_data = {
        "first_name": request.form['first_name'],
        "last_name": request.form['last_name'],
        "dob": datetime.strptime(request.form['dob'], "%Y-%m-%d"),
    }

    res = match_one(**match_data)

    return str(res)

if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0')
