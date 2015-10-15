all: schema.json

schema.json:
	prmd combine --meta schema/meta.json schema/voters.json | prmd verify > schema.json

test:
	python -m unittest discover --pattern='test*.py'

jenkins_ci:
***REMOVED***
	rbenv rehash
	DEBUG=1 bli test
