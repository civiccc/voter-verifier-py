all: schema.json

schema.json:
	prmd combine --meta schema/meta.json schema/voters.json | prmd verify > schema.json

test:
	python -m unittest discover --pattern='test*.py'

bli:
	gem install docker-api --version=1.28.0 --no-document
***REMOVED***

jenkins_ci: bli
	DEBUG=1 bli test

jenkins_build: bli
	DEBUG=1 bli build
