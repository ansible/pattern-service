### How to add and test pattern aap on aap-dev

### Description
This page describes how to add the pattern service application in [aap-dev](https://github.com/ansible/aap-dev/tree/main) as an AAP service registered with the gateway to run local changes and verify that they function as expected within the platform context.


### Steps to test

1. Build and push container image local change into quay.io (run the following  from the pattern source directory)

```shell
# login to quay.io registry
podman login -u="<quay_username>" -p="<quay_registry_secret>" quay.io

# build and push container image to registry
QUAY_NAMESPACE=<quay_username> make push
```

**Once the image is built and pushed, go to https://quay.io/organization/<quay_username>, select the image, and make it public.**

2. Follow the steps described [here](https://github.com/ansible/aap-dev/blob/main/docs/how-to-guides/pattern-service.md) to deploy aap-dev with the pattern service.
