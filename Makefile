***REMOVED***
NAME = verifier
VERSION = $(shell git rev-parse HEAD)

.PHONY: schema.json

all: build

deploy: build
	@while [ -z "$$DEPLOY_CONFIRM" ]; do \
		read -r -p "Deploy $(REGISTRY)/$(NAME):$(VERSION) [y/N]?: " DEPLOY_CONFIRM; \
	done && \
	( \
		if [ "x$$DEPLOY_CONFIRM" = "xy" ]; then \
			docker push $(REGISTRY)/$(NAME); \
			./deploy $(REGISTRY)/$(NAME):$(VERSION); \
		fi; \
	)

# To prevent dirty work-trees from being inadvertantly deployed, use `git
# archive HEAD` to create a local temporary build directory and use that as
# the source of the docker build.
#
# This has an added benefit of making good use of Docker's ADD cache so that
# if the same SHA is built multiple times it will prevent building a
# different image with the same name.
build:
	(rm -rf /tmp/verifier-build 2>/dev/null || true) && \
	git archive --prefix verifier-build/ HEAD | tar xf - -C /tmp && \
	cd /tmp/verifier-build && \
	echo $(VERSION) > REVISION && \
	docker build -t $(REGISTRY)/$(NAME):$(VERSION) .

schema.json:
	prmd combine --meta schema/meta.json schema/voters.json | prmd verify > schema.json
