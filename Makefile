SHELL = /bin/bash

.DEFAULT_GOAL := help
.PHONY: dev test lint start dev_build dev_start dev_test

build:
	docker-compose -f docker-compose-dev.yml build

up: 
	docker-compose -f docker-compose-dev.yml up -d && docker-compose -f docker-compose-dev.yml logs -f --tail=10

update:
	docker-compose -f docker-compose-dev.yml restart bot && make up

stop:
	docker-compose -f docker-compose-dev.yml stop

down:
	docker-compose -f docker-compose-dev.yml down

test:
	docker-compose -f docker-compose-dev.yml run --rm bot pytest

lint:
	black ./bot --check --diff
	pylint ./bot --rcfile .pylintrc
	flake8 ./bot --config .flake8 --count --show-source --statistics
	mypy --config-file mypy.ini ./bot

format:
	black ./bot

help:
	@IFS=$$'\n' ; \
	help_lines=(`fgrep -h "##" $(MAKEFILE_LIST) | fgrep -v fgrep | sed -e 's/\\$$//' | sed -e 's/##/:/'`); \
	printf "%s\n\n" "Usage: make [task]"; \
	printf "%-20s %s\n" "task" "help" ; \
	printf "%-20s %s\n" "------" "----" ; \
	for help_line in $${help_lines[@]}; do \
		IFS=$$':' ; \
		help_split=($$help_line) ; \
		help_command=`echo $${help_split[0]} | sed -e 's/^ *//' -e 's/ *$$//'` ; \
		help_info=`echo $${help_split[2]} | sed -e 's/^ *//' -e 's/ *$$//'` ; \
		printf '\033[36m'; \
		printf "%-20s %s" $$help_command ; \
		printf '\033[0m'; \
		printf "%s\n" $$help_info; \
	done
