SWAGGER_CODEGEN_JAR := https://repo1.maven.org/maven2/io/swagger/swagger-codegen-cli/2.4.13/swagger-codegen-cli-2.4.13.jar
BUILD_OUTPUT_DIR := swagger-build-artifacts
STUB_SERVER_DIR := edx-api-stub-server

help:
	@echo '                                                                                        '
	@echo 'Makefile for api-manager                                                                '
	@echo '                                                                                        '
	@echo 'Usage:                                                                                  '
	@echo '    make clean            Delete generated python byte code and testing remnants        '
	@echo '    make requirements     Install requirements for local development                    '
	@echo '    make quality          Run PEP8 and Pylint                                           '
	@echo '    make build            Flatten the swagger docs                                      '
	@echo '    make test             Run all tests                                                 '
	@echo '                                                                                        '

clean:
	find . -name '*.pyc' -delete
	find . -name '__pycache__' -type d -delete
	rm -rf $(BUILD_OUTPUT_DIR)
	rm -rf $(STUB_SERVER_DIR)

requirements:
	pip install -qr requirements/test-requirements.txt --exists-action w

quality:
	pep8 --config=.pep8 scripts/aws
	pylint --rcfile=.pylintrc scripts/aws

# Download the swagger codegen jar
# TODO: verify via checksum that the file is valid.
codegen.download:
	-curl $(SWAGGER_CODEGEN_JAR) -o swagger-codegen-cli.jar

# Flatten the swagger docs into a build artifact.
# Assumes java 7 is installed.
build: codegen.download
	java -jar swagger-codegen-cli.jar generate -l swagger -i swagger/api.yaml -o $(BUILD_OUTPUT_DIR)

test_python: clean requirements
	cd scripts/aws && python -m pytest

# Spin up a stub server and hit it with tests
test_swagger: codegen.download
	java -jar swagger-codegen-cli.jar generate -l nodejs-server -i swagger/api.yaml -o $(STUB_SERVER_DIR)
	cd $(STUB_SERVER_DIR) && npm install
	cd $(STUB_SERVER_DIR) && NODE_ENV=development node index.js 2> /dev/null &
	sleep 5
	pyresttest --url=http://localhost:8080 --test=tests/test_all.yaml
	killall -9 node

test: clean
	make quality
	make test_python
	make test_swagger

# Targets in a Makefile which do not produce an output file with the same name as the target name
.PHONY: help requirements clean quality test
