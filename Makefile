.DEFAULT_GOAL := help

.PHONY: help
help: ## Show this help message
	@grep -hE '^[a-zA-Z0-9._-]+:.*?##' $(MAKEFILE_LIST) | \
	awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-24s\033[0m %s\n", $$1, $$2}' | \
	sort -u


# -------------------------------------
# Container image
# -------------------------------------

CONTAINER_RUNTIME ?= podman
COMPOSE_COMMAND ?= podman compose
IMAGE_NAME ?= pattern-service
IMAGE_TAG ?= latest
QUAY_NAMESPACE ?= ansible
BUILD_ARGS ?= --arch amd64

ensure-namespace:
	@test -n "$$QUAY_NAMESPACE" || (echo "Error: QUAY_NAMESPACE is required to push quay.io" && exit 1)

.PHONY: build
build: ## Build the container image
	@echo "Building container image..."
	$(CONTAINER_RUNTIME) build -t $(IMAGE_NAME):$(IMAGE_TAG) -f tools/podman/Containerfile.dev $(BUILD_ARGS) .

.PHONY: clean
clean: ## Remove container image
	@echo "Cleaning up..."
	$(CONTAINER_RUNTIME) rmi -f $(IMAGE_NAME):$(IMAGE_TAG) || true

.PHONY: push
push: ensure-namespace build ## Tag and push container image to Quay.io
	@echo "Tagging and pushing to quay.io/$(QUAY_NAMESPACE)/$(IMAGE_NAME):$(IMAGE_TAG)..."
	$(CONTAINER_RUNTIME) tag $(IMAGE_NAME):$(IMAGE_TAG) quay.io/$(QUAY_NAMESPACE)/$(IMAGE_NAME):$(IMAGE_TAG)
	$(CONTAINER_RUNTIME) push quay.io/$(QUAY_NAMESPACE)/$(IMAGE_NAME):$(IMAGE_TAG)

#--------------------------------------
# Compose
# -------------------------------------
.PHONY: compose-build
compose-build: ## Build the containers images for the services
	$(COMPOSE_COMMAND) -f tools/podman/compose.yaml $(COMPOSE_OPTS) build

.PHONY: compose-up ## Build and start the containers for the services
compose-up:
	$(COMPOSE_COMMAND) -f tools/podman/compose.yaml $(COMPOSE_OPTS) up $(COMPOSE_UP_OPTS) --remove-orphans

.PHONY: compose-down
compose-down: ## Stop containers and remove containers, network, images and volumes created by compose-up
	$(COMPOSE_COMMAND) -f tools/podman/compose.yaml $(COMPOSE_OPTS) down --remove-orphans --rmi

.PHONY: compose-restart
compose-restart: compose-down compose-up ## Stop and remove existing infrastructure and start a new one

# -------------------------------------
# Dependencies
# -------------------------------------

.PHONY: requirements
requirements: ## Generate requirements.txt files from pyproject.toml
	pip-compile -o requirements/requirements.txt pyproject.toml
	pip-compile --extra dev --extra test -o requirements/requirements-dev.txt pyproject.toml
	pip-compile --extra test -o requirements/requirements-test.txt pyproject.toml

# -------------------------------------
# Test
# -------------------------------------

.PHONY: test
test: ## Run tests with a postgres database using docker-compose
	$(COMPOSE_COMMAND) -f tools/podman/compose-test.yaml $(COMPOSE_OPTS) up -d
	-rm coverage.xml
	-tox -e test
	$(COMPOSE_COMMAND) -f tools/podman/compose-test.yaml $(COMPOSE_OPTS) down

# -------------------------------------
# Docs
# -------------------------------------

.PHONY: generate-api-spec
generate-api-spec: ## Generate an OpenAPI specification
	python manage.py spectacular --validate --fail-on-warn --format openapi-json --file specifications/openapi.json
