import os
import sys
import boto3
import numpy as np
import pandas as pd
import sklearn
from awsglue.utils import getResolvedOptions
from io import StringIO

# Helper function to split dataset (80/19/1)
def split_data(df, train_percent=0.8, validate_percent=0.19, seed=None):
    np.random.seed()
    perm = np.random.permutation(df.index)
    m = len(df.index)
    train_end = int(train_percent * m)
    validate_end = int(validate_percent * m) + train_end
    train = df.iloc[perm[:train_end]]
    validate = df.iloc[perm[train_end:validate_end]]
    test = df.iloc[perm[validate_end:]]
    return [('train', train), ('test', test), ('validate', validate), ('baseline', train)]

# Get job args
args = getResolvedOptions(sys.argv, ['S3_INPUT_BUCKET', 'S3_INPUT_KEY_PREFIX', 'S3_OUTPUT_BUCKET', 'S3_OUTPUT_KEY_PREFIX'])

# Downloading the data from S3 into a Dataframe
column_names = ["sex", "length", "diameter", "height", "whole weight",  
                "shucked weight", "viscera weight", "shell weight", "rings"]
client = boto3.client('s3')
bucket_name = args['S3_INPUT_BUCKET']
object_key = os.path.join(args['S3_INPUT_KEY_PREFIX'], 'abalone.csv')
print("Downloading input data from S3 ...\n")
csv_obj = client.get_object(Bucket=bucket_name, Key=object_key)
body = csv_obj['Body']
csv_string = body.read().decode('utf-8')
data = pd.read_csv(StringIO(csv_string), sep=',', names=column_names)

# Re-order data to better separate features
data = data[["rings", "sex", "length", "diameter", "height", "whole weight", 
                "shucked weight", "viscera weight", "shell weight"]]

# Create dummy variables for categorical `sex` feature using pandas
print("Encoding Features ...\n")
data = pd.get_dummies(data)

# Create train, test and validate datasets
print("Creating dataset splits ...\n")
datasets = split_data(data)

# Upload data to S3 as .csv file while separating validation set
for file_name, partition_name in datasets:
    if file_name == 'test':
        print("Writing {} data ...\n".format(file_name))
        np.savetxt(file_name+'.csv', partition_name, delimiter=',')
        boto3.Session().resource('s3').Bucket(args['S3_OUTPUT_BUCKET']).Object(os.path.join(args['S3_OUTPUT_KEY_PREFIX'], 'testing', file_name+'.csv')).upload_file(file_name+'.csv')
    elif file_name == 'baseline':
        print("Writing {} data ...\n".format(file_name))
        np.savetxt(
            file_name+'.csv',
            partition_name,
            delimiter=',',
            header="rings,length,diameter,height,whole weight,shucked weight,viscera weight,shell weight,sex_F,sex_I,sex_M"
        )
        boto3.Session().resource('s3').Bucket(args['S3_OUTPUT_BUCKET']).Object(os.path.join(args['S3_OUTPUT_KEY_PREFIX'], 'baseline', file_name+'.csv')).upload_file(file_name+'.csv')
    else:
        print("Writing {} data ...\n".format(file_name))
        np.savetxt(file_name+'.csv', partition_name, delimiter=',')
        boto3.Session().resource('s3').Bucket(args['S3_OUTPUT_BUCKET']).Object(os.path.join(args['S3_OUTPUT_KEY_PREFIX'], 'training', file_name+'.csv')).upload_file(file_name+'.csv')

print("Done writing to S3 ...\n")