
import flask
from flask import request, make_response, abort
from flask_cors import cross_origin, CORS
from logging.handlers import RotatingFileHandler

from methods import evaluate_text, introspect_token, train_data

import json
import logging
import os

app = flask.Flask(__name__)

logging.basicConfig(level=logging.INFO)

handler = RotatingFileHandler(os.path.join(app.root_path, 'logs', 'error_log.log'), maxBytes=102400, backupCount=10)
logging_format = logging.Formatter('%(asctime)s - %(levelname)s - %(filename)s - %(funcName)s - %(lineno)s - %(message)s')
handler.setFormatter(logging_format)
app.logger.addHandler(handler)

cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

def validate_token():
    if 'Authorization' not in request.headers:
        abort(401)

    auth_header = request.headers['Authorization']
    if auth_header == None:
        abort(401)
    
    token = auth_header.split(' ')
    if(token.__len__() != 2):
        abort(401)

    result = introspect_token(request.headers['Authorization'].split(' ')[1])
    if result == False:
        abort(401)
    
@app.route('/home', methods=['GET'])
@cross_origin()
def home():

    #validate_token()

    return "Willkommen, der Texterkennungsdienst läuft!"

@app.route('/evaluate', methods=['POST'])
@cross_origin()
def evaluate():

    validate_token()

    text = request.get_json(True)['text']

    result = evaluate_text(text).to_json()

    response = make_response(result)
    response.headers.remove('Content-Type')
    response.headers.add('Content-Type', 'application/json')

    return response


@app.route('/create-training-data', methods=['GET'])
@cross_origin()
def create_training_data():

    validate_token()

    trained_words = train_data()

    response = make_response(
        json.dumps({
            'word_counter': trained_words
        })
    )

    return response


class PrefixMiddleware(object):
    # class for URL sorting
    def __init__(self, app, prefix=''):
        self.app = app
        self.prefix = prefix

    def __call__(self, environ, start_response):
        # in this line I'm doing a replace of the word flaskredirect which is my app name in IIS to ensure proper URL redirect

        if environ['PATH_INFO'].lower().replace('/text-recognition', '').startswith(self.prefix):
            environ['PATH_INFO'] = environ['PATH_INFO'].lower().replace(
                '/text-recognition', '')[len(self.prefix):]
            environ['SCRIPT_NAME'] = self.prefix
            return self.app(environ, start_response)

        else:
            start_response('404', [('Content-Type', 'text/plain')])
            return ["This url does not belong to the app.".encode()]

app.wsgi_app = PrefixMiddleware(app.wsgi_app, prefix='')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9010, debug=True)
