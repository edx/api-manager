#!/usr/bin/python

"""Various functions for day-to-day management of AWS API Gateway instances."""

import argparse
import logging
from scripts.aws.common.deploy import deploy

if __name__ == '__main__':

    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s %(message)s')

    parser = argparse.ArgumentParser()

    parser.add_argument("--aws-region", required=False, default="us-east-1")
    parser.add_argument(
        "--api-base-domain", required=True,
        help="The name of the API Gateway domain to be created."
    )
    parser.add_argument(
        "--swagger-filename", required=True,
        help="The name of a complete Swagger 2.0 specification file with AWS vendor hooks."
    )
    parser.add_argument(
        "--tag", required=True,
        help="Unique identifier for this deployment (such as a git hash)"
    )
    parser.add_argument(
        "--rotation-order", required=True, nargs='+',
        help="Ordered list of stages in the deployment ring (ex: 'red black')"
    )
    parser.add_argument(
        "--log-level", required=False, default="OFF", choices=['OFF', 'ERROR', 'INFO'],
        help="Verbosity of messages sent to CloudWatch Logs"
    )
    parser.add_argument(
        "--metrics", required=False, default="false", choices=['false', 'true'],
        help="Enable CloudWatch metrics"
    )
    parser.add_argument(
        "--caching", required=False, default="false", choices=['false', 'true'],
        help="Enable API Gateway caching feature"
    )
    parser.add_argument(
        "--rate-limit", required=False, default="500", type=str,
        help="Default per-resource average rate limit"
    )
    parser.add_argument(
        "--burst-limit", required=False, default="1000", type=str,
        help="Default per-resource maximum rate limit"
    )
    parser.add_argument(
        "--landing-page", required=True,
        help="Location of landing page for 'root' level requests"
    )
    parser.add_argument(
        "--edxapp-host", required=True,
        help="Location of edxapp for request routing"
    )
    parser.add_argument(
        "--catalog-host", required=True,
        help="Location of catalog IDA for request routing"
    )
    parser.add_argument(
        "--enterprise-host", required=False, default='',
        help="Location of enterprise IDA for request routing"
    )
    parser.add_argument(
        '--analytics-api-host', required=True,
        help="Location of analyitcs-api IDA for request routing"
    )
    parser.add_argument(
        '--registrar-host', required=True,
        help="Location of registrar IDA for request routing"
    )
    parser.add_argument(
        '--enterprise-catalog-host', required=True,
        help="Location of enterprise catalog IDA for request routing"
    )
    parser.add_argument(
        '--authoring-host', required=True,
        help="Location of Studio for authoring request routing"
    )
    parser.add_argument(
        '--license-manager-host', required=True,
        help="Location of License Manager IDA for request routing"
    )
    parser.add_argument(
        '--enterprise-access-host', required=True,
        help="Location of Enterprise Access IDA for request routing"
    )

    cli_args = parser.parse_args()
    integration_settings = {
        'id': cli_args.tag,
        'landing_page': cli_args.landing_page,
        'edxapp_host': cli_args.edxapp_host,
        'discovery_host': cli_args.catalog_host,
        'enterprise_host': cli_args.enterprise_host or cli_args.edxapp_host,
        'gateway_host': cli_args.api_base_domain,
        'analytics_api_host': cli_args.analytics_api_host,
        'registrar_host': cli_args.registrar_host,
        'enterprise_catalog_host': cli_args.enterprise_catalog_host,
        'authoring_host': cli_args.authoring_host,
        'license_manager_host': cli_args.license_manager_host,
        'enterprise_access_host': cli_args.enterprise_access_host
    }
    stage_settings = {
        'log_level': cli_args.log_level,
        'metrics': cli_args.metrics,
        'caching': cli_args.caching,
        'rate_limit': cli_args.rate_limit,
        'burst_limit': cli_args.burst_limit
    }
    deploy(cli_args, integration_settings, stage_settings)
