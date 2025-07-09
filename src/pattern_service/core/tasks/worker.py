#  Copyright 2023 Red Hat, Inc.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import logging
import os
import time

from dispatcherd.publish import submit_task  # type: ignore
from django.db import transaction

from pattern_service.core.models import ResourceState

logger = logging.getLogger(__name__)

PS_DEBUG_QUEUE_NAME = "ps_resource_state"


def create_resource_state(resource_id: str) -> str:
    job_data, queue = submit_task(
        _create_resource,
        queue=PS_DEBUG_QUEUE_NAME,
        args=(resource_id,),
    )
    return job_data["uuid"]


@transaction.atomic
def _create_resource(resource_id):
    logger.info(f"Task started: create resource for id={resource_id}")

    resource = ResourceState.objects.get(pk=resource_id)
    resource.state = ResourceState.StateOptions.RUNNING
    resource.save(update_fields=["state"])

    logger.info(
        "This is the place where the functional logic should take place."
    )
    sleep_time = 10
    time.sleep(sleep_time)
    resource.state = ResourceState.StateOptions.COMPLETED
    resource.save(update_fields=["state"])
