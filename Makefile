.PHONY: build build-multi run test clean install-deps lint push-quay login-quay push-quay-multi

# Image name and tag
CONTAINER_RUNTIME ?= podman
IMAGE_NAME ?= ansible-pattern-service
IMAGE_TAG ?= latest

# Build the Docker image
build:
	@echo "Building container image..."
	$(CONTAINER_RUNTIME) build -t $(IMAGE_NAME):$(IMAGE_TAG) -f Dockerfile.dev --arch amd64 .

ensure-namespace:
ifndef QUAY_NAMESPACE
$(error QUAY_NAMESPACE is required to push quay.io)
endif

# Clean up
clean:
	@echo "Cleaning up..."
	$(CONTAINER_RUNTIME) rmi -f $(IMAGE_NAME):$(IMAGE_TAG) || true

# Tag and push to Quay.io
push: ensure-namespace build
	@echo "Tagging and pushing to registry..."
	$(CONTAINER_RUNTIME) tag $(IMAGE_NAME):$(IMAGE_TAG) quay.io/$(QUAY_NAMESPACE)/$(IMAGE_NAME):$(IMAGE_TAG)
	$(CONTAINER_RUNTIME) push quay.io/$(QUAY_NAMESPACE)/$(IMAGE_NAME):$(IMAGE_TAG)
