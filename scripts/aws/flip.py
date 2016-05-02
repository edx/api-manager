#!/usr/bin/python

"""Various functions for day-to-day management of AWS API Gateway instances."""

import argparse
import sys
import logging
import botocore.session
import botocore.exceptions


def get_live_stage(client, api_base):
    """Get the current live stage tied to this base path."""
    try:
        response = client.get_base_path_mapping(
            domainName=api_base,
            basePath='(none)')
    except botocore.exceptions.ClientError:
        logging.error('No mapping found for "%s", have you bootstrapped it yet?', api_base)
        sys.exit(1)

    logging.info('Found existing base path mapping for API ID "%s", stage "%s"',
                 response['restApiId'], response['stage'])

    return response['stage']


def update_base_path_mapping(client, api_base, stage_name):
    """Flip base path pointer to new gateway object so it starts receiving real traffic."""

    try:
        response = client.update_base_path_mapping(
            domainName=api_base,
            basePath='(none)',
            patchOperations=[
                {'op': 'replace', 'path': '/stage', 'value': stage_name}
            ])
    except botocore.exceptions.ClientError:
        logging.error('Stage "%s" does not yet exist. Aborting operation.', stage_name)
        raise

    logging.info('API Gateway domain "%s" updated to "%s"', api_base, stage_name)
    return response


if __name__ == '__main__':

    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s %(message)s')

    parser = argparse.ArgumentParser()

    parser.add_argument("--aws-region", required=False, default="us-east-1")
    parser.add_argument("--api-base-domain", required=True,
                        help="The name of the API Gateway domain to be created.")
    parser.add_argument("--next-stage", required=True,
                        help="The name of the API Gateway stage to be activated.")

    args = parser.parse_args()

    session = botocore.session.get_session()
    apig = session.create_client('apigateway', args.aws_region)

    # Make sure we aren't doing any redundant work
    if args.next_stage == get_live_stage(apig, args.api_base_domain):
        logging.info('Stage "%s" is already the live stage; nothing to do here.', args.next_stage)

    # Flip the base path pointer to the new stage
    else:
        update_base_path_mapping(apig, args.api_base_domain, args.next_stage)
