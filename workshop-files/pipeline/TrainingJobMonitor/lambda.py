import boto3
import io
import os
import logging
from botocore.exceptions import ClientError

sm = boto3.client('sagemaker')
cw = boto3.client('events')
cp = boto3.client('codepipeline')

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
    logger.debug("## Environment Variables ##")
    logger.debug(os.environ)
    logger.debug("## Event ##")
    logger.debug(event)
    pipeline_name = os.environ['PIPELINE_NAME']
    model_name = os.environ['MODEL_NAME']
    result = None
    token = None
    try:
        response = cp.get_pipeline_state(name=pipeline_name)
        for stageState in response['stageStates']:
            if stageState['stageName'] == 'TrainApproval':
                for actionState in stageState['actionStates']:
                    if actionState['actionName'] == 'ApproveTrain':
                        latestExecution = actionState['latestExecution']
                        executionId = stageState['latestExecution']['pipelineExecutionId']
                        if latestExecution['status'] != 'InProgress':
                            raise(Exception("Train approval is not awaiting approval: {}".format(latestExecution['status'])))
                        token = latestExecution['token']
        if token is None:
            raise(Exception("Action token wasn't found. Aborting..."))
        response = sm.describe_training_job(
            TrainingJobName="mlops-{}-{}".format(model_name, executionId)
        )
        status = response['TrainingJobStatus']
        logger.info(status)
        if status == "Completed":
            result = {
                'summary': 'Model trained successfully',
                'status': 'Approved'
            }
        elif status == "InProgress":
            return "Training Job ({}) in progress".format(executionId)
        else:
            result = {
                'summary': response['FailureReason'],
                'status': 'Rejected'
            }
    except Exception as e:
        result = {
            'summary': str(e),
            'status': 'Rejected'
        }
    
    try:
        response = cp.put_approval_result(
            pipelineName=pipeline_name,
            stageName='TrainApproval',
            actionName='ApproveTrain',
            result=result,token=token
        )
    except ClientError as e:
        error_message = e.response["Error"]["Message"]
        logger.error(error_message)
        raise Exception(error_message)

    try:
        response = cw.disable_rule(Name="training-job-monitor-{}".format(model_name))
    except ClientError as e:
        error_message = e.response["Error"]["Message"]
        logger.error(error_message)
        raise Exception(error_message)
    
    return "Done!"