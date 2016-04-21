#!/usr/bin/python

"""Various functions for day-to-day management of AWS API Gateway instances."""

import os
import sys
import logging
import botocore.session
import botocore.exceptions

def get_live_stage(client, api_base):
    """Get the current live stage tied to this base path."""
    try:
        mapping = client.get_base_path_mapping(
            domainName=api_base,
            basePath='(none)')
    except botocore.exceptions.ClientError:
        logging.error('No mapping found for "%s", have you bootstrapped it yet?', api_base)
        sys.exit(1)

    logging.info('Found existing base path mapping for API ID "%s", stage "%s"',\
        mapping['restApiId'], mapping['stage'])

    return mapping['stage']

def update_base_path_mapping(client, api_base, stage_name):
    """Flip base path pointer to new gateway object so it starts receiving real traffic."""

    try:
        base_path_update = client.update_base_path_mapping(
            domainName=api_base,
            basePath='(none)',
            patchOperations=[
                {'op':'replace', 'path':'/stage', 'value': stage_name}
            ])
    except botocore.exceptions.ClientError:
        logging.error('Stage "%s" does not yet exist. Aborting operation.', stage_name)
        sys.exit(1)

    logging.info('API Gateway domain "%s" updated to "%s"', api_base, stage_name)
    return base_path_update

def main(log_level=20):
    """Update an AWS API Gateway object from a Swagger configuration file."""

    logging.basicConfig(level=log_level, format='[%(asctime)s] %(levelname)s %(message)s')

    if len(sys.argv) != 3:
        logging.error('Usage: %s <api-base-domain> <next-stage>', sys.argv[0])
        sys.exit(1)

    api_base = sys.argv[1]
    next_stage = sys.argv[2]

    session = botocore.session.get_session()
    apig = session.create_client('apigateway', os.environ['AWS_REGION'])

    # Make sure we aren't doing any redundant work
    if next_stage == get_live_stage(apig, api_base):
        logging.info('Stage "%s" is already the live stage; nothing to do here.', next_stage)

    # Flip the base path pointer to the new stage
    else:
        update_base_path_mapping(apig, api_base, next_stage)

if __name__ == '__main__':
    main()
