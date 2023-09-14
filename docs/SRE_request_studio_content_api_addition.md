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
- Download this `api-manager` repo onto the EC2 instance hosting the API Gateway
  - Set the working directory on a shell you'll be using to run scripts on to this repo's root directory


## <a name="stage-runbook"></a> Deploy, activate, and test on stage


### Generate an ACM certificate for use with the custom domain name we're about to create
- go to AWS Certificate Manager (ACM) (off of top-level serices icon)
- Push orange "Request" button
- Push orange "Next" button with default "Request a public certificate" selected
- Enter the fully qualified domain name "studio.api.stage.edx.org"
- Push orange "Request" button (accepting defaults for everything else)
- Back at ACM, should see a success banner with a "View Certificate" button. Push the button
- Should now see the new certificate in a "Pending validation" state
- In the "Domains" pane of this certificate display there is a "Create records in Route 53". You
must take this action for this certificate to exit "Pending validation" state
    - Push the "Create records in Route 53" button
    - In the next screen, accept all defaults and push the "Create records" orange button
    - You should be redirected to the certificate display screen, with a green success banner reading
        "Successfully created DNS records in Amazon Route 53 ..."
    - It will take maybe 10 minutes for the DNS records to match this newly created certificate. After some
    such delay you'll see this comain name's status change to a green Success status
- Your certificate is ready for use

### Create a custom domain name

- Select API Gateway "Custom domain names" menu link item
- click on "Create" button
- Enter `studio.api.stage.edx.org` as as the domain name to be created
- Select your newly created certificate in the "Endpoint configuration" panel, under "ACM Certificate"
- click the orange "Create domain name" button
- On success you'll be redirected to the Custom domain names view, with a green "Successfully created domain name ..."
banner


### Create a placeholder API object with a single "GET" method
    - Motivation:
        - The `api-manager` scripts we'll be running expect a deployed API on the custom domain name as a starting point
        - The newly created custom domain name currently has no APIs or deployments associated with it
    - Select the API Gateway "APIs" menu item link
    - Click the orange "Create API" button
    - Go to the REST API panel and click the oranage "Build" button within it
    - Enter "Studio content" as the API name and click the "Create API" button
    - You'll be redirected to the Studio content API Resources view
        - click the Actions button and select Create method
        - in the new pull-down box you're offered, select GET
        - click on the edit icon for this method
            - select HTTP integration type
            - enable "Use HTTP Proxy integration"
            - enter a bogus http://example.com for Endpoint URL (we'll never actually use this method)
            - click the Save button
            - On success you'll be presented with a request flow diagram through the system

### Deploy your placeholder API
    - Select the API Gateway "APIs" menu item link
    - select your newly created API
    - You'll now be on the API:Studio content, resources view
        - click the Actions button and select "Deploy API"
        - In the dialog box you're presented, select new stage from the Deployment Stage pull down menu
        - Enter Cerulean for the stage name and click the Deploy button
        - On success you'll be on the API: Studio content, Stages view
        - Select the "Deployment History" tab to see the deployment you just created

### Map your newly created, deployed API to your custom domain name
    - Select the API Gateway "Custom domain name" menu link item
    - Select the studio.api.stage.edx.org custom domain name
    - Click on the "API mappings" tab
    - Click on the "Configure API mappings" button and then on the "Add new mapping" button
    - Select the Studio content API on the API box
    - Select the Cerulean stage on the Stage box
    - Click on the "Save" button
    - On success you'll be redirected to the custom domain names view, with a green success banner "Successfully
    updated API mappings"
    - In the displayed API Mappings tab, you'll now see the current stage for the Studio content API shown as Cerulean

### Deploy the real Studio API (as opposed to the placeholder API deployed above)

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

The above steps in no way affect live deployments of currently deployed APIs. No rollback mechanism is required. Unless
the scripts are edited, it's not even possible to "fat finger" the process, as the scripts are hard-wired for the new
custom domain names.

### Add metrics and alerts for new studio API

No additional work is required for AWS-based metrics and alerts. Existing metrics discriminate on the basis of API
gateway, API ID, and stage. We're still operating with the existing API Gateway, and we've added a new API ID and a new
stage. Existing metrics and alerts will continue to run, but will generate charts and alerts that identify
that they're responding to traffic from the new API ID and the new stage.

It's possible that additional work is required for New Relic monitoring and alerting. This can occur at a later time.


## <a name="prod-runbook"></a> Deploy, activate, and test on prod

Follow the same flow as prescribed for the stage environment, but with scripts out of the `scripts/aws/invocation_history/prod` folder.
Note that the name for the experimental API gateway stage we use here is `cerulean` (corresponding to our use of `chartreuse`
on stage), and that we now use `prod_black` instead of `yellow` as the API gateway stage that had been live



