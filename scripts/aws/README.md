## scripts/aws
The `api-manager` Swagger documents in this repository contain some vendor-specific deployment hooks. This directory contains a few scripts that help with deploying your very own api-manager to Amazon Web Services' API Gateway service.

You *do not* need to deploy an API Manager in your Open edX installation, and you *do not* need to use Amazon here. But if you choose to go this route, and want to use Amazon's gateway service, feel free to use these tools to get started.

### Setup
See the requirements.txt file for more information on the various Python dependencies needed. Just run `pip install -r requirements.txt` in this directory to get started. Right now, only `botocore` is necessary beyond the stock Python packages.

### Design
Before getting started here, please familiarize yourself with [Amazon API Gateway](https://aws.amazon.com/api-gateway/).

The approach these scripts take to deployment is not standard (we're not sure there _is_ a standard) and may not fit your exact use case. Where possible, we will call out API Gateway specific objects as `aws.apigateway.X` below.

The flow is as follows:

1. *Pre-work*: we expect that each API lives behind a custom domain (`aws.apigateway.DomainName`) that has already been provisioned - see [the AWS docs](http://docs.aws.amazon.com/apigateway/latest/developerguide/how-to-custom-domains.html) for more detail.

2. *Bootstrapping*: the [bootstrap](bootstrap.py) script creates a new `aws.apigateway.RestApi` object and deploys it to a "bootstrap" `aws.apigateway.Stage` with a simple hello-world API defined by [bootstrap.json](bootstrap.json).

3. *Build*: clone this repo and point [swagger-codegen](https://github.com/swagger-api/swagger-codegen) at the top-level `api.yaml` file to generate a "flattened" Swagger JSON document (hint: use `-l swagger`).

4. *Deployment*: the [deploy](deploy.py) script takes the flattened Swagger document and uploads it to the `aws.apigateway.RestApi` in a new stage, following a simple "ring" approach. (Given an ordered list of stages, the script will figure out which stage is live and automatically push to the next stage in the sequence.)

5. *Activation*: the [flip](flip.py) script updates the `aws.apigateway.DomainName` to point to the newly deployed stage - or, more specifically, whatever stage you want. You can also use this script to quickly roll back your API to a previous stage in the ring.

### Environment
First, make sure `AWS_REGION`, `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` are set up as per [AWS' instructions](http://boto3.readthedocs.org/en/latest/guide/configuration.html#environment-variables).

There are a few custom environment variables required for the `deploy` script to work. At some point, we'll probably move some of these to be command-line arguments.
* `STAGE_ROTATION_ORDER`: comma-separated list of stages in your "ring". Be aware of your AWS account's limit on stages per gateway. Example: `red,black`
* `STAGE_EDXAPP_HOST`: the API base of your edx-platform service deployment
* `STAGE_DISCOVERY_HOST`: the API base of your course-discovery service deployment (just set to an empty or dummy string if you aren't using this in your specific Open edX deployment)
* `STAGE_ENTERPRISE_HOST`: the API base of your enterprise service deployment (just set to an empty or dummy string if you aren't using this in your specific Open edX deployment)

And some environment variables for provisioning specific stage settings (see the [AWS docs](http://docs.aws.amazon.com/apigateway/latest/developerguide/how-to-stage-settings.html) for more on the allowed values and examples):
* `STAGE_LOG_LEVEL`
* `STAGE_METRICS`
* `STAGE_CACHING`
* `STAGE_RATE_LIMIT`
* `STAGE_BURST_LIMIT`
