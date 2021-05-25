#!/usr/bin/python

"""Various functions to bootstrap new AWS API Gateway instances."""

import os
import logging
import argparse
import boto3
import botocore.exceptions


CLOUDFRONT_HOSTED_ZONE = "Z2FDTNDATAQYW2"


def get_domain(api_base):
    """Returns a dictionary response for the specified domain or None if the domain does not exit"""

    client = boto3.client('apigateway', region_name=args.aws_region)

    try:
        response = client.get_domain_name(domainName=api_base)
    except botocore.exceptions.ClientError:
        return None

    return response


def get_base_path(api_base):
    """Returns a dictionary response for the specified base path or None if the base path does not exist"""

    client = boto3.client('apigateway', region_name=args.aws_region)

    try:
        mapping = client.get_base_path_mapping(
            domainName=api_base,
            basePath='(none)')
    except botocore.exceptions.ClientError:
        return None

    return mapping


def create_apigw_custom_domain_name(domain_name, cert_name, cert_body, cert_pk, cert_chain):
    """Creates an api gateway custom domain entity"""

    client = boto3.client('apigateway', region_name=args.aws_region)

    try:
        response = client.create_domain_name(
            domainName=domain_name,
            certificateName=cert_name,
            certificateBody=cert_body,
            certificatePrivateKey=cert_pk,
            certificateChain=cert_chain
        )
    except Exception as e:
        raise e

    return response


def create_route53_rs(host_zone, domain_name, alias_target):
    """Creates a A record Alias pointing to the hostname of the api gateways internal cloudfront distribution"""
    client = boto3.client('route53', region_name=args.aws_region)

    changes = {"Changes": [{
        "Action": "UPSERT",
        "ResourceRecordSet": {
            "Name": domain_name + ".",
            "Type": "A",
            "AliasTarget": {
                "HostedZoneId": CLOUDFRONT_HOSTED_ZONE,
                "DNSName": alias_target + ".",
                "EvaluateTargetHealth": False
            }
        }
    }]}

    client.change_resource_record_sets(HostedZoneId=host_zone, ChangeBatch=changes)


def bootstrap_api(stage_name):
    """
    Upload a bootstrap Swagger document to a new API Gateway object and set it live
    with environment-specific variables.
    """

    client = boto3.client('apigateway', region_name=args.aws_region)

    # bootstrap.json is relative to me; where am I?
    my_dir = os.path.dirname(os.path.realpath(__file__))

    with open(my_dir + '/bootstrap.json', 'r') as bootstrap_swagger:

        response = client.import_rest_api(body=bootstrap_swagger.read())
        logging.info('New bootstrap API ID "%s" created', response['id'])

        client.create_deployment(
            restApiId=response['id'],
            stageName=stage_name)
        logging.info('API ID "%s" deployed to stage "%s"', response['id'], stage_name)

        return response['id']


def create_base_path_mapping(rest_api_id, api_base, stage_name):
    """Link a custom domain with an API Gateway object stage"""

    client = boto3.client('apigateway', region_name=args.aws_region)

    # Note: this will fail if a mapping already exists (bootstrapping is not idempotent).
    response = client.create_base_path_mapping(
        domainName=api_base,
        basePath='(none)',
        restApiId=rest_api_id,
        stage=stage_name
    )
    logging.info("Domain '%s' now pointed to '%s':'%s'", api_base, rest_api_id, stage_name)
    return response


def file_arg_to_string(filename):

    with open(filename, "r") as fin:
        body = fin.read()

    return body


if __name__ == '__main__':

    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s %(message)s')

    parser = argparse.ArgumentParser()

    parser.add_argument("--aws-profile", required=True)
    parser.add_argument("--aws-region", default="us-east-1")
    parser.add_argument("--stage-name", default="bootstrap")
    parser.add_argument("--api-base-domain", required=True,
                        help="The name of the API Gateway domain to be created.")
    parser.add_argument("--ssl-cert-name", required=True,
                        help="The name of the SSL certificate to associate with the daomin.")
    parser.add_argument("--ssl-cert", required=True,
                        help="The path to the file containing the SSL cert from the CA.")
    parser.add_argument("--ssl-pk", required=True,
                        help="The Private Key created when generating the CSR for the SSL certificte.")
    parser.add_argument("--ssl-cert-chain", required=True,
                        help="The certificate chain provided by the CA.")
    parser.add_argument("--route53-hosted-zone", required=True,
                        help="The AWS ID of the the Route53 hosted zone used for managing gateway DNS.")

    args = parser.parse_args()

    # Configure the default session and prompt for MFA token
    if args.aws_profile:
        boto3.setup_default_session(profile_name=args.aws_profile)

    # read file arguments into string vars
    ssl_cert = file_arg_to_string(args.ssl_cert)
    ssl_pk = file_arg_to_string(args.ssl_pk)
    ssl_cert_chain = file_arg_to_string(args.ssl_cert_chain)

    # Phase 1, create the api gateway "custom domain" and associated DNS record.

    # Note:
    # It can take up to 40 minutes for creation to complate.
    # Deletion takes time in the background, re-use of names, even for apparently
    # deleted domains can be problematic.
    domain = get_domain(args.api_base_domain)

    if not domain:
        logging.info("Custom domain does not exist, creating")
        domain = create_apigw_custom_domain_name(args.api_base_domain, args.ssl_cert_name,
                                                 ssl_cert, ssl_pk, ssl_cert_chain)

    logging.info("Upserting DNS for the custom domain.")
    create_route53_rs(args.route53_hosted_zone, args.api_base_domain, domain['distributionDomainName'])

    # Phase 2, create the api gateway and dummy base path mapping

    base_path = get_base_path(args.api_base_domain)

    if not base_path:

        #  Create new dummy API Gateway object and deploy to a stage
        api_id = bootstrap_api(args.stage_name)

        # Link custom domain to stage (base path mapping)
        create_base_path_mapping(api_id, args.api_base_domain, args.stage_name)

        logging.info('Bootstrap successful.')

    else:
        api_id = base_path['restApiId']
        logging.info('Bootstrap not necessary.')

    logging.info('Completed bootstrapping for API "%s".', api_id)
