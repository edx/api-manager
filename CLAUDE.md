# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains specifications and deployment scripts for managing Open edX REST API routing through an API management layer. **This repository does not contain source code for running an API management service** - it contains Swagger/OpenAPI specifications and AWS API Gateway deployment scripts.

The primary purpose is to:
- Define a unified API interface for Open edX REST endpoints
- Provide deployment automation for AWS API Gateway
- Enable routing to various Open edX services (edx-platform, IDAs) through a single access point

## Development Commands

### Setup

This project requires Python 3.11. The Makefile will automatically:
1. Check if Python 3.11 is installed
2. On Ubuntu/Debian systems with apt-get: automatically install Python 3.11 via deadsnakes PPA (requires sudo)
3. On other systems: provide installation instructions

```bash
make venv            # Create Python 3.11 virtualenv (auto-created by other targets)
make requirements    # Install Python dependencies for local development
```

**Note**: On Ubuntu, the first run will install Python 3.11, python3.11-venv, and python3.11-dev packages via apt-get.

### Testing
```bash
make test           # Run all tests (quality, Python tests, and Swagger tests)
make test_python    # Run Python tests only
make test_swagger   # Spin up stub server and run integration tests
```

### Quality Checks
```bash
make quality        # Run PEP8 and Pylint on scripts/aws directory
```

### Building Swagger Documentation
```bash
make build          # Flatten Swagger docs into build artifacts
                    # Requires Java 7+ installed
                    # Downloads swagger-codegen-cli.jar and generates flattened docs
```

### Dependency Management
```bash
make upgrade        # Update all requirements/*.txt files with latest packages
```

### Cleanup
```bash
make clean          # Remove Python bytecode and build artifacts
```

## Architecture

### Swagger Specifications

The API definitions use nested Swagger 2.0 specifications with remote references:

- **`swagger/api.yaml`**: Main specification that defines the complete Open edX public API surface
- **`swagger/index.yaml`**: Index endpoint specification
- **`swagger/heartbeat.yaml`**: Health check endpoint
- **`swagger/oauth.yaml`**: OAuth2 token endpoint

The main `api.yaml` uses `$ref` to pull in both local files and remote specifications from upstream services (e.g., course-discovery, edx-enterprise). This allows service teams to maintain their own API specs while the api-manager composes them into a unified interface.

### AWS Deployment Scripts

Located in `scripts/aws/`, these Python scripts manage AWS API Gateway deployments using a ring deployment strategy:

1. **`bootstrap.py`**: Creates a new API Gateway RestApi and deploys a hello-world bootstrap stage
2. **`deploy.py`**: Uploads flattened Swagger to API Gateway in the next stage of the ring rotation
3. **`flip.py`**: Updates the custom domain to point to a specific stage (activation/rollback)
4. **`monitor.py`**: Monitoring utilities for API Gateway instances
5. **`common/deploy.py`**: Shared deployment logic (stage rotation, API updates, throttling configuration)

#### Deployment Flow

1. Bootstrap: Create initial API Gateway with custom domain
2. Build: Generate flattened Swagger JSON using swagger-codegen
3. Deploy: Upload to next stage in ring (e.g., red → black → red)
4. Flip: Point domain to new stage or rollback to previous

#### Ring Deployment Strategy

The deployment scripts use ordered stages (e.g., "red" and "black") to enable zero-downtime deployments. The live stage serves traffic while the next stage is updated, then traffic is flipped to the new stage.

### Test Structure

- **`scripts/aws/tests/`**: Unit tests for deployment scripts (bootstrap, deploy, flip)
- **`tests/`**: Integration tests that validate Swagger specifications against a stub server

## AWS Configuration

When working with AWS deployment scripts, ensure these environment variables are set:
- `AWS_REGION`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`

## Key Files

- **`Makefile`**: Build, test, and quality commands
- **`swagger/api.yaml`**: Main API specification with nested references
- **`scripts/aws/bootstrap.json`**: Minimal hello-world API for bootstrap stage
- **`.pep8`** and **`.pylintrc`**: Code quality configuration

## Important Notes

- Java 7+ is required for building Swagger documentation
- The repository uses pip-tools for dependency management (requirements/*.in → requirements/*.txt)
- AWS API Gateway is the reference implementation, but the specs are vendor-agnostic
- Stage variables in API Gateway must be configured for your specific Open edX installation
