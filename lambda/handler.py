import json
import os
import boto3

secrets_client = boto3.client("secretsmanager")
SECRET_NAME = os.environ["SECRET_NAME"]


def handler(event, context):
    response = secrets_client.get_secret_value(SecretId=SECRET_NAME)
    secret_value = response["SecretString"]

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({
            "message": "Successfully retrieved a secret from AWS Secrets Manager",
            "secret_length": len(secret_value)
        })
    }
