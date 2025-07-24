from core.services import pattern_instance_task
from core.services import pattern_task


def run_pattern_task(pattern_id, task_id):
    pattern_task(pattern_id, task_id)


def run_pattern_instance_task(instance_id, task_id):
    pattern_instance_task(instance_id, task_id)
