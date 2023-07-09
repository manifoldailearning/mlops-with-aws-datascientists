import os
import sys
import json
import re
import traceback
import tensorflow as tf
import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense
from tensorflow.keras.optimizers import Adam
from sklearn import preprocessing

tf.get_logger().setLevel('ERROR')

# Declare communication channel between Sagemaker and container
prefix = '/opt/ml'
# Sagemaker stores the dataset copied from S3
input_path = os.path.join(prefix, 'input/data')
# If something bad happens, write a failure file with the error messages and store here
output_path = os.path.join(prefix, 'output')
# Everything stored here will be packed into a .tar.gz by Sagemaker and copied into S3
model_path = os.path.join(prefix, 'model')
# These are the hyperparameters sent to the training algorithms through the Estimator
param_path = os.path.join(prefix, 'input/config/hyperparameters.json')


# Define function called for training
def train():
    print("Training mode ...")
    
    try:
        # This algorithm has a single channel of input data called 'training'. Since we run in
        # File mode, the input files are copied to the directory specified here.
        channel_name = 'training'
        training_path = os.path.join(input_path, channel_name)

        params = {}
        # Read in any hyperparameters that the are passed with the training job
        with open(param_path, 'r') as tc:
            is_float = re.compile(r'^\d+(?:\.\d+)$')
            is_integer = re.compile(r'^\d+$')
            for key,value in json.load(tc).items():
                # Workaround to convert numbers from string
                if is_float.match(value) is not None:
                    value = float(value)
                elif is_integer.match(value) is not None:
                    value = int(value)
                params[key] = value

        # Confirm that training files exists and the channel was correctly configured
        input_files = [ os.path.join(training_path, file) for file in os.listdir(training_path) ]
        if len(input_files) == 0:
            raise ValueError(('There are no files in {}.\\n' +
                              'This usually indicates that the channel ({}) was incorrectly specified,\\n' +
                              'the data specification in S3 was incorrectly specified or the role specified\\n' +
                              'does not have permission to access the data.').format(training_path, channel_name))
        
        # Specify the Column names in order to manipulate the specific columns for pre-processing
        column_names = ["rings", "length", "diameter", "height", "whole weight", 
                "shucked weight", "viscera weight", "shell weight", "sex_F", "sex_I", "sex_M"]
        
        # Load the training dataset
        train_data = pd.read_csv(os.path.join(training_path, 'train.csv'), sep=',', names=column_names)
        
        # Load the validation dataset
        val_data = pd.read_csv(os.path.join(training_path, 'validate.csv'), sep=',', names=column_names)

        # Split the data for training features vs. predictor
        train_y = train_data['rings'].to_numpy()
        train_X = train_data.drop(['rings'], axis=1).to_numpy()
        val_y = val_data['rings'].to_numpy()
        val_X = val_data.drop(['rings'], axis=1).to_numpy()

        # Normalize the data
        train_X = preprocessing.normalize(train_X)
        val_X = preprocessing.normalize(val_X)
        
        # Prevent overtraining to minimize model overfitting the data
        early_stop = keras.callbacks.EarlyStopping(monitor='val_loss', patience=10)
        
        # Build the DNN layers
        algorithm = 'TensorflowRegression'
        print("Training Algorithm: %s" % algorithm)
        # Initialize weight tensors with a normal "Xavier" distribution
        initializer = tf.keras.initializers.GlorotNormal()
        dense_layers = []
        # Build Deep layers
        for layer in range(int(params.get('layers'))):
            if layer == 0:
                dense_layers.append(Dense(params.get('dense_layer'), kernel_initializer=initializer, input_dim=10))
            else:
                dense_layers.append(Dense(params.get('dense_layer'), activation='relu'))
        # Add final linear `pass-through` layer
        dense_layers.append(Dense(1, activation='linear'))
        
        # Build the model
        model = Sequential(dense_layers)
        model.summary()
        
        # Compile and train the model
        model.compile(loss='mse', optimizer='adam', metrics=['mae','accuracy'])
        model.fit(
            train_X,
            train_y,
            validation_data=(val_X, val_y),
            batch_size=params.get('batch_size'),
            epochs=params.get('epochs'),
            shuffle=True,
            verbose=1,
            callbacks=[early_stop]
        )
        
        # Save the model as a single 'h5' file without the optimizer
        print("Saving Model ...")
        model.save(
            filepath=os.path.join(model_path, 'model.h5'),
            overwrite=True,
            include_optimizer=False,
            save_format="h5"
        )

    except Exception as e:
        # Write out an error file. This will be returned as the failureReason in the
        # `DescribeTrainingJob` result.
        trc = traceback.format_exc()
        with open(os.path.join(output_path, 'failure'), 'w') as s:
            s.write('Exception during training: ' + str(e) + '\\n' + trc)
            
        # Printing this causes the exception to be in the training job logs, as well.
        print('Exception during training: ' + str(e) + '\\n' + trc, file=sys.stderr)
        
        # A non-zero exit code causes the training job to be marked as Failed.
        sys.exit(255)

# Define function called for local testing
def predict(payload, algorithm):
    print("Local Testing Mode ...")
    if algorithm is None:
        raise ValueError("Please provide the algorithm specification")
    payload = np.asarray(payload) # Convert the payload to numpy array
    payload = payload.reshape(1, -1) # Vectorize the payload
    return algorithm.predict(payload).tolist()