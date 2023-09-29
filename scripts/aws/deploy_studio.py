#!/usr/bin/python

"""Various functions for day-to-day management of AWS API Gateway instances."""

import argparse
import logging
from scripts.aws.common.deploy import deploy

if __name__ == '__main__':

    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s %(message)s')

    parser = argparse.ArgumentParser()

    parser.add_argument("--aws-region", required=False, default="us-east-1")
    parser.add_argument("--api-base-domain", required=True,
                        help="The name of the API Gateway domain to be deployed to.")
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
    parser.add_argument('--studio-host', required=True,
                        help="Location of Studio IDA for request routing")

    args = parser.parse_args()
    cli_args = parser.parse_args()
    integration_settings = {
        'id': cli_args.tag,
        'landing_page': cli_args.landing_page,
        'edxapp_host': cli_args.edxapp_host,
        'studio_host': cli_args.studio_host,
    }
    stage_settings = {
        'log_level': cli_args.log_level,
        'metrics': cli_args.metrics,
        'caching': cli_args.caching,
        'rate_limit': cli_args.rate_limit,
        'burst_limit': cli_args.burst_limit
    }
    deploy(cli_args, integration_settings, stage_settings)
