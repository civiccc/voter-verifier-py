all: schema.json

schema.json:
	prmd combine --meta schema/meta.json schema/voters.json | prmd verify > schema.json
