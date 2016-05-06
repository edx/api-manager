SWAGGER_CODEGEN_JAR := http://repo1.maven.org/maven2/io/swagger/swagger-codegen-cli/2.1.6/swagger-codegen-cli-2.1.6.jar
STUB_SERVER_FOLDER := edx-api-stub-server

help:
	@echo '                                                                                        '
	@echo 'Makefile for api-manager                                                                '
	@echo '                                                                                        '
	@echo 'Usage:                                                                                  '
	@echo '    make clean            Delete generated python byte code and testing remnants        '
	@echo '    make requirements     Install requirements for local development                    '
	@echo '    make quality          Run PEP8 and Pylint                                           '
	@echo '    make build            Flatten the swagger docs and build a stub server              '
	@echo '    make test             Run all tests that do not require a running server            '
	@echo '    make test_swagger     Run tests for the API contracts against a running stub server '
	@echo '    make run              Run a stub server that serves built swagger docs              '
	@echo '                                                                                        '

clean:
	@find . -name '*.pyc .cache __pycache__' -delete

requirements:
	@pip install -qr requirements/test.txt --exists-action w

quality:
	@pep8 --config=.pep8 scripts/aws
	@pylint --rcfile=.pylintrc scripts/aws

clean.stub:
	@rm -rf $(STUB_SERVER_FOLDER)

# Download the swagger codegen jar if you don't already have it.
# TODO: verify via checksum that the file is valid.
codegen.download:
	-@wget $(SWAGGER_CODEGEN_JAR) -O swagger-codegen-cli.jar --no-clobber

# Flatten the swagger docs and generate a stub server to serve them.
# Assumes java 7 is installed.
build: clean.stub codegen.download
	@java -jar swagger-codegen-cli.jar generate -l nodejs-server -i swagger/api.yaml -o $(STUB_SERVER_FOLDER)

test_python: clean requirements
	@cd scripts/aws && python -m pytest

test: clean quality test_python

# Assumes you have a stub server that is up and running.
test_swagger:
	pyresttest --url=http://localhost:8080 --test=tests/test_all.yaml

run: build
	cd $(STUB_SERVER_FOLDER) && npm install && NODE_ENV=development node index.js

# Targets in a Makefile which do not produce an output file with the same name as the target name
.PHONY: help requirements clean quality test
