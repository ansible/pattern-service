---
title: Ansible Patterns Specification
author: Ansible Cloud Content team
version: v25.6.1
---

# Ansible Pattern Specification

## Introduction

This document describes the technical specification for an Ansible pattern, an extension of Collections, which are the standard method for packaging and distributing Ansible content. Patterns are used by Ansible Automation Platform (AAP) to offer users a seamless way to start automating with minimal setup, enhancing productivity and efficiency.

A pattern defines an Ansible automation, such as a playbook, and the resources needed in AAP to run that automation, such as a project, execution environment, job template, and survey. The pattern definition can be consumed by the AAP API to create and configure those resources, allowing pattern catalogs to provide users with a seamless journey from identifying relevant patterns to using them in AAP. 

Patterns are delivered as files within an Ansible collection. This approach ensures seamless integration with the Ansible ecosystem by leveraging the existing collection framework. These patterns are bundled during collection packaging, enabling them to be searchable, downloadable, and publishable alongside roles, modules, and plugins in the future. The `ansible-doc` tool will list these patterns, enabling users to discover and learn about them just like other Ansible components.

## Conventions

This document follows the IETF [RFC2119](https://datatracker.ietf.org/doc/html/rfc2119) definitions of Key words for use in RFCs to Indicate Requirement Levels.

## Support

This pattern specification is supported and maintained by the Ansible Cloud Content team. To submit support or other requests for the specification, please <do whatever the method is for requesting support>.

Individual patterns that implement this specification are the responsibility of the collection maintainers for the collections in which they reside. For support or feature requests for individual patterns, contact their collection owners.

## Pattern Directory Structure

- A pattern **MUST** be contained within a single directory in the `/extensions/patterns/` directory of an Ansible collection.
- An Ansible pattern directory name **MUST** be limited to 64 characters.
- An Ansible collection **MAY** contain zero or more patterns.

## Required Files

### `meta/pattern.json`

The pattern definition meta file is the machine-readable entry point for creating an instance of the pattern in AAP. It defines the resources required to execute the pattern, such as controller projects, job templates, and labels. The pattern definition also includes metadata about the pattern to enable its discovery and use, such as its title, audience, and tags. A [JSON schema](pattern_specification.json) has been published to aid with validation of the pattern definition file.

- A pattern **MUST** include exactly one meta file defining the pattern metadata and AAP resources it requires.
- The pattern definition meta file **MUST** be a valid instance of the [Ansible pattern schema](pattern_specification.json).

### `README.md`

The README file is the human-readable documentation for the pattern. It provides information on what the pattern does, its inputs, its dependencies, and how it can be used.

- A pattern **MUST** include a README file.
- The pattern README file **SHOULD** include all of the following:
  - A description of what the pattern does
  - A list of the AAP resources created by the pattern
  - Documentation on how to use the pattern

### `playbooks/`

Pattern playbook files are included in the `/extensions/patterns/<pattern_name>/playbooks/` directory. 

- A pattern **MUST** contain a `playbooks/` directory.
- The `playbooks/` directory **MUST** contain at least one playbook.
- A pattern **MAY** contain multiple playbooks. 
- If a pattern contains multiple playbooks, it **MUST** define a primary playbook in its setup file.

#### Playbook Requirements

- All required and optional input variables to a pattern playbook **MUST** be defined in a play argument spec following the documented [play argument spec format](https://github.com/sivel/play-argument-spec/blob/main/README.md).
- If a pattern playbook requires any user-provided information other than variables to launch as a job template, such as inventory or credentials, those **MUST** be specified as `fields_required_at_launch` in the relevant `controller_job_templates` section of the pattern definition meta file.

### `execution_environments/`

- A pattern **MAY** contain an `execution_environments/` directory.
- If included, the `execution_environments/` directory **MUST** contain exactly one execution environment definition file following the [documented format](https://ansible.readthedocs.io/projects/builder/en/stable/definition).
- The execution environment definition file **MUST** include all dependencies needed to execute the pattern automation(s), including system, Python, and Ansible collection dependencies.

## Optional Files

### `templates/`

Templates for various types of catalog software in which patterns may be published. A template provides pattern data in the format required for a given catalog, such as Red Hat Developer Hub.

- A pattern **MAY** contain a `templates/` directory to hold templates specific to catalogs that may publish the pattern, such as Red Hat Developer Hub or ServiceNow.
- The `templates/` directory **MAY** contain one or more catalog template files.

## Example Pattern Directory

```txt

/extensions/patterns/
├── network.backup/ # Backup pattern directory
│ ├── setup # Backup pattern definition
│ ├── README.md # Documentation for Backup pattern
│ ├── playbooks/ # Directory containing pattern playbooks
│ │ ├── meta/backup.yaml # Backup playbook arg spec
│ │ ├── backup.yaml # Backup playbook
│ ├── templates/ # Directory containing catalog templates
│ │ ├── rhdh.yaml # Display template for RHDH catalog
├── network.restore/ # Restore pattern directory
│ ├── setup # Restore pattern definition
│ ├── README.md # Documentation for Restore pattern
│ ├── playbooks/ # Directory containing pattern playbooks
│ │ ├── meta/restore.yaml # Restore playbook arg spec
│ │ ├── restore.yaml # Restore playbook
│ ├── templates/ # Directory containing catalog templates
│ │ ├── rhdh.yaml # Display template for RHDH catalog

```

## Other Pattern Requirements

- A pattern **MUST** inherit the version number of the collection that contains it.
- A pattern **MUST** be valid according to the requirements specified in this document, including validation of each file contained in the pattern against its relevant schema.
