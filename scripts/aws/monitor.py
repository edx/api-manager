#!/usr/bin/python
#
# Pre-reqs:
# Run this script from the directory its in
#
# Arguments:
# This script requires following arguments
# --api-base-domain (name of the API Gateway domain)
# --splunk-host (splunk host IP and port)
# --splunk-token (base-64 encoded splunk access token)
# --acct-id (aws account id)
# --lambda-timeout (The function execution time)
# --lambda-memory (The amount of memory, in MB, your Lambda function is given)
# --kms-key (The KMS key)
# --subnet-list (space seperated list of subnet IDs for VPC config)
# --sg-list (space seperated list of security group IDs for VPC config)
# --environment (the environment where lambda function is to be created)
# --deployment (the deployment for which lambda function is created)
# e.g.
# python monitor.py --api-base-domain test.edx.org --splunk-host 10.2.1.2:99 --splunk-token xxx \
# --acct-id 000 --lambda-timeout 10 --lambda-memory 512 --kms-key xxxx-xx-xx-xxx
# --subnet-list subnet-112 subnet-113 --sg-list sg-899 sg-901 --environment stage --deployment edx
#
"""
Api Gateway monitoring scripts
"""
import logging
import time
import argparse
import tempfile
import shutil
from zipfile import ZipFile
from os.path import os, basename
import botocore.session
import botocore.exceptions
from jinja2 import Environment, FileSystemLoader


def get_api_id(client, api_base_domain):
    """Get the current live API ID and stage tied to this base path."""
    try:
        response = client.get_base_path_mapping(
            domainName=api_base_domain,
            basePath='(none)')
    except botocore.exceptions.ClientError as exception:
        raise ValueError('No mapping found for "%s"' % api_base_domain) from exception  # pylint: disable=consider-using-f-string

    logging.info('Found existing base path mapping for API ID "%s", stage "%s"',
                 response['restApiId'], response['stage'])

    return (response['restApiId'], response['stage'])


def create_api_alarm(*, cw_session, alarm_name, metric,
                     namespace, stat, comparison, description,
                     threshold, period, eval_period, dimensions, topic):
    """Puts data to the metric, then creates the alarm for appropriate metric in API Gateway"""
    cw_session.put_metric_data(
        Namespace=namespace,
        MetricData=[{'MetricName': metric, 'Dimensions': dimensions, 'Value': 0}, ])
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


def create_lambda_function_zip(jinja_env, temp_dir, splunk_host, splunk_token, lf_name):
    """Updates and Zips the lambda function file"""
    splunk_values = {
        'splunk_ip': splunk_host,
        'token': splunk_token,
        'lambda_function_name': lf_name,
    }
    js_file = temp_dir + '/index.js'
    with open(js_file, 'w', encoding='utf-8') as lambda_function_file:
        lf_data = jinja_env.get_template('index.js.j2').render(splunk_values)
        lambda_function_file.write(lf_data)

    zip_file = temp_dir + '/lambda.zip'
    with ZipFile(zip_file, 'w') as lambda_zip:
        lambda_zip.write(js_file, basename(js_file))
    return zip_file


def get_lambda_exec_policy(*, jinja_env, temp_dir, region, acct_id, func_name, kms_key):
    """updates the policy json and returns it"""
    resource_values = {
        'region': region,
        'acct_id': acct_id,
        'func_name': func_name,
        'kms_key': kms_key,
    }
    json_file = temp_dir + '/lambda_exec_policy.json'
    with open(json_file, 'w', encoding='utf-8') as json_policy_file:
        json_data = jinja_env.get_template('lambda_exec_policy.json.j2').render(resource_values)
        json_policy_file.write(json_data)
    return json_file


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


def lambda_exists(client, function_name):
    """Checks if the function exists already"""
    try:
        client.get_function(FunctionName=function_name)
    except botocore.exceptions.ClientError:
        return False
    return True


def attach_managed_policy(iam, role_name, policy_arn):
    """Attaches a managed policy to an existing role"""
    response = iam.attach_role_policy(RoleName=role_name,
                                      PolicyArn=policy_arn)
    logging.info('response for attaching managed policy to role = "%s"', response)


def create_role_with_inline_policy(iam, policy_name, assume_role_policy_document, policy_str):
    """Creates a new role with inline policy if there is not already a role by that name"""
    if role_exists(iam, policy_name):
        logging.info('Role "%s" already exists. Assuming correct values.', policy_name)
        return get_role_arn(iam, policy_name)

    response = iam.create_role(RoleName=policy_name,
                               AssumeRolePolicyDocument=assume_role_policy_document)
    iam.put_role_policy(RoleName=policy_name,
                        PolicyName='inlinepolicy', PolicyDocument=policy_str)
    logging.info('response for creating role = "%s"', response)
    return response['Role']['Arn']


def create_role_with_managed_policy(iam, role_name, assume_role_policy_document, policy_arn):
    """Creates a new role with managed policy if there is not already a role by that name"""
    if role_exists(iam, role_name):
        logging.info('Role "%s" already exists. Assuming correct values.', role_name)
        return get_role_arn(iam, role_name)

    response = iam.create_role(RoleName=role_name,
                               AssumeRolePolicyDocument=assume_role_policy_document)
    attach_managed_policy(iam, role_name, policy_arn)
    logging.info('response for creating role = "%s"', response)
    return response['Role']['Arn']


def create_lambda_function(*, client, function_name, runtime, role,
                           handler, zip_file, description, timeout, mem_size, vpc):
    """Creates a lambda function to pull data from cloudwatch event.
    It only works works in VPC"""
    try:
        code_file = open(zip_file, 'rb')  # pylint: disable=consider-using-with
        if lambda_exists(client, function_name):
            logging.info('"%s" function already exists. Updating its code', function_name)
            response = client.update_function_code(
                FunctionName=function_name,
                ZipFile=code_file.read(),
                Publish=True)

        else:
            response = client.create_function(
                FunctionName=function_name,
                Runtime=runtime,
                Role=role,
                Handler=handler,
                Code={
                    'ZipFile': code_file.read(),
                },
                Description=description,
                Timeout=timeout,
                MemorySize=mem_size,
                Publish=True,
                VpcConfig=vpc)

        logging.info('response for lambda function = "%s"',
                     response)
    except IOError:
        logging.error('Unable to open the zip file')
    finally:
        code_file.close()


def get_topic_arn(client, topic_name):
    """Gets the Arn of an SNS topic"""
    response = client.list_topics()
    for value in response['Topics']:
        sns_arn = value['TopicArn']
        if topic_name in str(sns_arn):
            return str(sns_arn)
    return None


def get_api_gateway_name(client, gw_id):
    """gets the name of the API Gateway"""
    gw_res = client.get_rest_apis()
    for value in gw_res['items']:
        if value['id'] == gw_id:
            gw_name = value['name']
            return str(gw_name)
    return None


def add_cloudwatchlog_role_to_apigateway(client, role_arn):
    """updates the role ARN to allow api gateway to push logs to cloudwatch"""
    response = client.update_account(
        patchOperations=[{'op': 'replace', 'path': '/cloudwatchRoleArn', 'value': role_arn}, ])
    logging.info('response for updating role = "%s"', response)


if __name__ == '__main__':

    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s %(message)s')

    parser = argparse.ArgumentParser()
    parser.add_argument("--aws-region", default="us-east-1")
    parser.add_argument("--api-base-domain", required=True)
    parser.add_argument("--splunk-host", required=True)
    parser.add_argument("--splunk-token", required=True)
    parser.add_argument("--acct-id", required=True)
    parser.add_argument("--lambda-timeout", type=int, default=10)
    parser.add_argument("--lambda-memory", type=int, default=512)
    parser.add_argument("--kms-key", required=True)
    parser.add_argument("--subnet-list", nargs='+', required=True)
    parser.add_argument("--sg-list", nargs='+', required=True)
    parser.add_argument("--environment", required=True)
    parser.add_argument("--deployment", required=True)

    args = parser.parse_args()
    session = botocore.session.get_session()
    j2_env = Environment(
        loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates')),
        trim_blocks=False
    )
    tmpdirname = tempfile.mkdtemp()
    lambda_role_name = (
        args.environment + '-' + args.deployment + '-' +
        'lambda-basic-execution-monitor-cloudwatch-logs'
    )
    lambda_function_name = args.environment + '-' + args.deployment + '-' + 'cloudwatch-logs-splunk'

    iam_client = session.create_client('iam', args.aws_region)
    cloudwatch_log_role_arn = \
        create_role_with_managed_policy(iam_client,
                                        'apigateway-to-cloudwatch-logs',
                                        '{"Version": "2012-10-17","Statement": '
                                        '[{"Sid": "","Effect": "Allow","Principal": '
                                        '{"Service": "apigateway.amazonaws.com"},'
                                        '"Action": "sts:AssumeRole"}]}',
                                        'arn:aws:iam::aws:policy/service-role/'
                                        'AmazonAPIGatewayPushToCloudWatchLogs')

    logging.info('Waiting for the newly created role to be available')
    # Sleep for 10 seconds to allow the role created above to be avialable
    time.sleep(10)
    api_client = session.create_client('apigateway', args.aws_region)
    (api_id, api_stage) = get_api_id(api_client, args.api_base_domain)
    add_cloudwatchlog_role_to_apigateway(api_client, cloudwatch_log_role_arn)

    api_gateway_name = get_api_gateway_name(api_client, api_id)
    sns_client = session.create_client('sns', args.aws_region)
    cw = session.create_client('cloudwatch', args.aws_region)

    create_api_alarm(
        cw_session=cw, alarm_name='api-gateway-count', metric='Count', namespace='ApiGateway',
        stat='Average', comparison='GreaterThanOrEqualToThreshold',
        description='Average API count for a period of 5 min',
        threshold=50, period=300, eval_period=1,
        dimensions=[
            {'Name': 'ApiName', 'Value': api_gateway_name},
            {'Name': 'Stage', 'Value': api_stage},
            {'Name': 'ApiId', 'Value': api_id}
        ],
        topic=get_topic_arn(sns_client, 'aws-non-critical-alert')
    )

    create_api_alarm(
        cw_session=cw, alarm_name='api-gateway-latency', metric='Latency', namespace='ApiGateway',
        stat='Average', comparison='GreaterThanOrEqualToThreshold',
        description='Average API Latency for a period of 5 min',
        threshold=3, period=300, eval_period=1,
        dimensions=[
            {'Name': 'ApiName', 'Value': api_gateway_name},
            {'Name': 'Stage', 'Value': api_stage},
            {'Name': 'ApiId', 'Value': api_id}
        ],
        topic=get_topic_arn(sns_client, 'aws-non-critical-alert')
    )

    create_api_alarm(
        cw_session=cw, alarm_name='api-gateway-errors-4xx', metric='4XXError',
        namespace='ApiGateway', stat='Average', comparison='GreaterThanOrEqualToThreshold',
        description='Average 4XX errors for a period of 5 min',
        threshold=4, period=300, eval_period=1,
        dimensions=[
            {'Name': 'ApiName', 'Value': api_gateway_name},
            {'Name': 'Stage', 'Value': api_stage},
            {'Name': 'ApiId', 'Value': api_id}
        ],
        topic=get_topic_arn(sns_client, 'aws-non-critical-alert')
    )

    create_api_alarm(
        cw_session=cw, alarm_name='api-gateway-errors-5xx', metric='5XXError',
        namespace='ApiGateway', stat='Average', comparison='GreaterThanOrEqualToThreshold',
        description='Average 5XX errors for a period of 5 min',
        threshold=4, period=300, eval_period=1,
        dimensions=[
            {'Name': 'ApiName', 'Value': api_gateway_name},
            {'Name': 'Stage', 'Value': api_stage},
            {'Name': 'ApiId', 'Value': api_id}
        ],
        topic=get_topic_arn(sns_client, 'aws-non-critical-alert')
    )

    with open(
        get_lambda_exec_policy(
            jinja_env=j2_env,
            temp_dir=tmpdirname,
            region=args.aws_region,
            acct_id=args.acct_id,
            func_name=lambda_function_name,
            kms_key=args.kms_key
        ),
        encoding='utf-8'
    ) as f:
        lambda_exec_role_arn = create_role_with_inline_policy(
            iam_client,
            lambda_role_name,
            '{"Version": "2012-10-17",'
            '"Statement": [{"Effect": "Allow","Principal": {"Service": "lambda.amazonaws.com"},'
            '"Action": "sts:AssumeRole"}]}',
            f.read()
        )

    logging.info('Waiting for the newly created role to be available')
    # Sleep for 10 seconds to allow the role created above
    # to be available for lambda function creation
    time.sleep(10)
    attach_managed_policy(iam_client, lambda_role_name,
                          'arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole')
    lambda_client = session.create_client('lambda', args.aws_region)
    zip_file_name = create_lambda_function_zip(j2_env, tmpdirname, args.splunk_host,
                                               args.splunk_token, lambda_function_name)
    vpc_config = {'SubnetIds': args.subnet_list, 'SecurityGroupIds': args.sg_list}
    create_lambda_function(
        client=lambda_client,
        function_name=lambda_function_name,
        runtime='nodejs18.x',
        role=lambda_exec_role_arn,
        handler='index.handler',
        zip_file=zip_file_name,
        description=(
            'Demonstrates logging events to Splunk HTTP Event Collector,'
            ' accessing resources in a VPC'
        ),
        timeout=args.lambda_timeout,
        mem_size=args.lambda_memory,
        vpc=vpc_config
    )
    try:
        shutil.rmtree(tmpdirname)
    except OSError as exc:
        logging.error(exc)
    logging.info('The lambda function is created, now in order to provide'
                 ' event source to it, go to aws console, select the cloudwatch '
                 'log group and select the action Start streaming to lambda')
