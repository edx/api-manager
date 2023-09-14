# Calls flip.sh script with command line arguments tailored to the stage environment
#   each deployment is to a single (new) AWS stage
#  8/29/2023 Created
#  8/29/2023   Set the active stage to Cerulean, from red (used on playground account)

# Usage assumes working directory to be the api-manager repo's base folder
#

python3 ./scripts/aws/flip.py \
 --api-base-domain studio.api.stage.edx.org  \
 --next-stage $1
