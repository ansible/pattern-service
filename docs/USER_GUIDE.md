# Pattern Loading Service Workflow

This section walks you through setting up of the complete pattern loading workflow in your AAP environment, including pattern-service, cloud collections, and execution environments (EE).

---

## Prerequisites

* Access to AAP development environment.
* Latest container images for `pattern-service`.
* Required tools installed: `ansible-builder`, `podman`, `make`.
* Admin credentials for PAH (Private Automation Hub).

---

## Steps to Test the Workflow

### 1. Publish the Latest Pattern-Service Container

Publish the latest container image for the `pattern-service` so it can be used in your AAP development environment.

---

### 2. Run AAP Dev

Run your AAP development environment, pointing to the newly published latest `pattern-service` image.
For detailed steps on deploying AAP dev with the pattern service, see the AAP-Dev [How-To Guide](https://github.com/ansible/aap-dev/blob/main/docs/how-to-guides/pattern-service.md).

---

### 3. Apply License and Admin Setup

Run the following commands in your AAP dev environment:

```bash
make aap-apply-license
make aap-admin
```

---

### 4. Build, Tag, and Publish the Execution Environment to Private Automation Hub
The example collection used here is cloud.aws_ops

From the directory containing the EE definition, run the following steps:

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

---

### 5. Configure AAP UI

1. **Collections Hub**:

   * Create a new collection namespace, e.g., `cloud`.
   * Upload the `cloud.aws_ops` collection tarball.
   * Approve the collection from the staging pipeline.

2. **Controller Credentials**:

   * Create a **source control credential** to PAH using the admin username and password. Note the **credential ID**.
   * Create a **registry credential** to PAH using the admin username and password and `localhost:44926` as the authentication URL. Note the **credential ID**.

3. **User and Team Setup**:

   * Create a user and a team to assign the Job Template (JT) execute role. Note their **IDs**.

---

### 6. Run the Pattern Service Locally

Bring up the pattern service using Docker Compose:

```bash
make compose-up
```

---

### 7. Create Pattern and Pattern Instance

1. In the **Pattern Service Browseable API**:

   * Create the **pattern**.
   * Create a **pattern instance**, using the saved IDs and credentials from the previous steps.

#### Example Credentials Payload

```json
{
  "ee": 4,
  "project": 3
}
```

> Note: IDs correspond to resources created in previous steps.

#### Example Executors Payload

```json
{
  "teams": [1],
  "users": [3]
}
```

> Note: IDs correspond to resources created in previous steps.

---
