import boto3
import io
import zipfile
import json
import os
import logging

s3 = boto3.client('s3')
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
    trainingJob = None
    pipeline_name = os.environ['PIPELINE_NAME']
    model_name = os.environ['MODEL_NAME']
    jobId = event['CodePipeline.job']['id']
    accountId = event['CodePipeline.job']['accountId']
    region = os.environ.get('AWS_REGION')
    pipeline_bucket = "mlops-{}-{}".format(region, accountId)
    try:
        response = cp.get_pipeline_state(name=pipeline_name)
        for stageState in response['stageStates']:
            if stageState['stageName'] == 'Train':
                for actionState in stageState['actionStates']:
                    if actionState['actionName'] == 'TrainModel':
                        executionId = stageState['latestExecution']['pipelineExecutionId']
        logger.info("Start training job for 'jobid[{}]' and 'executionId[{}]'".format(jobId, executionId))
        for inputArtifacts in event["CodePipeline.job"]["data"]["inputArtifacts"]:
            if inputArtifacts['name'] == 'ModelSourceOutput':
                s3Location = inputArtifacts['location']['s3Location']
                zip_bytes = s3.get_object(Bucket=s3Location['bucketName'], Key=s3Location['objectKey'])['Body'].read()
                with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as z:
                    trainingJob = json.loads(z.read('trainingjob.json').decode('ascii'))
        if trainingJob is None:
            raise(Exception("'trainingjob.json' not found"))
        trainingJob['TrainingJobName'] = "mlops-{}-{}".format(model_name, executionId)
        trainingJob['OutputDataConfig']['S3OutputPath'] = os.path.join('s3://', pipeline_bucket, executionId)
        trainingJob['InputDataConfig'][0]['DataSource']['S3DataSource']['S3Uri'] = os.path.join('s3://', pipeline_bucket, executionId, 'input/training')
        trainingJob['Tags'].append({'Key': 'jobid', 'Value': jobId})
        logger.info(trainingJob)
        sm.create_training_job(**trainingJob)
        cw.enable_rule(Name="training-job-monitor-{}".format(model_name))
        cp.put_job_success_result(jobId=jobId)
    except Exception as e:
        logger.error(e)
        response = cp.put_job_failure_result(
            jobId=jobId,
            failureDetails={
                'type': 'ConfigurationError',
                'message': str(e),
                'externalExecutionId': context.aws_request_id
            }
        )
    
    return 'Done'