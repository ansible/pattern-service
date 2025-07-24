from core.services import pattern_task, pattern_instance_task


def run_pattern_task(pattern_id, task_id):
    pattern_task(pattern_id, task_id)


def run_instance_task(instance_id, task_id):
    pattern_instance_task(instance_id, task_id)
