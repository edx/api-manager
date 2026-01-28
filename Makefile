SWAGGER_CODEGEN_JAR := https://repo1.maven.org/maven2/io/swagger/swagger-codegen-cli/2.4.13/swagger-codegen-cli-2.4.13.jar
BUILD_OUTPUT_DIR := swagger-build-artifacts
STUB_SERVER_DIR := edx-api-stub-server
VENV := venv
PYTHON_VERSION := 3.11
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

# Detect available Python and OS
PYTHON311 := $(shell command -v python3.11 2> /dev/null)
HAS_APT := $(shell command -v apt-get 2> /dev/null)

help:
	@echo '                                                                                        '
	@echo 'Makefile for api-manager                                                                '
	@echo '                                                                                        '
	@echo 'Usage:                                                                                  '
	@echo '    make venv             Create Python 3.11 virtualenv                                 '
	@echo '    make clean            Delete generated python byte code and testing remnants        '
	@echo '    make requirements     Install requirements for local development                    '
	@echo '    make quality          Run PEP8 and Pylint                                           '
	@echo '    make build            Flatten the swagger docs                                      '
	@echo '    make test             Run all tests                                                 '
	@echo '                                                                                        '

venv:
	@echo "Checking for Python $(PYTHON_VERSION)..."
ifndef PYTHON311
	@echo "Python 3.11 not found, attempting to install..."
ifeq ($(HAS_APT),)
	@echo "ERROR: Python $(PYTHON_VERSION) is not installed and apt-get is not available."
	@echo ""
	@echo "Please install Python $(PYTHON_VERSION) manually:"
	@echo "  macOS (using Homebrew): brew install python@$(PYTHON_VERSION)"
	@echo ""
	@exit 1
endif
	@echo "Installing Python $(PYTHON_VERSION) using apt-get..."
	sudo apt-get update
	sudo apt-get install -y software-properties-common
	sudo add-apt-repository -y ppa:deadsnakes/ppa
	sudo apt-get update
	sudo apt-get install -y python$(PYTHON_VERSION) python$(PYTHON_VERSION)-venv python$(PYTHON_VERSION)-dev
	@echo "Python $(PYTHON_VERSION) installed successfully"
else
	@echo "Found python3.11 at $(PYTHON311)"
endif
	@if [ ! -d "$(VENV)" ]; then \
		echo "Creating virtual environment in $(VENV)"; \
		python3.11 -m venv $(VENV); \
		$(PIP) install --upgrade pip; \
	else \
		echo "Virtual environment $(VENV) already exists, skipping creation"; \
	fi

clean:
	find . -name '*.pyc' -delete
	find . -name '__pycache__' -type d -delete
	rm -rf $(BUILD_OUTPUT_DIR)
	rm -rf $(STUB_SERVER_DIR)
	rm -rf $(VENV)

requirements: venv
	$(PIP) install -r requirements/pip.txt
	$(PIP) install -qr requirements/test.txt --exists-action w

quality: venv requirements
	$(VENV)/bin/pep8 --config=.pep8 scripts/aws
	$(VENV)/bin/pylint --rcfile=.pylintrc scripts/aws

# Download the swagger codegen jar
# TODO: verify via checksum that the file is valid.
codegen.download:
	-curl $(SWAGGER_CODEGEN_JAR) -o swagger-codegen-cli.jar

# Flatten the swagger docs into a build artifact.
# Assumes java 7 is installed.
build: codegen.download
	java -jar swagger-codegen-cli.jar generate -l swagger -i swagger/api.yaml -o $(BUILD_OUTPUT_DIR)

# GoCD agents have a version of Java that is not put into the path for some reason. We need to refer to it directly to get access to it.
build-gocd: codegen.download
	/gocd-jre/bin/java -jar swagger-codegen-cli.jar generate -l swagger -i swagger/api.yaml -o $(BUILD_OUTPUT_DIR)

test_python: clean requirements
	cd scripts/aws && ../../$(PYTHON) -m pytest

# Spin up a stub server and hit it with tests
test_swagger: codegen.download venv requirements
	java -jar swagger-codegen-cli.jar generate -l nodejs-server -i swagger/api.yaml -o $(STUB_SERVER_DIR)
	cd $(STUB_SERVER_DIR) && npm install
	cd $(STUB_SERVER_DIR) && NODE_ENV=development node index.js 2> /dev/null &
	sleep 5
	$(VENV)/bin/pyresttest --url=http://localhost:8080 --test=tests/test_all.yaml
	killall -9 node

test: clean
	make quality
	make test_python
	make test_swagger

# Targets in a Makefile which do not produce an output file with the same name as the target name
.PHONY: help venv requirements clean quality test codegen.download build build-gocd test_python test_swagger upgrade

upgrade: export CUSTOM_COMPILE_COMMAND=make upgrade
upgrade: venv ## update the requirements/*.txt files with the latest packages satisfying requirements/*.in
	$(PIP) install -q -r requirements/pip_tools.txt
	$(VENV)/bin/pip-compile --upgrade --allow-unsafe --rebuild -o requirements/pip.txt requirements/pip.in
	$(VENV)/bin/pip-compile --upgrade -o requirements/pip_tools.txt requirements/pip_tools.in
	$(PIP) install -qr requirements/pip.txt
	$(PIP) install -qr requirements/pip_tools.txt
	$(VENV)/bin/pip-compile --upgrade -o requirements/base.txt requirements/base.in
	$(VENV)/bin/pip-compile --upgrade -o requirements/test.txt requirements/test.in
