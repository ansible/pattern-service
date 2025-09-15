# Pattern Loading Service Workflow

This section walks you through setting up of the complete pattern loading workflow in your AAP environment, including pattern-service, cloud collections, and execution environments (EE).

## Prerequisites

* Access to AAP development environment.
* Latest container images for `pattern-service`.
* Required tools installed: `ansible-builder`, `podman`, `make`.
* Admin credentials for Private Automation Hub (PAH).

## Steps to Test the Workflow

### 1. Publish the Latest Pattern-Service Container

Publish the latest container image for the `pattern-service` so it can be used in your AAP development environment. Following documents can be referred to achieve it
* [Build container image](https://github.com/ansible/pattern-service/blob/main/tools/podman/README.md)
* [Push the image to quay.io](https://github.com/ansible/pattern-service/blob/main/register-service-on-aap-gateway.md)

### 2. Run AAP Dev

Run your AAP development environment, pointing to the newly published latest `pattern-service` image.
For detailed steps on deploying AAP dev with the pattern service, see the AAP-Dev [How-To Guide](https://github.com/ansible/aap-dev/blob/main/docs/how-to-guides/pattern-service.md).

### 3. Apply License and Admin Setup

In a separate terminal window, run the following commands from the top level of your locally-cloned [aap-dev](https://github.com/ansible/aap-dev) repository:

```bash
make aap-apply-license
make aap-admin
```

### 4. Build, Tag, and Publish the Execution Environment (EE) to Private Automation Hub (PAH)
The example collection used is [cloud.aws_ops](https://github.com/redhat-cop/cloud.aws_ops) and the pattern is [configure_ec2](https://github.com/redhat-cop/cloud.aws_ops/tree/main/extensions/patterns/configure_ec2).

From the directory containing the [EE definition](https://github.com/redhat-cop/cloud.aws_ops/blob/main/extensions/patterns/configure_ec2/exec_env/execution-environment.yml), run the following steps:

1. Create the execution environment:

```bash
ansible-builder create
```

2. Build the container image for AMD64 architecture:

```bash
podman build --arch amd64 -f context/Containerfile --no-cache -t localhost:44926/cloud/aws_ops-ee:latest context
```

3. Log in to the local registry:

```bash
podman login localhost:44926 --tls-verify=false
```

4. Push the EE to the local registry:

```bash
podman push localhost:44926/cloud/aws_ops-ee:latest --tls-verify=false
```

### 5. Configure AAP UI

1. **Collections Hub**:

   * Create a new collection namespace, e.g., `cloud` and upload the `cloud.aws_ops` collection tarball created in the above step into Automation Hub.
   * Approve the collection from the staging pipeline (Contact [Partner-Engineering](https://source.redhat.com/groups/public/ansible_engineering/wiki/partner_engineering_team) for approval).
   * For detailed steps, refer [Managing collections in automation hub](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.5/html/managing_automation_content/managing-collections-hub).

2. **Controller Credentials**:

   * Create a [**source control credential**](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.5/html/using_automation_execution/controller-credentials#ref-controller-credential-source-control) to PAH using the admin username and password. Note the **credential ID**.
   * Create a [**registry credential**](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/latest/html/using_automation_execution/controller-credentials#ref-controller-credential-container-registry) to PAH using the admin username and password and `localhost:44926` as the authentication URL. Note the **credential ID**.

#### Example Credentials Payload

```json
{
  "ee": 4,
  "project": 3
}
```

> Note: IDs correspond to resources created in this step.

3. **User and Team Setup**:

   * Create a user and a team to assign the Job Template (JT) execute role. Note their **IDs**.

#### Example Executors Payload

```json
{
  "teams": [1],
  "users": [3]
}
```

> Note: IDs correspond to resources created in this step.

### 6. Run the Pattern Service Locally

Bring up the pattern service using Docker Compose:

```bash
make compose-up
```

### 7. Create Pattern and Pattern Instance

1. In the **Pattern Service Browseable API** (e.g. `http://localhost:8000/api/pattern-service/v1/patterns`):

   * Create the **pattern**.
   * Create a **pattern instance**, using the saved IDs and credentials from the previous steps.
