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
    except botocore.exceptions.ClientError as exc:
        raise ValueError('No mapping found for "%s"' % api_base_domain) from exc  # pylint: disable=consider-using-f-string

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

    swagger = open(swagger_filename, 'r', encoding="utf-8")  # pylint: disable=consider-using-with

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

def deploy(cli_args, integration_settings, stage_settings):
    session = botocore.session.get_session()
    apig = session.create_client('apigateway', cli_args.aws_region)

    # Look up API ID based on the custom domain link.
    (api_id, current_stage) = get_api_id(apig, cli_args.api_base_domain)

    # Get the next stage in rotation.
    new_stage = get_next_stage(cli_args.rotation_order, current_stage)

    # Activate the API with the requested stage variables.
    deploy_api(apig, api_id, cli_args.swagger_filename, new_stage, integration_settings)

    # Apply stage setting updates.
    update_stage(apig, api_id, new_stage, stage_settings)

    # Return new stage name.
    print(new_stage)
