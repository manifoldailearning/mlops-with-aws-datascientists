import boto3
import io
import zipfile
import json
import os
import logging

s3 = boto3.client('s3')
glue = boto3.client('glue')
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
    try:
        pipeline_name=os.environ['PIPELINE_NAME']
        model_name = os.environ['MODEL_NAME']
        jobId = event['CodePipeline.job']['id']
        accountId = event['CodePipeline.job']['accountId']
        region = os.environ.get('AWS_REGION')
        role = "arn:aws:iam::{}:role/MLOps".format(accountId)
        data_bucket = "data-{}-{}".format(region, accountId)
        output_bucket = "mlops-{}-{}".format(region, accountId)
        etlJob = None
        response = cp.get_pipeline_state(name=pipeline_name)
        for stageState in response['stageStates']:
            if stageState['stageName'] == 'ETL':
                for actionState in stageState['actionStates']:
                    if actionState['actionName'] == 'GlueJob':
                        executionId = stageState['latestExecution']['pipelineExecutionId']
        script_location = "s3://{}/{}/code/preprocess.py".format(output_bucket, executionId)
        job_name = "abalone-preprocess-{}".format(executionId)
        logger.info("Start Glue ETL Job for jobid[{}] executionId[{}]".format(jobId, executionId))
        for inputArtifacts in event["CodePipeline.job"]["data"]["inputArtifacts"]:
            if inputArtifacts['name'] == 'EtlSourceOutput':
                s3Location = inputArtifacts['location']['s3Location']
                zip_bytes = s3.get_object(Bucket=s3Location['bucketName'], Key=s3Location['objectKey'])['Body'].read()
                with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as z:
                    for file in z.infolist():
                        if file.filename == 'preprocess.py':
                            s3.put_object(Bucket=output_bucket, Key="{}/code/{}".format(executionId, file.filename), Body=z.read(file))
                        if file.filename == 'etljob.json':
                            etlJob = json.loads(z.read('etljob.json').decode('ascii'))
        etlJob['Name'] = job_name
        etlJob['Role'] = role
        etlJob['Command']['ScriptLocation'] = script_location
        glue_job_name = glue.create_job(**etlJob)['Name']
        logger.info(glue_job_name)
        job_run_id = glue.start_job_run(
            JobName=job_name,
            Arguments={
                '--S3_INPUT_BUCKET': data_bucket,
                '--S3_INPUT_KEY_PREFIX': 'input/raw',
                '--S3_OUTPUT_BUCKET': output_bucket,
                '--S3_OUTPUT_KEY_PREFIX': executionId+'/input'
            }
        )['JobRunId']
        logger.info(job_run_id)
        cw.enable_rule(Name="etl-job-monitor-{}".format(model_name))
        cp.put_job_success_result(jobId=jobId)
    except Exception as e:
        logger.error(e)
        resppnse = cp.put_job_failure_result(
            jobId=jobId,
            failureDetails={
                'type': 'ConfigurationError',
                'message': str(e),
                'externalExecutionId': context.aws_request_id
            }
        )
    
    return 'Done'