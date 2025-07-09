.PHONY: build clean push compose-up compose-down compose-clean

# Image name and tag
CONTAINER_RUNTIME ?= podman
IMAGE_NAME ?= ansible-pattern-service
IMAGE_TAG ?= latest
COMPOSE_UP_OPTS ?=
COMPOSE_OPTS ?=


## docker compose targets
compose-build:
	$(CONTAINER_RUNTIME) compose -f tools/docker/docker-compose.yaml $(COMPOSE_OPTS) build

compose-up:
	$(CONTAINER_RUNTIME) compose -f tools/docker/docker-compose.yaml $(COMPOSE_OPTS) up $(COMPOSE_UP_OPTS) --remove-orphans

compose-down:
	$(CONTAINER_RUNTIME) compose -f tools/docker/docker-compose.yaml $(COMPOSE_OPTS) down --remove-orphans

compose-clean:
	$(CONTAINER_RUNTIME) compose -f tools/docker/docker-compose.yaml rm -sf
	docker rmi --force localhost/ansible-pattern-service-api localhost/ansible-pattern-service-worker
	docker volume rm -f postgres_data

compose-restart: compose-down compose-clean compose-up

## docker compose targets for macOS
compose-mac-build:
	$(CONTAINER_RUNTIME) compose -f tools/docker/docker-compose-mac.yaml $(COMPOSE_OPTS) build

compose-mac-up:
	$(CONTAINER_RUNTIME) compose -f tools/docker/docker-compose-mac.yaml $(COMPOSE_OPTS) up $(COMPOSE_UP_OPTS) --remove-orphans

compose-mac-down:
	$(CONTAINER_RUNTIME) compose -f tools/docker/docker-compose-mac.yaml $(COMPOSE_OPTS) down --remove-orphans

compose-mac-clean:
	$(CONTAINER_RUNTIME) compose -f tools/docker/docker-compose-mac.yaml rm -sf
	docker rmi --force localhost/ansible-pattern-service-api localhost/ansible-pattern-service-worker
	docker volume rm -f postgres_data

compose-mac-restart: compose-mac-down compose-mac-clean compose-mac-up


# Build the Docker image
build_amd64:
	@echo "Building container image..."
	$(CONTAINER_RUNTIME) build -t $(IMAGE_NAME):$(IMAGE_TAG) --target aap-dev-image -f tools/docker/Dockerfile --arch amd64 .

build:
	@echo "Building container image..."
	$(CONTAINER_RUNTIME) build -t $(IMAGE_NAME):$(IMAGE_TAG) --target aap-dev-image -f tools/docker/Dockerfile .

# Clean up
clean:
	@echo "Cleaning up..."
	$(CONTAINER_RUNTIME) rmi -f $(IMAGE_NAME):$(IMAGE_TAG) || true

# Tag and push to Quay.io
push: ensure-namespace build
	@echo "Tagging and pushing to registry..."
	$(CONTAINER_RUNTIME) tag $(IMAGE_NAME):$(IMAGE_TAG) quay.io/$(QUAY_NAMESPACE)/$(IMAGE_NAME):$(IMAGE_TAG)
	$(CONTAINER_RUNTIME) push quay.io/$(QUAY_NAMESPACE)/$(IMAGE_NAME):$(IMAGE_TAG)

ensure-namespace:
ifndef QUAY_NAMESPACE
	$(error QUAY_NAMESPACE is required to push quay.io)
endif

