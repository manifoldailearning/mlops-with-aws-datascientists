#!/usr/bin/env python

import json
import io
import sys
import os
import signal
import traceback
import flask
import multiprocessing
import subprocess
import tarfile
import model
import pandas as pd
import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense
from tensorflow.keras.optimizers import Adam
from sklearn import preprocessing

# Adds the model.py path to the list
prefix = '/opt/ml'
model_path = os.path.join(prefix, 'model')
sys.path.insert(0,model_path)
model_cache = {}

class PredictionService(object):
    tf_model = None
    @classmethod
    def get_model(cls):
        if cls.tf_model is None:
            cls.tf_model = load_model()
        return cls.tf_model

    @classmethod
    def predict(cls, input):
        tf_model = cls.get_model()
        return tf_model.predict(input)

def load_model():
    # Load 'h5' keras model
    model = tf.keras.models.load_model(os.path.join(model_path, 'model.h5'))
    model.compile(optimizer='adam', loss='mse')
    return model

def sigterm_handler(nginx_pid, gunicorn_pid):
    try:
        os.kill(nginx_pid, signal.SIGQUIT)
    except OSError:
        pass
    try:
        os.kill(gunicorn_pid, signal.SIGTERM)
    except OSError:
        pass

    sys.exit(0)

def start_server(timeout, workers):
    print('Starting the inference server with {} workers.'.format(model_server_workers))
    # link the log streams to stdout/err so they will be logged to the container logs
    subprocess.check_call(['ln', '-sf', '/dev/stdout', '/var/log/nginx/access.log'])
    subprocess.check_call(['ln', '-sf', '/dev/stderr', '/var/log/nginx/error.log'])

    nginx = subprocess.Popen(['nginx', '-c', '/opt/program/nginx.conf'])
    gunicorn = subprocess.Popen(['gunicorn',
                                 '--timeout', str(timeout),
                                 '-k', 'gevent',
                                 '-b', 'unix:/tmp/gunicorn.sock',
                                 '-w', str(workers),
                                 'wsgi:app'])

    signal.signal(signal.SIGTERM, lambda a, b: sigterm_handler(nginx.pid, gunicorn.pid))

    # If either subprocess exits, so do we.
    pids = set([nginx.pid, gunicorn.pid])
    while True:
        pid, _ = os.wait()
        if pid in pids:
            break

    sigterm_handler(nginx.pid, gunicorn.pid)
    print('Inference server exiting')

# The flask app for serving predictions
app = flask.Flask(__name__)

@app.route('/ping', methods=['GET'])
def ping():
    health = PredictionService.get_model() is not None
    status = 200 if health else 404
    return flask.Response(response='\n', status=status, mimetype='application/json')

@app.route('/invocations', methods=['POST'])
def invoke():
    data = None
    if flask.request.content_type == 'text/csv':
        """
        NOTE: print(flask.request.data) --> Bytes string
        """
        payload = np.fromstring(flask.request.data.decode('utf-8'), sep=',') # Convert `str` to `Numpy`
        data = payload.reshape(1, -1) # Vectorize the payload
    else:
        return flask.Response(response="Invalid request data type, only 'text/csv' is supported.", status=415, mimetype='text/plain')
    
    # Get predictions
    predictions = PredictionService.predict(data)

    # Convert from Numpy to CSV
    out = io.StringIO()
    pd.DataFrame({'results':predictions.flatten()}).to_csv(out, header=False, index=False)
    result = out.getvalue()
    print("Prediction Result: {}".format(result))
    return flask.Response(response=result, status=200, mimetype='text/csv')
    
 
if __name__ == '__main__':
    print("Tensorflow Version: {}".format(tf.__version__))
    if len(sys.argv) < 2 or ( not sys.argv[1] in [ "serve", "train", "test"] ):
        raise Exception("Invalid argument: you must specify 'train' for training mode, 'serve' for predicting mode or 'test' for local testing.") 

    train = sys.argv[1] == "train"
    test = sys.argv[1] == "test"

    if train:
        model.train()
        
    elif test:
        algo = 'TensorflowRegression'
        if model_cache.get(algo) is None:
            model_cache[algo] = load_model()
        req = eval(sys.argv[2])
        print(model.predict(req, model_cache[algo]))

    else:
        cpu_count = multiprocessing.cpu_count()
        model_server_timeout = os.environ.get('MODEL_SERVER_TIMEOUT', 60)
        model_server_workers = int(os.environ.get('MODEL_SERVER_WORKERS', cpu_count))
        start_server(model_server_timeout, model_server_workers)