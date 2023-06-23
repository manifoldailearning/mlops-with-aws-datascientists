import json
import os
import logging
import boto3
from botocore.exceptions import ClientError


sm = boto3.client('sagemaker')
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    logger.debug("Boto3 Version: {}".format(boto3.__version__))
    logger.debug("## Environment Variables ##")
    logger.debug(os.environ)
    logger.debug("## Event ##")
    logger.debug(event)

    # Ensure variables passed from Model Evaluation Step
    if ("Model_Name" in event):
        model_name = event["Model_Name"]
    else:
        raise KeyError("'Model_Name' not found in Lambda event!")
    if ("Group_Name" in event):
        group_name = event['Group_Name']
    else:
        raise KeyError("'Group_Name' not found in Lambda event!")
    if ("Model_Uri" in event):
        model_uri = event['Model_Uri']
    else:
        raise KeyError("'Model_Uri' not found in Lambda event!")
    if ("Image_Uri" in event):
        image_uri = event['Image_Uri']
    else:
        raise KeyError("'Image_Uri' not found in Lambda event!")
    if ("Job_Id" in event):
        job_id = event['Job_Id']
    else:
        raise KeyError("'Job_Id' not found in Lambda event!")
    if ("Evaluation_Uri" in event):
        evaluation_uri = event['Evaluation_Uri']
    else:
        raise KeyError("'Evluation_Uri' not found in Lambda event!")
    
    # Create request payload
    request = {
        "InferenceSpecification": { 
            "Containers": [ 
                { 
                    "Image": image_uri,
                    "ModelDataUrl": model_uri
                }
            ],
            "SupportedContentTypes": [ 
                "text/csv" 
            ],
            "SupportedRealtimeInferenceInstanceTypes": [ 
                "ml.t2.large",
                "ml.c5.large",
                "ml.c5.xlarge"
            ],
            "SupportedResponseMIMETypes": [ 
                "text/csv" 
            ],
            "SupportedTransformInstanceTypes": [ 
                "ml.c5.xlarge"
            ]
        },
        "MetadataProperties": { 
            "ProjectId": str(job_id)
        },
        "ModelApprovalStatus": "Approved",
        "ModelMetrics": {
            "ModelQuality": { 
                "Statistics": { 
                    "ContentType": "application/json",
                    "S3Uri": evaluation_uri
                }
            }
        },
        "ModelPackageDescription": "Abalone Production Model",
        "ModelPackageGroupName": group_name
    }

    # Create the Model Package
    try:
        response = sm.create_model_package(**request)
    except ClientError as e:
        error_message = e.response["Error"]["Message"]
        logger.error(error_message)
        raise Exception(error_message)

    # Return results
    logger.info("Done!")
    return {
        "statusCode": 200,
        "PackageArn": response['ModelPackageArn']
    }
