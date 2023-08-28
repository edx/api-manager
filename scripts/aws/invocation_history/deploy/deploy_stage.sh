# Calls deploy.sh script with command line arguments tailored to the stage environment
#   each deployment is to a single (new) AWS stage
#  8/28/2023 Created
#  8/28/2023   new stage = Cerulean, includes Studio content host variable,

# Usage assumes working directory to be the api-manager repo's base folder
#

python3 ./scripts/aws/deploy.py
{
  --tag ukf9g3meqi                    # AWS API ID for the API whose Resource configuration is to be overwritten
  --api-base-domain gwtst.edx.us.org  # AWS Custom Domain Name that's been mapped to the selected API
  --swagger-filename ./swagger/api.json
  --landing-page https://stage.edx.org
  --rotation-order Cerulean
  --edxapp-host courses.stage.edx.org
  --enterprise-host enterprise-catalog.stage.edx.org
  --analytics-api-host stage-edx-analyticsapi.edx.org
  --registrar-host stage-edx-registrar.edx.org
  --enterprise-catalog-host enterprise-catalog.stage.edx.org
  --studio-host courses.stage.edx.org
}
