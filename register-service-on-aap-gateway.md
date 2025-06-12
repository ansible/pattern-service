### How to add and test pattern aap on aap-dev

### Description
This page describes how to add the pattern service application in [aap-dev](https://github.com/ansible/aap-dev/tree/main) as an AAP service registered with the gateway to run local changes and verify that they function as expected within the platform context.


### Steps to test

1. Build and push container image local change into quay.io (run the following  from the pattern source directory)

```shell
# login to quay.io registry
podman login -u="<quay_username>" -p="<quay_registry_secret>" quay.io

# build and push container image to registry
QUAY_NAMESPACE=abikouo1 make push
```

**Once the image is built and pushed, go to https://quay.io/organization/<quay_username>, select the image, and make it public.**

2. Clone the following [repository](https://github.com/abikouo/aap-dev.git) (on branch ``pattern-service``) containing changes to register the pattern service application and ensure the prerequisites defined [here](https://github.com/ansible/aap-dev/blob/main/docs/getting-started/quick-start.md#prerequisites)

```shell
# clone the git repository and move into it
git clone -b pattern-service <repository_url> <destination> && cd <destination>

# ensure prerequisites
make preflight

# update the deployment image with your quay_username used at step 1.
sed -i -e s/'<quay_username>'/abikouo1/ manifests/base/apps/pattern-service/k8s/deployments.yaml 
```

3. Deploy the application using the following command

```shell
cd <destination>

# deploy
AAP_VERSION=2.6 make app

# apply license
AAP_VERSION=2.6 make aap-apply-license
```

4. Test the pattern service application (should be available on http://localhost:44926/pattern/)

```shell
# Retrieve admin password
AAP_VERSION=2.6 make admin-password

# Ping the application
curl -u 'admin:<aap_admin_password>' http://localhost:44926/pattern/
```