#!/usr/bin/python
#
# Run this script from the directory its in
# This script requires following arguments
# --aws-profile (name of the profile to use for aws credentials)
# --api-gw (name of the api_gateway)
# --splunk-host (splunk host IP and port)
# --splunk-token (splunk access token)
# e.g.
# python monitor.py --aws-profile test --api-gw api --splunk-host 10.2.1.2:99 --splunk-token xxx
#

import logging
import os
import time
import argparse
from zipfile import ZipFile
import botocore.session
import botocore.exceptions


def create_api_alarm(cw_session, alarm_name, metric,
                     namespace, stat, comparison, description,
                     threshold, period, eval_period, dimensions, topic):
    """Create the alarm for appropriate metric in API Gateway"""
    response = cw_session.put_metric_alarm(
        AlarmName=alarm_name,
        AlarmDescription=description,
        ActionsEnabled=True,
        Namespace=namespace,
        Dimensions=dimensions,
        MetricName=metric,
        Statistic=stat,
        Period=period,
        EvaluationPeriods=eval_period,
        Threshold=threshold,
        ComparisonOperator=comparison,
        AlarmActions=[topic])

    logging.info('response for creating api alarm = "%s"',
                 response['ResponseMetadata'])


def create_firehose_stream(firehose, stream_name, arn, bucket_arn):
    """Setup a stream(if required) to export cloudwatch logs to s3"""
    response = firehose.create_delivery_stream(
        DeliveryStreamName=stream_name,
        S3DestinationConfiguration={
            'RoleARN': arn,
            'BucketARN': bucket_arn,
            'Prefix': '',
            'BufferingHints': {
                'SizeInMBs': 5,
                'IntervalInSeconds': 300
            },
            'CompressionFormat': 'UNCOMPRESSED',
            'EncryptionConfiguration': {
                'NoEncryptionConfig': 'NoEncryption',
            },
            'CloudWatchLoggingOptions': {
                'Enabled': False,
            }
        })

    logging.info('response for creating firehose stream = "%s"',
                 response)


def create_lambda_function_zip(splunk_host, splunk_token):
    """Updates and Zips the lambda function file"""

    with open('index.js', "wt") as lambda_function_file:
        with open('index.js.template', 'rt') as lambda_function_template:
            for line in lambda_function_template:
                lambda_function_file.write(line.replace('<splunk host:port>',
                                                        splunk_host).replace('<token>',
                                                                             splunk_token))
    zip_file = 'lambda.zip'

    with ZipFile(zip_file, 'w') as lambda_zip:
        lambda_zip.write('index.js')

    return zip_file


def role_exists(iam, role_name):
    """Checks if the role exists already"""
    try:
        iam.get_role(RoleName=role_name)
    except botocore.exceptions.ClientError:
        return False
    return True


def get_role_arn(iam, role_name):
    """Gets the ARN of role"""
    response = iam.get_role(RoleName=role_name)
    return response['Role']['Arn']


def create_role(iam, policy_name, assume_role_policy_document, policy_str):
    """Creates a new role if there is not already a role by that name"""
    if role_exists(iam, policy_name):
        logging.info('Role "%s" already exists. Assuming correct values.', policy_name)
        return get_role_arn(iam, policy_name)
    else:
        response = iam.create_role(RoleName=policy_name,
                                   AssumeRolePolicyDocument=assume_role_policy_document)
        iam.put_role_policy(RoleName=policy_name,
                            PolicyName='inlinepolicy', PolicyDocument=policy_str)
        logging.info('response for creating role = "%s"', response)
        return response['Role']['Arn']


def create_lambda_function(client, function_name, runtime, role,
                           handler, zip_file, description, timeout, mem_size):
    """Create a lambda function to pull data from cloudwatch event"""
    response = client.create_function(
        FunctionName=function_name,
        Runtime=runtime,
        Role=role,
        Handler=handler,
        Code={
            'ZipFile': open(zip_file, 'rb').read(),
        },
        Description=description,
        Timeout=timeout,
        MemorySize=mem_size,
        Publish=True)

    logging.info('response for creating lambda function = "%s"',
                 response)


def get_topic_arn(client, topic_name):
    """Gets the Arn of an SNS topic"""
    response = client.list_topics()
    for value in response['Topics']:
        sns_arn = value['TopicArn']
        if topic_name in str(sns_arn):
            return str(sns_arn)
        else:
            return None


def cleanup():
    """Cleans the extra files generated"""
    logging.info('The lambda function is created, now in order to provide'
                 ' event source to it, go to aws console, select the cloudwatch '
                 'log group and select the action Start streaming to lambda')
    os.system("rm -rf lambda.zip index.js")


if __name__ == '__main__':

    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s %(message)s')

    parser = argparse.ArgumentParser()
    parser.add_argument("--aws-profile", required=True)
    parser.add_argument("--aws-region", default="us-east-1")
    parser.add_argument("--api-gw", required=True)
    parser.add_argument("--splunk-host", required=True)
    parser.add_argument("--splunk-token", required=True)

    args = parser.parse_args()
    session = botocore.session.Session(profile=args.aws_profile)

    sns_client = session.create_client('sns', args.aws_region)
    cw = session.create_client('cloudwatch', args.aws_region)

    create_api_alarm(cw, 'api_count', 'Count', 'ApiGateway',
                     'Average', 'GreaterThanOrEqualToThreshold',
                     'Average API count for a period of 5 min', 50, 300, 1,
                     [{'Name': 'ApiName', 'Value': args.api_gw}, {'Name': 'Label', 'Value': args.api_gw}],
                     get_topic_arn(sns_client, 'aws-non-critical-alert'))

    create_api_alarm(cw, 'api_latency', 'Latency', 'ApiGateway', 'Average',
                     'GreaterThanOrEqualToThreshold', 'Average API Latency for a period of 5 min',
                     3, 300, 1, [{'Name': 'ApiName', 'Value': args.api_gw}, {'Name': 'Label', 'Value': args.api_gw}],
                     get_topic_arn(sns_client, 'aws-non-critical-alert'))

    create_api_alarm(cw, 'api_errors_4xx', '4XXError', 'ApiGateway', 'Average',
                     'GreaterThanOrEqualToThreshold', 'Average 4XX errors for a period of 5 min',
                     4, 300, 1, [{'Name': 'ApiName', 'Value': args.api_gw}, {'Name': 'Label', 'Value': args.api_gw}],
                     get_topic_arn(sns_client, 'aws-non-critical-alert'))

    create_api_alarm(cw, 'api_errors_5xx', '5XXError', 'ApiGateway', 'Average',
                     'GreaterThanOrEqualToThreshold', 'Average 5XX errors for a period of 5 min',
                     4, 300, 1, [{'Name': 'ApiName', 'Value': args.api_gw}, {'Name': 'Label', 'Value': args.api_gw}],
                     get_topic_arn(sns_client, 'aws-non-critical-alert'))

    iam_client = session.create_client('iam', args.aws_region)
    role_arn = create_role(iam_client, 'lambda_basic_execution_monitor',
                           '{"Version": "2012-10-17","Statement": [{"Effect": "Allow","Principal": '
                           '{"Service": "lambda.amazonaws.com"},"Action": "sts:AssumeRole"}]}',
                           open(os.path.join(os.path.dirname(__file__), 'lambda_exec_policy.json')).read())

    time.sleep(10)
    lambda_client = session.create_client('lambda', args.aws_region)
    zip_file_name = create_lambda_function_zip(args.splunk_host, args.splunk_token)
    create_lambda_function(lambda_client, 'cloudwatch-logs-splunk', 'nodejs4.3', role_arn,
                           'index.handler', zip_file_name,
                           'Demonstrates logging events to Splunk HTTP Event '
                           'Collector.', 10, 512)
    time.sleep(2)
    cleanup()
