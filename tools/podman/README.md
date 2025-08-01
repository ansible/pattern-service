# Container Compose for Development

## Getting started

### Clone the repo

If you have not already done so, you will need to clone, or create a local copy, of the [pattern-service repo](https://github.com/ansible/pattern-service).
Once you have a local copy, run the commands in the following sections from the root of the project tree.

### Prerequisites

- [Podman](https://podman.io/docs/installation) on the host where the application will be deployed.
- [Podman Compose](https://podman-desktop.io/docs/compose/setting-up-compose) or [python installation](https://pypi.org/project/podman-compose/).


## Starting the Development Environment

### Build the Image

Run the following to build the image:

```bash
$ make compose-build
```

> The image will need to be rebuilt if there are any changes to `tools/podman/compose.yaml`.

Once the build completes, you will have a `ansible/awx_devel` image in your local image cache. Use the `podman images` command to view it, as follows:

```bash
(host)$ podman images

REPOSITORY                                       TAG       IMAGE ID       CREATED         SIZE
localhost/pattern-service-api                    latest    fcf098365c6a   2 minutes ago   739MB
localhost/pattern-service-worker                 latest    20e63a95799b   2 minutes ago   739MB
quay.io/sclorg/postgresql-15-c9s                 latest    8e0c195e634c   2 minutes ago   372MB
```

### Run the pattern-service application

##### Start the containers

Run the pattern-service-api, pattern-service-worker, and postgres containers. This utilizes the image built in the previous step, and will automatically start all required services and dependent containers. Once the containers launch, you'll be able to watch log messages and events in real time.

```bash
$ make compose-up
```

> For running podman-compose in detached mode, start the containers using the following command: `$ make compose-up COMPOSE_UP_OPTS=-d`

You can test the application from the url `http://localhost:8000/api/pattern-service/v1/test/`
