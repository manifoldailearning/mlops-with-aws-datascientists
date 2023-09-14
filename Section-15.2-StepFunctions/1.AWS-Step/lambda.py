import json

def lambda_handler(event, context):

    # TODO implement

    return {

        'statusCode': 200,

        'body': json.dumps('AWS ML course, the lambda function has been invoked from Step Function.')

    }