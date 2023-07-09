import argparse
import json
import logging
import os
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)
cp = boto3.client('codepipeline')
sm = boto3.client('sagemaker')
deployment_stage = os.environ['STAGE']


def get_approved_package(package_group_name):
    """
    Description:
    -----------
    Gets the latest approved model package for a model package group.

    :package_group_name: The model package group name.

    :returns: The SageMaker Model Package ARN.
    """
    try:
        # Get the latest approved model package
        response = sm.list_model_packages(
            ModelPackageGroupName=package_group_name,
            ModelApprovalStatus="Approved",
            SortBy="CreationTime",
            MaxResults=100,
        )
        approved_packages = response["ModelPackageSummaryList"]

        # Fetch more packages if none returned with continuation token
        while len(approved_packages) == 0 and "NextToken" in response:
            logger.debug("Getting more packages for token: {}".format(response["NextToken"]))
            response = sm.list_model_packages(
                ModelPackageGroupName=package_group_name,
                ModelApprovalStatus="Approved",
                SortBy="CreationTime",
                MaxResults=100,
                NextToken=response["NextToken"],
            )
            approved_packages.extend(response["ModelPackageSummaryList"])

        # Return error if no packages found
        if len(approved_packages) == 0:
            error_message = (
                f"No approved ModelPackage found for ModelPackageGroup: {package_group_name}"
            )
            logger.error(error_message)
            raise Exception(error_message)

        # Return the pmodel package arn
        model_package_arn = approved_packages[0]["ModelPackageArn"]
        logger.info(f"Identified the latest approved model package: {model_package_arn}")
        return model_package_arn
    except ClientError as e:
        error_message = e.response["Error"]["Message"]
        logger.error(error_message)
        raise Exception(error_message)


def get_job_id(env, pipeline_name):
    """
    Description:
    -----------
    Gets the latest ExecutionID based on the Codepipeline Stage.

    :env: (str) The current Deployment Stage.
    :pipeline_name: (str) CodePipeline name.

    :return: CodePipeline Execition ID.
    """
    try:
        response = cp.get_pipeline_state(name=pipeline_name)
        for stageState in response['stageStates']:
            if stageState['stageName'] == "Deploy{}".format(env):
                for actionState in stageState['actionStates']:
                    if actionState['actionName'] == "Build{}Deployment".format(env):
                        return stageState['latestExecution']['pipelineExecutionId']
    except ClientError as e:
        error_message = e.response["Error"]["Message"]
        logger.error(error_message)
        raise Exception(error_message)


def extend_dev_params(args, stage_config):
    """
    Description:
    -----------
    Extend the stage configuration with additional parameters specifc to the pipeline execution.

    :args: (parser) Parsed known arguments.
    :stage_config: (dict) Current configuration for the stage.

    :return: (dict) Configured CloudFormation parmaters for the stage.
    """
    # Verify that config has parameters
    if not "Parameters" in stage_config:
        raise Exception("Configuration file must include Parameters")
    params = {
        "ImageRepoName": args.image_repo_name,
        "ImageTagName": args.image_tag,
        "ModelName": args.model_name,
        "TrainJobId": get_job_id(deployment_stage, args.pipeline_name)
    }
    return {
        "Parameters": {**stage_config["Parameters"], **params}
    }


def extend_prd_params(args, stage_config):
    """
    Description:
    -----------
    Extend the stage configuration with additional parameters specifc to the pipeline execution.

    :args: (parser) Parsed known arguments.
    :stage_config: (dict) Current configuration for the stage.

    :return: (dict) Configured CloudFormation parmaters for the stage.
    """
    # Verify that config has parameters
    if not "Parameters" in stage_config:
        raise Exception("Configuration file must include Parameters")
    params = {
        "ModelName": args.model_name,
        "TrainJobId": get_job_id(deployment_stage, args.pipeline_name),
        "ModelPackageName": get_approved_package(args.model_package_group_name)
    }
    return {
        "Parameters": {**stage_config["Parameters"], **params}
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pipeline-name", type=str, default=os.environ["PIPELINE_NAME"])
    parser.add_argument("--image-repo-name", type=str, default=os.environ["IMAGE_REPO_NAME"])
    parser.add_argument("--image-tag", type=str, default=os.environ["IMAGE_TAG"])
    parser.add_argument("--model-name", type=str, default=os.environ["MODEL_NAME"])
    parser.add_argument("--model-package-group-name", type=str, default=os.environ['MODEL_GROUP'])
    parser.add_argument("--import-config", type=str, default=os.environ["CODEBUILD_SRC_DIR"]+"/assets/{}/{}-config.json".format(deployment_stage, deployment_stage))
    parser.add_argument("--export-config", type=str, default=os.environ["CODEBUILD_SRC_DIR"]+"/assets/{}/{}-config-export.json".format(deployment_stage, deployment_stage))
    args, _ = parser.parse_known_args()

    # Configure logging to output the line number and message
    log_format = "%(levelname)s: [%(filename)s:%(lineno)s] %(message)s"
    logging.basicConfig(format=log_format, level=os.environ.get("LOGLEVEL", "INFO").upper())

    if deployment_stage == 'Dev':
        # Write the `Dev` stage config
        with open(args.import_config, "r") as f:
            config = extend_dev_params(args, json.load(f))
        logger.debug("Config: {}".format(json.dumps(config, indent=4)))
        with open(args.export_config, "w") as f:
            json.dump(config, f, indent=4)
    elif deployment_stage == 'Prd':
        # Write the `Prd` stage config
        with open(args.import_config, "r") as f:
            config = extend_prd_params(args, json.load(f))
        logger.debug("Config: {}".format(json.dumps(config, indent=4)))
        with open(args.export_config, "w") as f:
            json.dump(config, f, indent=4)
    else:
        error_message = "'STAGE' Environment Variable not configured."
        logger.error(error_message)
        raise Exception(error_message)