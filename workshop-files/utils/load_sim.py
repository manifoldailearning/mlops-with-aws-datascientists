import threading
import boto3
import json
import time
import math
import os
from botocore.exceptions import ClientError
from multiprocessing.pool import ThreadPool
from datetime import datetime 
import numpy as np
import pandas as pd
from botocore.config import Config

# Global Variables
config = Config(retries = {'max_attempts': 10, 'mode': 'adaptive'})
sagemaker = boto3.client("sagemaker-runtime", config=config)
codepipeline = boto3.client('codepipeline')
s3 = boto3.client('s3')
pipeline_name = 'abalone-pipeline'
endpoint_name = 'abalone-prd-endpoint'
pipeline_bucket = '<PipelineBucket>'
obj = 'input/testing/test.csv'


# Helpr functions
def get_env_jobid(env='prd'):
    """
    Description:
    ------------
    Function to return the most up to date `pipelineExecitionId` based on the 
    environment input.
    
    :env: (str) Specifies either 'dev' or 'prd' environments.
    
    :returns: Latest CodePipeline Execution ID
    """
    try:
        response = codepipeline.get_pipeline_state(name=pipeline_name)
        for stage in response['stageStates']:
            if stage['stageName'] == 'Deploy%s' % env.capitalize():
                for action in stage['actionStates']:
                    if action['actionName'] == 'Deploy%sModel' % env.capitalize():
                        return stage['latestExecution']['pipelineExecutionId']
    except ClientError as e:
        error_message = e.response["Error"]["Message"]
        print(error_message)
        raise Exception(error_message)


# Invoke SageMaker endpoint
def predict(payload):
    """
    Description:
    ------------
    Invokes SageMaker endpoint with NumPy payload.

    :payload: (NumPy Array) Abalone datset observations as a NumPy Array.
    
    :returns: response (str) Python list containing the predicted age.
    """
    payload = ",".join(map(str, payload))
    try:
        request = sagemaker.invoke_endpoint(
            EndpointName=endpoint_name,
            ContentType = "text/csv",
            Body=payload
        )
    except ClientError as e:
        error_message = e.request["Error"]["Message"]
        print(error_message)
        raise Exception(error_message)
    return request['Body'].read().decode('utf-8').rstrip('\n')

# Execute inference test
def run_test(max_threads, max_requests, dataset):
    """
    Description:
    ------------
    Executes the inference testing.

    :max_threads: (int) Integer specifying the number of concurrent threads.
    :max_requests: (int) Integer specifying the the number of inference requests per thread.
    :dataset: (NumPy) Array of test data.
    """
    start_time = datetime.now() 
    num_batches = math.ceil(max_requests / len(dataset))
    requests = []
    for i in range(num_batches):
        batch = dataset.copy()
        np.random.shuffle(batch)
        requests += batch.tolist()
    pool = ThreadPool(max_threads)
    result = pool.map(predict, requests)
    pool.close()
    pool.join()
    elapsed_time = datetime.now() - start_time
    print("Time elapsed (hh:mm:ss.ms) {}".format(elapsed_time))

if __name__ == "__main__":
    # Get latest CodePipeline Execition ID
    job_id=get_env_jobid()

    # Download test dataset
    s3.download_file(pipeline_bucket, os.path.join(job_id, obj), 'test.csv')
    test_data = pd.read_csv('test.csv', header=None)
    test_data = test_data.drop(test_data.columns[0], axis=1)
    dataset = test_data.to_numpy()

    print("Starting test ...")
    run_test(150, 1000000, dataset)