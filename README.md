# api-manager
[![Build Status](https://travis-ci.com/edx/api-manager.svg?branch=master)](https://travis-ci.com/edx/api-manager)

Specifications and optional lightweight service for routing clients of the Open edX REST API to various endpoints within the platform.

## About
The API Manager is meant to define an independently deployable application that acts as an interface to developers building on top of Open edX REST APIs. The APIs listed in this repository are not a comprehensive list of the Open edX REST API set, just the endpoints likely to be valuable to an external API consumer.

The primary objectives of this service are to:
* provide learners with a richer Open edX experience by creating an ecosystem of third-party apps to enhance the platform
* create a framework for any Open edX deployment to hook into their own API management infrastructure
* enable upstream services to iterate independently by adhering to a “mission control” strategy of having a lightweight central system that routes to service-specific configuration and code

## Getting started
It's important to note that **this repository does not contain any source code** that actually runs an API management service. It contains specifications and scripts that could be used to configure a commercial off-the-shelf API management vendor, or could just be used as a documentation source.

At edx.org, we're using Amazon Web Services' [API Gateway](https://aws.amazon.com/api-gateway) to power an API management service at api.edx.org, and the scripts/specs in this repository allow us to provision AWS API Gateway for our needs. See the note about vendor extensions below if this is of interest.

An example API Manager is defined by an [Open API / Swagger](https://github.com/OAI/OpenAPI-Specification) specification document at [swagger/api.yaml](swagger/api.yaml). You could point the third-party tool [swagger-codegen](https://github.com/swagger-api/swagger-codegen) at this document to generate a lightweight client SDK or stub server in many languages, or just flatten the nested references into a single Swagger document using the swagger (JSON) or swagger-yaml language options (this may be required for use by certain Swagger consumers). Read the swagger-codegen docs for more information.

```sh
swagger-codegen generate -l swagger -i swagger/api.yaml
```

## Vendor extensions

### AWS API Gateway
The flattened Swagger document (see note above) should "just work" when using Amazon's `ImportRestApi` feature. Note that stage variables still need to be defined that are specific to your Open edX installation. To be clear, while you may use AWS API Gateway for your specific Open edX instance, we are intentionally isolating vendor-specific hooks to avoid any lock-ins.

### Other vendor extensions
None yet.

## Capabilities
Below are a set of capabilities that we believe are essential when selecting an API Management vendor (or building your own).

### Routing
> Contain all possible API actions within a single, central access point, to present a unified front to API clients.

One of the core capabilities of an API management service is its presentation layer. API clients should not need to know the underlying deployment details in order to call various endpoints; using an example, if endpoint A is part of edx-platform, while endpoint B belongs to a separate IDA, API clients of A and B shouldn’t have to know that level of implementation detail.

The simplest version of API routing, which is where we've started, is just passing requests through to an underlying origin based on calling to an “upstream” DNS entry. The API service acts as an abstraction layer. More complex routers may include service discovery mechanisms for dynamic request forwarding, but we have no plans on implementing that at this time.

### Audit logging
> Keep track of all calls made against APIs for auditing, monitoring and debugging.

The service should have the ability to record some/all calls made against it. Ideally, these logs can be shipped to a log analysis system in near-real-time so that we can detect API error conditions, monitor request volumes, and understand usage patterns. Here at edx.org, we're using Amazon API Gateway's built-in logging capabilities for now.

### Specification
> Clearly define the API contract in a machine-parseable format so that API clients don’t need to guess about our endpoints.

There are several emerging specification formats for APIs; for now, we’re using Swagger as it has wide adoption and good tooling. With well-placed Swagger documents, clients can easily interact with our APIs as well as generate client SDKs for faster adoption.
Another benefit of a machine-parseable specification is that it can actually be used to configure the API management layer, in the spirit of infrastructure-as-code. This methodology is hugely beneficial at scale, and helps prevent drift between the code and the docs (a real problem for us today). These specifications are also allowed to contain vendor specific overrides (such as AWS “stage variables”).

If done properly, the index file represents a readily available and complete snapshot of the API management layer with environment-level customization. The per-repo specs also enable decoupling of individual service teams from the central API management authority, which should help foster autonomy among those teams and increase velocity / decrease handoffs when changes are needed.

_Note: we made a conscious decision to hand-write the per-repo specifications and index file instead of using tools like django-rest-framework-swagger that can automatically generate specs based on code introspection. These tools may be useful for unit testing an upstream service, but contain far too much internal detail and are not suitable for use by our third-party API clients. If these specifications are intended to define a contract between client and server, then we should consider any auto-generated specs to be the contract between the upstream service and the API manager; meanwhile, we should consider the hand-written specs to be the contract between the API manager and its third-party clients._

### Authentication
> Manage identity information (both application and user).

The general idea is that clients interact with platform APIs using cryptographically-secured tokens that contain identity information. In Open edX, API tokens are generated using the OAuth2 protocol, where each client application has a unique “client secret” that it uses to request new tokens for that application’s users.

We're increasingly using JSON Web Tokens (JWTs) as the format for API tokens. These are generated and signed by the Open edX authentication service and contain basic user information. The API management layer simply needs to verify that the token is legitimate using a public signatory key (or just forward the opaque key to the underlying service to deal with). The key advantage with JWTs is the ability to validate tokens at the API layer instead of needing to reach back to the authentication service, but that’s only valuable if we hit a ceiling on those server-side calls (which should be relatively cacheable).

### Throttling
> Protect upstream services from unnecessarily heavy and expensive client load.

You should consider utilizing any rate limiting / throttling features of the technology selected if available, and plan on enabling this early as it’s much harder to enforce throttling later.

### Developer support
> Give API developers - this service's key user base - a clear understanding of the endpoints available and how to extract maximum value from them.

There are multiple components to developer support, with varying degrees of usefulness and urgency:
- Documentation (initially, can be static; ideally, dynamic based on actual specs)
- Registration (profile, self-service API key requests and generation)
- Support (help tickets, forums, etc)
- Tools (libraries/SDKs, sandboxes)
- Community evangelism (developer conferences and branded hoodies)

Initially, the most critical feature is clear, updated, documentation, so that’s where we have focused our efforts. We're also working on a self-service portal for managing API keys (with a manual approval workflow). The rest of the list above are just suggestions.

### Authorization
> Determine which actions an API client (application) is allowed to access, and the allowed frequency.

Note that API authorization is fundamentally different from user authorization, which we currently enforce at the individual service level. Taking the example of a service for managing and querying a catalog, the division of responsibilities would be: the API Manager will determine if an application is allowed to get any Catalog information or not; the Discovery service will then need to determine if the requesting user is allowed to get information on a specific catalog.

The eventual Open edX plan is to map scopes to routes, and include scope information in the user’s access token. It is not yet clear how we will manage scopes.

### Global deployment and caching
> Be resilient to regional failures, and minimize client latency to the API manager.

The API manager service should be globally deployable and can be opinionated about how it routes requests upstream to avoid global cross-chatter. One approach is to deploy regional management “service clusters” that each point to their region’s upstream services, and then use geographic load-balancing at the DNS layer to route client traffic to the appropriate manager. Of course, we could go the opposite direction and deploy a single logical management cluster that routes to global upstream paths, which is less maintenance work but also less efficient operationally.

Another related performance improvement is API-level caching. Most API management services provide per-region caching.

## Contributing
As with other Open edX codebases, please take a look at [our Contributing docs](https://github.com/edx/edx-platform/blob/master/CONTRIBUTING.rst) if you'd like to help build out this service.
