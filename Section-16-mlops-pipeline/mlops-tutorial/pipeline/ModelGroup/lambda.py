import io
import json
import os
import logging
import urllib3
import boto3
from botocore.exceptions import ClientError

sm = boto3.client('sagemaker')
logger = logging.getLogger()
logger.setLevel(logging.INFO)
http = urllib3.PoolManager()
group_name = "{}PackageGroup".format(os.environ['MODEL_NAME'].capitalize())
SUCCESS = "SUCCESS"
FAILED = "FAILED"


def send(event, context, responseStatus, responseData, physicalResourceId=None, noEcho=False, error=None):
    responseUrl = event['ResponseURL']
    logger.info(responseUrl)
    responseBody = {}
    responseBody['Status'] = responseStatus
    if error is None: 
        responseBody['Reason'] = 'See the details in CloudWatch Log Stream: ' + context.log_stream_name + ' LogGroup: ' + context.log_group_name
    else:
        responseBody['Reason'] = error
    responseBody['PhysicalResourceId'] = physicalResourceId or context.log_stream_name
    responseBody['StackId'] = event['StackId']
    responseBody['RequestId'] = event['RequestId']
    responseBody['LogicalResourceId'] = event['LogicalResourceId']
    responseBody['NoEcho'] = noEcho
    responseBody['Data'] = responseData
    json_responseBody = json.dumps(responseBody)
    logger.info("Response body:\n" + json_responseBody)
    headers = {
        'content-type' : '',
        'content-length' : str(len(json_responseBody))
    }
    try:
        response = http.request('PUT',responseUrl,body=json_responseBody.encode('utf-8'),headers=headers)
        logger.info("Status code: " + response.reason)
    except Exception as e:
        logger.error("send(..) failed executing requests.put(..): " + str(e))


def create(event, context):
    logger.info("Creating model package group: {}".format(group_name))
    try:
        response = sm.create_model_package_group(
            ModelPackageGroupName=group_name,
            ModelPackageGroupDescription='Model Package Group for Production Models.',
            Tags=[
                {
                    'Key': 'Name',
                    'Value': group_name
                }
            ]
        )
    except ClientError as e:
        error_message = e.response["Error"]["Message"]
        logger.error("Failed to create model package group: {}".format(error_message))
        send(event, context, FAILED, {}, error=str(error_message))
    package_arn = response['ModelPackageGroupArn']
    send(event, context, SUCCESS, {'Arn': package_arn, 'Name': group_name}, physicalResourceId=package_arn)
    

def update(event, context):
    logger.info("Received update event")
    send(event, context, SUCCESS, {}, physicalResourceId=event['PhysicalResourceId'])


def delete(event, context):
    logger.info("Deleting model package group: {}".format(group_name))
    try:
        # Get a list of the model package versions
        response = sm.list_model_packages(
            ModelPackageGroupName=group_name,
            ModelApprovalStatus="Approved",
            SortBy="CreationTime",
            MaxResults=100,
        )
        # Delete model package versions
        for model_package in response["ModelPackageSummaryList"]:
            sm.delete_model_package(ModelPackageName=model_package['ModelPackageArn'])
        # Delete the package group
        sm.delete_model_package_group(ModelPackageGroupName=group_name)
    except ClientError as e:
        error_message = e.response["Error"]["Message"]
        logger.error("Failed to delete model package group: {}".format(error_message))
        send(event, context, FAILED, {}, error=str(error_message))
    send(event, context, SUCCESS, {}, physicalResourceId=event['PhysicalResourceId'])


def handler(event, context):
    logger.debug("Boto3 Version: {}".format(boto3.__version__))
    logger.debug("## Environment Variables ##")
    logger.debug(os.environ)
    logger.debug("## Event ##")
    logger.debug(event)
    if event['RequestType'] == 'Create':
        create(event, context)
    elif event['RequestType'] == 'Update':
        update(event, context)
    elif event['RequestType'] == 'Delete':
        delete(event, context)
