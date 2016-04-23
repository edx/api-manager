#!/usr/bin/python

"""Various functions to bootstrap new AWS API Gateway instances."""

import sys
import logging
import botocore.session
import botocore.exceptions


def test_domain_exists(client, api_base):
    """Make sure the domain of interest actually exists before bootstrapping."""
    try:
        client.get_domain_name(domainName=api_base)
    except botocore.exceptions.ClientError:
        logging.error('Could not find custom domain "%s", has it been configured yet?', api_base)
        sys.exit(1)

    return True


def test_no_base_path_exists(client, api_base):
    """Get the current live API ID and stage tied to this base path."""
    try:
        mapping = client.get_base_path_mapping(
            domainName=api_base,
            basePath='(none)')
    except botocore.exceptions.ClientError:
        logging.info('No base path exists yet, proceeding with bootstrap.')
        return True

    logging.error('Found existing base path mapping for API ID "%s", stage "%s"',
                  mapping['restApiId'], mapping['stage'])
    return False


def bootstrap_api(client, stage_name):
    """
    Upload a bootstrap Swagger document to a new API Gateway object and set it live
    with environment-specific variables.
    """

    bootstrap_swagger = open('bootstrap.json', 'r')

    response = client.import_rest_api(body=bootstrap_swagger.read())
    logging.info('New bootstrap API ID "%s" created', response['id'])

    client.create_deployment(
        restApiId=response['id'],
        stageName=stage_name)
    logging.info('API ID "%s" deployed to stage "%s"', response['id'], stage_name)

    return response['id']


def create_base_path_mapping(client, api_id, api_base, stage_name):
    """Link a custom domain with an API Gateway object stage"""

    # Note: this will fail if a mapping already exists (bootstrapping is not idempotent).
    response = client.create_base_path_mapping(
        domainName=api_base,
        basePath='(none)',
        restApiId=api_id,
        stage=stage_name
    )
    logging.info("Domain '%s' now pointed to '%s':'%s'", api_base, api_id, stage_name)
    return response


def main(log_level=20):
    """Update an AWS API Gateway object from a Swagger configuration file."""

    logging.basicConfig(level=log_level, format='[%(asctime)s] %(levelname)s %(message)s')

    if len(sys.argv) != 2:
        logging.error('Usage: %s <api-base-domain>', sys.argv[0])
        sys.exit(1)

    api_base = sys.argv[1]
    stage_name = 'bootstrap'

    session = botocore.session.get_session()
    apig = session.create_client('apigateway')

    test_domain_exists(apig, api_base)

    if test_no_base_path_exists(apig, api_base):

        #  Create new dummy API Gateway object and deploy to a stage
        api_id = bootstrap_api(apig, stage_name)

        # Link custom domain to stage (base path mapping)
        create_base_path_mapping(apig, api_id, api_base, stage_name)

        logging.info('Bootstrap successful.')

    else:
        logging.info('Bootstrap not necessary.')


if __name__ == '__main__':
    main()
