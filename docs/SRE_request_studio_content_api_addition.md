# tl;dr
TNL is requesting support from SRE team with AWS API Gateway configuration steps that require privileges we lack.
See [stage runbook](#stage-runbook) section below for concrete steps needed to update the API Gateway on stage.
See [prod runbook](#prod-runbook) section below for similar steps to follow up on prod.

As the repo used to control the API Gateway, the `api-manager` repo, has fallen out of use, we've included a
[Background](#background) section in this document to provide context for the requested operations.

# <a name="background"></a> Background

## Discovery
 
- The TNL team is adding the Studio content public API and intends for that to be offered via our shared AWS API gateway.
- TNL has conducted a [discovery activity](https://2u-internal.atlassian.net/browse/TNL-10899) surrounding use of this repo using the playground AWS account
  - The repo hasn't received active attention for some time. 
  - Generic API Gateway learnings from that activity are documented in "configuration_objects.md" in this folder
  - edX-specific learnings from that activity follow here and are incorporated into this document's [runbook](#runbook) section

## Last "go live" date from repo updates was September 20, 2021
- Review of __api_manager__ repo [commits](https://github.com/edx/api-manager/commits/master)  shows a steady stream of python requirement upgrades, marked as "Verified" commits
  - The non-verified commits are by the `edx-requirements-bot`
  - The verified commits are merge commits, frequently run by Usama Sadiq and M Umar Khan, both of Arbisoft
- Review of the [deployment history for the prod_red stage for the prod environment custom domain name on the API Gateway (prod_black)](https://us-east-1.console.aws.amazon.com/apigateway/home?region=us-east-1#/apis/v96bizdp9b/stages/prod_red) reveals that it is this stage that the python upgrade merges are being applied to as new deployments
- But the [live stage for the prod environment custom domain name](https://us-east-1.console.aws.amazon.com/apigateway/main/publish/domain-names/api-mappings?domain=api.edx.org&region=us-east-1) is not `prod_red`, but `prod_black`
  - And `prod_black` has not been updated with new commits since September 20, 2021: no changes to the repo have gone live since that date
- Similar review of "go live dates" for other stages for the prod environment custom domain are even older
  - June 27, 2016 for "black"
  - June 27, 2016 for "red"
- For the stage environment
  - The "Yellow" stage is live and is current with the latest repo commits and deployments
  - Other named stages are behind Yellow, but not by much; unclear who is using these, or how

## The API Gateway supports an "omnibus" API
- The "API" offered by the API Gateway is an amalgamation of edX APIs (discovery, enterprise, registrar)
  - Specification of the omnibus API is in [swagger/api.yaml](https://github.com/edx/api-manager/blob/master/swagger/api.yaml)
- The last [substantive PR](https://github.com/edx/api-manager/pull/127) was on September 20, 2021, adding [v3 enterprise customer endpoints](https://github.com/edx/api-manager/pull/127/files)
  - That PR and merge line up with the last "go live" date for the prod environment API Gateway (`prod_black` stage)

## Changes made with introduciton of a new API
The registrar API was added to `api-manager` in commits dated 4/17/2019 through the merge #87 commit of 6/26/2019.

They entail adding the proxy description of the API to `swagger/api.yaml`
They entail adding a registrar host variable to `scripts/aws/deploy.py`

Corresponding steps were taken to add the Studio content API

## Command line arguments to `deploy.py` and `flip.py`

Both these repo commands take multiple command-line arguments, yet the values supplied with deployment and "go-live"
events are not documented in the repo.

### Command line arguments for `deploy.py`

The call to the boto/apigateway function that carries out deployments is as follows:

>    deploy_api(apig, api_id, args.swagger_filename, new_stage, {
>        'id': args.tag,
>        'landing_page': args.landing_page,
>        'edxapp_host': args.edxapp_host,
>        'discovery_host': args.catalog_host,
>        'enterprise_host': args.enterprise_host or args.edxapp_host,
>        'gateway_host': args.api_base_domain,
>        'analytics_api_host': args.analytics_api_host,
>        'registrar_host': args.registrar_host,
>        'enterprise_catalog_host': args.enterprise_catalog_host,
>        'studio_host': args.studio_host,
>    })

Of the command line arguments used in this call (all the `args.something` vaiables), most are integration hosts, and
the values that were supplied at script invocation time are persisted in AWS gateway objects, under 
"Custom domain names -> api.edx.org -> API mappings tab -> prod_black link -> Stage variables". Once there, you also 
find persisted values for `args.id` and `args.landing_page`.

This leaves only the value used for the `args.swagger_filename` unaccounted for, and that's just the pathname for
the `swagger/api.yaml` file in this repo.

### Command line arguments for `flip.py`

The call to the boto/apigateway function that promotes a new stage to live status is as follows:

>         update_base_path_mapping(apig, args.api_base_domain, args.next_stage)

Only two command line arguments are used. The first, `args.api_base_domain` is the API Gateway custom domain name
associated with the API in question. The second, `args.next_stage` is the name of the stage going live in support
of that API.



# <a name="runbook"></a> SRE Runbook

## Preliminaries

- Review this document
- Verify that APIs on API Gateway are up and running on stage and prod as expected
- Verify that "yellow" is the live AWS stage on the api.stage.edx.org API Gateway custom domain
- Verify that "prod_black" is the live AWS stage on the api.edx.org API Gateway custom domain
- Download this `api-manager` repo onto the EC2 instance hosting the API Gateway
  - Set the working directory on a shell you'll be using to run scripts on to this repo's root directory


## <a name="stage-runbook"></a> Deploy, activate, and test on stage

### Deploy

- Deploy the API swagger specification with the Studio content API in it onto API Gateway resources, 
- creating a new API Gateway stage named chartreuse

> ./scripts/aws/invocation_history/stage/0001_deploy_studio_on_chartreuse.sh

- Verify that the "yellow" AWS stage remains the active stage for the `api.stage.edx.org` custom domain
- Verify that pre-Studio APIs on API Gateway on stage environment are up and running, as expected

### Activate

Go live with the newly imported Studio content API endpoints (API Gateway resources) with:

> ./scripts/aws/invocation_history/stage/0002_chartreuse_goes_live.sh

- Verify that the "chartreuse" AWS stage is now the active stage for the `api.stage.edx.org` custom domain
- Verify that the public APIs on the stage environment API Gateway have suffered no regressions
- Verify that the studio API on the stage environment is now working as expected

### Roll back in case of failure

- In case activation failed, roll back on the stage environment to the AWS stage that had been live prior to this exercise

> ./scripts/aws/invocation_history/stage/1000_rollback_to_yellow.sh

- Verify that the "yellow" API Gateway stage is now the active stage for the `api.stage.edx.org` custom domain
- Verify that the public APIs on the stage environment API Gateway have suffered no regressions
- Verify that the Studio content API endpoints are not offered

### Restore yellow as active AWS stage for future Python upgrades

The process we follow with python upgrades expects the active AWS stage to be 'yellow'. Make it so.
This differs from the rollback step, in that here we want the live API Gateway to continue offering Studio content API endpoints

> ./scripts/aws/invocation_history/stage/0003_deploy_studio_on_yellow.sh
> ./scrits/aws/invocation_history/stage/0004_yellow_goes_live.sh

- Verify that the "yellow" API Gateway stage is now the active stage for the `api.stage.edx.org` custom domain
- Verify that the public APIs on the stage environment API Gateway have suffered no regressions
- Verify that the studio API on the stage environment is now working as expected


## <a name="prod-runbook"></a> Deploy, activate, and test on prod

Follow the same flow as prescribed for the stage environment, but with scripts out of the `scripts/aws/invocation_history/prod` folder.
Note that the name for the experimental API gateway stage we use here is `cerulean` (corresponding to our use of `chartreuse`
on stage), and that we now use `prod_black` instead of `yellow` as the API gateway stage that had been live



