# Calls deploy.sh script with command line arguments tailored to the stage environment
#   each deployment is to a single (new) AWS stage
#  8/28/2023 Created
#  8/28/2023   new stage = Cerulean, yincludes Studio content host variable,

# Usage (assumes working directory to be the api-manager repo's base folder)
# ./scripts/aws/deploy_repo_to_prod_env_api_gw.sh <aws stage name>

python3 ./scripts/aws/deploy.py \
  --tag  None
  --api-base-domain $1  # AWS Custom Domain Name that's been mapped to the selected API \
  --swagger-filename ./swagger/api.yaml \
  --landing-page https://stage.edx.org \
  --rotation-order Cerulean \
  --edxapp-host courses.stage.edx.org \
  --enterprise-host enterprise-catalog.stage.edx.org \
  --analytics-api-host stage-edx-analyticsapi.edx.org \
  --registrar-host stage-edx-registrar.edx.org \
  --catalog-host catalog.stage.edx.org \
  --enterprise-catalog-host enterprise-catalog.stage.edx.org \
  --studio-host courses.stage.edx.org
