#!/usr/bin/env python3
# iac/app.py — repositorio: blick-api
import os

import aws_cdk as cdk

from iac_stack import BlickApiStack

app = cdk.App()

aws_region = os.environ.get("AWS_REGION", "us-east-1")
aws_account_id = os.environ["AWS_ACCOUNT_ID"]
model_data_url = os.environ["MODEL_DATA_URL"]
sagemaker_role_arn = os.environ["SAGEMAKER_ROLE_ARN"]
endpoint_name = os.environ.get("SAGEMAKER_ENDPOINT_NAME", "blick-classificador")

BlickApiStack(
    app, "BlickApiStack",
    model_data_url=model_data_url,
    sagemaker_role_arn=sagemaker_role_arn,
    endpoint_name=endpoint_name,
    env=cdk.Environment(account=aws_account_id, region=aws_region),
    synthesizer=cdk.CliCredentialsStackSynthesizer(),
)

app.synth()