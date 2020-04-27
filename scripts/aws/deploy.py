#!/usr/bin/python

"""Various functions for day-to-day management of AWS API Gateway instances."""

import argparse
import logging
import botocore.session
import botocore.exceptions


def get_api_id(client, api_base_domain):
    """Get the current live API ID and stage tied to this base path."""
    try:
        response = client.get_base_path_mapping(
            domainName=api_base_domain,
            basePath='(none)')
    except botocore.exceptions.ClientError:
        raise ValueError('No mapping found for "%s"' % api_base_domain)

    logging.info('Found existing base path mapping for API ID "%s", stage "%s"',
                 response['restApiId'], response['stage'])

    return (response['restApiId'], response['stage'])


def get_next_stage(rotation, cur_stage):
    """
    Based on a pre-set stage rotation order, and a pointer to the current location in the order,
    determine the next stage based on a simple circular iteration. If the pointer is invalid,
    start at the first stage.
    """

    next_index = 0

    num_rotations = len(rotation)

    if num_rotations == 0:
        raise ValueError("No rotation order provided, cannot return next stage.")

    try:
        cur_index = rotation.index(cur_stage)

        # Circular iteration. If we're at the end, go back to the beginning!
        if cur_index < num_rotations - 1:
            next_index = cur_index + 1

    except ValueError:
        logging.info('Stage "%s" is not in the rotation, starting from the top.', cur_stage)

    next_stage = rotation[next_index]

    logging.info('Rotating from stage "%s" to "%s".', cur_stage, next_stage)
    return next_stage


def deploy_api(client, rest_api_id, swagger_filename, stage_name, stage_variables):
    """
    Upload the Swagger document to an existing API Gateway object and set it live
    with environment-specific variables.
    """

    swagger = open(swagger_filename, 'r')

    api_response = client.put_rest_api(restApiId=rest_api_id, mode='overwrite', body=swagger.read())
    logging.info('Existing API ID "%s" updated (name "%s")', api_response['id'], api_response['name'])

    deployment_response = client.create_deployment(
        restApiId=rest_api_id,
        stageName=stage_name,
        variables=stage_variables)

    logging.info('API ID "%s" deployed (deployment ID %s)', rest_api_id, deployment_response['id'])

    return deployment_response['id']


def update_stage(client, rest_api_id, stage_name, stage_settings):
    """
    Modify deployed stage with throttling, logging and caching settings.
    Note that you can define path-level overrides if you want; we're not
    tackling that at this time but it's theoretically possible.
    """

    response = client.update_stage(
        restApiId=rest_api_id,
        stageName=stage_name,
        patchOperations=[
            {'op': 'replace', 'path': '/*/*/logging/loglevel', 'value': stage_settings['log_level']},
            {'op': 'replace', 'path': '/*/*/metrics/enabled', 'value': stage_settings['metrics']},
            {'op': 'replace', 'path': '/*/*/caching/enabled', 'value': stage_settings['caching']},
            {'op': 'replace', 'path': '/*/*/throttling/rateLimit', 'value': stage_settings['rate_limit']},
            {'op': 'replace', 'path': '/*/*/throttling/burstLimit', 'value': stage_settings['burst_limit']}
        ])

    logging.info('API ID "%s", stage "%s" updated with settings: %s',
                 rest_api_id, stage_name, response['methodSettings'])

    return response

if __name__ == '__main__':

    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s %(message)s')

    parser = argparse.ArgumentParser()

    parser.add_argument("--aws-region", required=False, default="us-east-1")
    parser.add_argument("--api-base-domain", required=True,
                        help="The name of the API Gateway domain to be created.")
    parser.add_argument("--swagger-filename", required=True,
                        help="The name of a complete Swagger 2.0 specification file with AWS vendor hooks.")
    parser.add_argument("--tag", required=True,
                        help="Unique identifier for this deployment (such as a git hash)")
    parser.add_argument("--rotation-order", required=True, nargs='+',
                        help="Ordered list of stages in the deployment ring (ex: 'red black')")
    parser.add_argument("--log-level", required=False, default="OFF", choices=['OFF', 'ERROR', 'INFO'],
                        help="Verbosity of messages sent to CloudWatch Logs")
    parser.add_argument("--metrics", required=False, default="false", choices=['false', 'true'],
                        help="Enable CloudWatch metrics")
    parser.add_argument("--caching", required=False, default="false", choices=['false', 'true'],
                        help="Enable API Gateway caching feature")
    parser.add_argument("--rate-limit", required=False, default="500", type=str,
                        help="Default per-resource average rate limit")
    parser.add_argument("--burst-limit", required=False, default="1000", type=str,
                        help="Default per-resource maximum rate limit")
    parser.add_argument("--landing-page", required=True,
                        help="Location of landing page for 'root' level requests")
    parser.add_argument("--edxapp-host", required=True,
                        help="Location of edxapp for request routing")
    parser.add_argument("--catalog-host", required=True,
                        help="Location of catalog IDA for request routing")
    parser.add_argument("--enterprise-host", required=False, default='',
                        help="Location of enterprise IDA for request routing")
    parser.add_argument('--analytics-api-host', required=True,
                        help="Location of analyitcs-api IDA for request routing")
    parser.add_argument('--registrar-host', required=True,
                        help="Location of registrar IDA for request routing")
    parser.add_argument('--enterprise-catalog-host', required=True,
                        help="Location of enterprise catalog IDA for request routing")

    args = parser.parse_args()

    session = botocore.session.get_session()
    apig = session.create_client('apigateway', args.aws_region)

    # Look up API ID based on the custom domain link.
    (api_id, current_stage) = get_api_id(apig, args.api_base_domain)

    # Get the next stage in rotation.
    new_stage = get_next_stage(args.rotation_order, current_stage)

    # Activate the API with the requested stage variables.
    deploy_api(apig, api_id, args.swagger_filename, new_stage, {
        'id': args.tag,
        'landing_page': args.landing_page,
        'edxapp_host': args.edxapp_host,
        'discovery_host': args.catalog_host,
        'enterprise_host': args.enterprise_host or args.edxapp_host,
        'gateway_host': args.api_base_domain,
        'analytics_api_host': args.analytics_api_host,
        'registrar_host': args.registrar_host,
        'enterprise_catalog_host': args.enterprise_catalog_host,
    })

    # Apply stage setting updates.
    update_stage(apig, api_id, new_stage, {
        'log_level': args.log_level,
        'metrics': args.metrics,
        'caching': args.caching,
        'rate_limit': args.rate_limit,
        'burst_limit': args.burst_limit
    })

    # Return new stage name.
    print new_stage
