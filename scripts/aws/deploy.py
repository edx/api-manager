#!/usr/bin/python

"""Various functions for day-to-day management of AWS API Gateway instances."""

import os
import sys
import logging
import botocore.session
import botocore.exceptions


def get_api_id(client, api_base):
    """Get the current live API ID and stage tied to this base path."""
    try:
        mapping = client.get_base_path_mapping(
            domainName=api_base,
            basePath='(none)')
    except botocore.exceptions.ClientError:
        raise ValueError('No mapping found for "%s"', api_base)

    logging.info('Found existing base path mapping for API ID "%s", stage "%s"',
                 mapping['restApiId'], mapping['stage'])

    return (mapping['restApiId'], mapping['stage'])


def get_next_stage(rotation, cur_stage):
    """
    Based on a pre-set stage rotation order, and a pointer to the current location in the order,
    determine the next stage based on a simple circular iteration. If the pointer is invalid,
    start at the first stage.
    """

    next_index = 0

    if len(rotation) == 0:
        raise ValueError("No rotation order provided, cannot return next stage.")

    try:
        cur_index = rotation.index(cur_stage)

        # Circular iteration. If we're at the end, go back to the beginning!
        if cur_index < len(rotation) - 1:
            next_index = cur_index + 1

    except ValueError:
        logging.info('Stage "%s" is not in the rotation, starting from the top.', cur_stage)

    next_stage = rotation[next_index]

    logging.info('Rotating from stage "%s" to "%s".', cur_stage, next_stage)
    return next_stage


def deploy_api(client, api_id, swagger_filename, stage_name, stage_config):
    """
    Upload the Swagger document to an existing API Gateway object and set it live
    with environment-specific variables.
    """

    swagger = open(swagger_filename, 'r')
    response = client.put_rest_api(restApiId=api_id, mode='overwrite', body=swagger.read())
    logging.info('Existing API ID "%s" updated (name "%s")', response['id'], response['name'])

    deployment = client.create_deployment(
        restApiId=api_id,
        stageName=stage_name,
        variables=stage_config['variables'])

    logging.info('API ID "%s" deployed (deployment ID %s)', api_id, deployment['id'])


def update_stage(client, api_id, stage_name, stage_config):
    """
    Modify deployed stage with throttling, logging and caching settings.
    Note that you can define path-level overrides if you want; we're not
    tackling that at this time but it's theoretically possible.
    """

    settings = stage_config['settings']

    stage_update = client.update_stage(
        restApiId=api_id,
        stageName=stage_name,
        patchOperations=[
            {'op': 'replace', 'path': '/*/*/logging/loglevel', 'value': settings['log_level']},
            {'op': 'replace', 'path': '/*/*/metrics/enabled', 'value': settings['metrics']},
            {'op': 'replace', 'path': '/*/*/caching/enabled', 'value': settings['caching']},
            {'op': 'replace', 'path': '/*/*/throttling/rateLimit', 'value': settings['rate_limit']},
            {'op': 'replace', 'path': '/*/*/throttling/burstLimit', 'value': settings['burst_limit']}
        ])

    logging.info('API ID "%s", stage "%s" updated with settings: %s',
                 api_id, stage_name, stage_update['methodSettings'])


def main(log_level=20):
    """Update an AWS API Gateway object from a Swagger configuration file."""

    logging.basicConfig(level=log_level, format='[%(asctime)s] %(levelname)s %(message)s')

    if len(sys.argv) != 4:
        logging.error('Usage: %s <api-base-domain> <swagger-filename> <tag>', sys.argv[0])
        sys.exit(1)

    api_base = sys.argv[1]
    swagger_filename = sys.argv[2]
    tag = sys.argv[3]

    rotation_order = os.environ['STAGE_ROTATION_ORDER'].split(',')
    stage_config = {
        'settings': {
            'log_level': os.environ['STAGE_LOG_LEVEL'],
            'metrics': os.environ['STAGE_METRICS'],
            'caching': os.environ['STAGE_CACHING'],
            'rate_limit': os.environ['STAGE_RATE_LIMIT'],
            'burst_limit': os.environ['STAGE_BURST_LIMIT']
        },
        'variables': {
            'edxapp_host': os.environ['STAGE_EDXAPP_HOST'],
            'discovery_host': os.environ['STAGE_DISCOVERY_HOST'],
            'id': tag
        }
    }

    session = botocore.session.get_session()
    apig = session.create_client('apigateway', os.environ['AWS_REGION'])

    # Look up API ID based on the custom domain link.
    (api_id, current_stage) = get_api_id(apig, api_base)

    # Get the next stage in rotation.
    next_stage = get_next_stage(rotation_order, current_stage)

    # Activate the API with the requested stage variables.
    deploy_api(apig, api_id, swagger_filename, next_stage, stage_config)

    # Apply stage setting updates.
    update_stage(apig, api_id, next_stage, stage_config)

    # Return new stage name.
    print next_stage


if __name__ == '__main__':
    main()
