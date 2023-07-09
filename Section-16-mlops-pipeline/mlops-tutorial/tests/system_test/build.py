import logging
import os
import random
import boto3
import argparse
import json
import time
from botocore.exceptions import ClientError

# Step Functions Libraries
import stepfunctions
from stepfunctions import steps
from stepfunctions.inputs import ExecutionInput
from stepfunctions.steps import (
    Chain,
    ChoiceRule,
    ProcessingStep,
    TrainingStep,
    Task,
    LambdaStep
)
from stepfunctions.template import TrainingPipeline
from stepfunctions.workflow import Workflow

# SageMaker Libraries
import sagemaker
from sagemaker.processing import ProcessingInput, ProcessingOutput, Processor
from sagemaker.s3 import S3Uploader

# Client Session
logger = logging.getLogger(__name__)
sagemaker_session = sagemaker.Session()
region = sagemaker_session.boto_region_name
account_id = boto3.client('sts').get_caller_identity()["Account"]
role = sagemaker.session.get_execution_role()
sfn = boto3.client('stepfunctions')
cp = boto3.client('codepipeline')
ssm = boto3.client('ssm')

# Helper Functions
def get_job_id(pipeline_name):
    """
    Description:
    -----------
    Gets the current executionId based on the CodePipeline Stage.

    :pipeline_name: CodePipeline Name.

    :return: CodePipeline Execution ID for this state.
    """
    try:
        response = cp.get_pipeline_state(name=pipeline_name)
        for stageState in response['stageStates']:
            if stageState['stageName'] == 'SystemTest':
                for actionState in stageState['actionStates']:
                    if actionState['actionName'] == 'BuildTestingWorkflow':
                        return stageState['latestExecution']['pipelineExecutionId']
    except ClientError as e:
        error_message = e.response["Error"]["Message"]
        logger.error(error_message)
        raise Exception(error_message)

def get_workflow_role():
    """
    Description:
    -----------
    Retrieves the Workflow Arn from Parameter Store.

    :return: Workflow Execution Role ARN from parameters store.
    """
    try:
        response = ssm.get_parameter(
            Name='WorkflowExecRole',
        )
        return response['Parameter']['Value']
    except ClientError as e:
        error_message = e.response["Error"]["Message"]
        logger.error(error_message)
        raise Exception(error_message)


def get_lambda_arn(name):
    """
    Description:
    -----------
    Retrieves the Lambda Function Arn from the Parameter Store.

    :name: (str) Name of the Lambda Function to return the ARN for.

    :return: Evaluation Lambda ARN from paramater store.
    """
    try:
        response = ssm.get_parameter(
            Name=name
        )
        return response['Parameter']['Value']
    except ClientError as e:
        error_message = e.response["Error"]["Message"]
        logger.error(error_message)
        raise Exception(error_message)


def get_baseline_uri(region):
    """
    Description:
    -----------
    Compiles the container uri for the Baseline Processing Container based ont he region.

    :region: (str) Current AWS Region
    
    :return: Baseline Container URI.
    """
    container_uri_format = (
        "{0}.dkr.ecr.{1}.amazonaws.com/sagemaker-model-monitor-analyzer"
    )
    regions_to_accounts = {
        "eu-north-1": "895015795356",
        "me-south-1": "607024016150",
        "ap-south-1": "126357580389",
        "eu-west-3": "680080141114",
        "us-east-2": "777275614652",
        "eu-west-1": "468650794304",
        "eu-central-1": "048819808253",
        "sa-east-1": "539772159869",
        "ap-east-1": "001633400207",
        "us-east-1": "156813124566",
        "ap-northeast-2": "709848358524",
        "eu-west-2": "749857270468",
        "ap-northeast-1": "574779866223",
        "us-west-2": "159807026194",
        "us-west-1": "890145073186",
        "ap-southeast-1": "245545462676",
        "ap-southeast-2": "563025443158",
        "ca-central-1": "536280801234"
    }
    container_uri = container_uri_format.format(regions_to_accounts[region], region)
    
    return container_uri

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pipeline-name", type=str, default=os.environ["PIPELINE_NAME"])
    parser.add_argument("--image-repo-name", type=str, default=os.environ["IMAGE_REPO_NAME"])
    parser.add_argument("--image-tag", type=str, default=os.environ["IMAGE_TAG"])
    parser.add_argument("--model-name", type=str, default=os.environ["MODEL_NAME"])
    parser.add_argument("--model-package-group-name", type=str, default=os.environ["MODEL_GROUP"])
    parser.add_argument("--test-endpoint", type=str, default="{}-dev-endpoint".format(os.environ["MODEL_NAME"]))
    parser.add_argument("--pipeline-bucket", type=str, default=os.environ["PIPELINE_BUCKET"])
    args, _ = parser.parse_known_args()

    # Configure logging to output the line number and message
    log_format = "%(levelname)s: [%(filename)s:%(lineno)s] %(message)s"
    logging.basicConfig(format=log_format, level=os.environ.get("LOGLEVEL", "INFO").upper())

    # Configure workflow variables for current execution
    job_id = get_job_id(args.pipeline_name)
    baseline_job_name = "{}-baseline-{}".format(args.model_name, job_id)
    image_uri = "{}.dkr.ecr.{}.amazonaws.com/{}:{}".format(account_id, region, args.image_repo_name, args.image_tag)

    """
    SageMaker expects unique names for each job, model and endpoint.

    NOTE: If these names are not unique the execution will fail.
          Pass these dynamically for each execution using placeholders.
    """
    execution_input = ExecutionInput(
        schema={
            "ModelName": str,
            "ModelGroup": str,
            "EndpointName": str,
            "BaselineProcessingJobName": str
        }
    )

    # S3 Locations of processing baseline and testing data.
    s3_bucket_base_uri = "s3://{}".format(args.pipeline_bucket)
    input_data_prefix = os.path.join(s3_bucket_base_uri, job_id, 'input')
    output_data_prefix = os.path.join(s3_bucket_base_uri, job_id)
    preprocessed_baseline_data = "{}/{}".format(input_data_prefix, 'baseline')
    output_baseline_report_s3_uri = "{}/{}".format(output_data_prefix,"baseline_report")
    output_model_evaluation_s3_uri = "{}/{}".format(output_data_prefix,"evaluation")
    model_s3_uri = "{}/{}/mlops-{}-{}/{}".format(s3_bucket_base_uri, job_id, args.model_name, job_id, "output/model.tar.gz")

    # Create the Lambda Function `configure_output` Step 
    evaluate_endpoint_step = LambdaStep(
        "Evaluate SageMaker Hosted Model",
        parameters={
            "FunctionName": get_lambda_arn('EvaluateEndpoint'),
            "Payload": {
                "Endpoint_Name": execution_input['EndpointName'],
                "Bucket": args.pipeline_bucket,
                "Key": "{}/input/testing/test.csv".format(job_id),
                "Output_Key": "{}/evaluation".format(job_id)
            }
        }
    )

    # Create the Lambda Function `registerModel` Step
    register_model_step = LambdaStep(
        "Register Production Model",
        parameters={
            "FunctionName": get_lambda_arn('RegisterModel'),
            "Payload": {
                "Model_Name": execution_input['ModelName'],
                "Group_Name": execution_input['ModelGroup'],
                "Model_Uri": model_s3_uri,
                "Image_Uri": image_uri,
                "Job_Id": job_id,
                "Evaluation_Uri": os.path.join(output_model_evaluation_s3_uri, "evaluation.json")
            }
        }

    )

    # Create Baseline suggestion step
    baseline_step = ProcessingStep(
        "Suggest Baseline",
        processor=Processor(
            image_uri=get_baseline_uri(region),
            instance_count=1,
            instance_type="ml.m5.xlarge",
            volume_size_in_gb=30,
            role=role,
            max_runtime_in_seconds=1800,
            env={
                "dataset_format": "{\"csv\": {\"header\": true, \"output_columns_position\": \"START\"}}",
                "dataset_source": "/opt/ml/processing/input/baseline_dataset_input",
                "output_path": "/opt/ml/processing/output",
                "publish_cloudwatch_metrics": "Disabled"
                }
        ),
        job_name=execution_input["BaselineProcessingJobName"],
        inputs=[
            ProcessingInput(
                source="{}/{}".format(preprocessed_baseline_data, "baseline.csv"),
                destination="/opt/ml/processing/input/baseline_dataset_input",
                input_name="baseline_dataset_input"
            )
        ],
        outputs=[
            ProcessingOutput(
                source="/opt/ml/processing/output",
                destination=output_baseline_report_s3_uri,
                output_name="monitoring_output"
            )
        ]
    )

    # Create a `Parallel` Step to simultaneously run the `baseline` and `register_model` steps
    parallel_step = stepfunctions.steps.states.Parallel(
        "Finalize Production Model",
    )
    parallel_step.add_branch(baseline_step)
    parallel_step.add_branch(register_model_step)

    # Create `Fail` states to mark the workflow failed in case any of the steps fail
    workflow_failed_state = stepfunctions.steps.states.Fail(
        "Workflow Failed", cause="WorkflowFailed"
    )

    # Create `Fail` state if Model evaluation is below the evaluation threshold
    threshold_fail_state = stepfunctions.steps.states.Fail(
        "Model Above Quality Threshold"
    )

    # Creates `Pass` state for successfull evaluation
    threshold_pass_state = stepfunctions.steps.states.Pass(
        "Model Below Quality Threshold"
    )

    # Add the baseline step after the `Pass` state
    threshold_pass_state.next(parallel_step)

    # Create Threshold PASS | Fail Branch Step
    check_threshold_step = steps.states.Choice(
        "Evaluate Model Quality Threshold"
    )

    # Set rule to evaluate the results of the Analysis Step with the Threshold value
    threshold_rule = steps.choice_rule.ChoiceRule.NumericLessThan(
        variable=evaluate_endpoint_step.output()['Payload']['Result'],
        value=float(os.environ["THRESHOLD"])
    )

    # If results less than threshold, workflow is successful
    check_threshold_step.add_choice(rule=threshold_rule, next_step=threshold_pass_state)

    # If results above threshold, workflow failed
    check_threshold_step.default_choice(next_step=threshold_fail_state)

    # Define `catch` Step to catch any step failures
    catch_state = stepfunctions.steps.states.Catch(
        error_equals=["States.TaskFailed"],
        next_step=workflow_failed_state,
    )

    # Add catch block to workflow steps
    evaluate_endpoint_step.add_catch(catch_state)
    parallel_step.add_catch(catch_state)

    # Define the workflow graph
    workflow_graph = Chain(
        [
            evaluate_endpoint_step,
            check_threshold_step
        ]
    )

    # Define the workflow
    workflow = Workflow(
        name=os.environ['WORKFLOW_NAME'],
        definition=workflow_graph,
        role=get_workflow_role()
    )

    # Create State Machine
    try:
        logger.info("Creating workflow ...")
        workflow.create()
    except sfn.exceptions.StateMachineAlreadyExists:
        logger.info("Found existing workflow, updating the State Machine definition ...")
    else:
        # Update workflow
        workflow.update(workflow_graph)
        # Wait 60 seconds to ensure that definition has been updated before execution
        time.sleep(60)

    # Create JSON file of the current execution variables
    with open("input.json", "w") as json_file:
        json.dump(
            {
                "ModelName": args.model_name,
                "ModelGroup": args.model_package_group_name,
                "EndpointName": args.test_endpoint,
                "BaselineProcessingJobName": baseline_job_name
            },
            json_file
        )
