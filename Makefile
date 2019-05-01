.PHONY: install
.SILENT:

COMPOSE := docker-compose -f dev.yml

# Variables
PIP := ./env/bin/pip
PYTHON := ./env/bin/python

# CONFIGURATION
env:
	virtualenv -p python3 env --always-copy --no-site-packages
	$(PIP) install pip --upgrade
	$(PIP) install setuptools --upgrade
	$(PIP) install -r requirements.txt
	source env/bin/activate

install:
	$(PIP) install --editable .

start: env install
	@echo "Starting..."
