# api-manager
Specifications and optional lightweight service for routing clients of the Open edX REST API to various endpoints within the platform.

## About
The API Manager is a *work in progress* and is meant to define an independently deployable application that acts as an interface to developers building on top of Open edX REST APIs. The APIs listed in this repository are not a comprehensive list of the Open edX REST API set, just the endpoints most valuable to an external API consumer.

At the moment, this repository is a working prototype and is not officially supported or part of an Open edX release. As with other Open edX codebases, please take a look at [our Contributing docs](https://github.com/edx/edx-platform/blob/master/CONTRIBUTING.rst) if you'd like to help build out this capability.

## Specification
The API Manager is defined by an [Open API / Swagger](https://github.com/OAI/OpenAPI-Specification) specification document at [swagger/api.yaml](swagger/api.yaml). You can point [swagger-codegen](https://github.com/swagger-api/swagger-codegen) at this document to generate a lightweight SDK in many languages, or just flatten the nested references into a single Swagger document using the `swagger` (JSON) or `swagger-yaml` (YAML) language options.

## Vendor extensions
Initially, we will provide vendor extensions for Amazon Web Services' [API Gateway](https://aws.amazon.com/api-gateway). The flattened Swagger document (see note above) should "just work" when using Amazon's `ImportRestApi` feature. Note that stage variables still need to be defined that are specific to your Open edX installation. To be clear, while you may use AWS API Gateway for your specific Open edX instance, we are intentionally isolating vendor-specific hooks to avoid any lock-ins.

In addition, the `api.yaml` file should also "just work" when loaded into Swagger UI (see http://petstore.swagger.io as an example). Note that you will need to modify the base path and potentially instrument CORS headers if you want to use Swagger UI for truly interactive documentation.
 
