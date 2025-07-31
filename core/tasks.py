from core.services import pattern_task


def run_pattern_task(pattern_id: int, task_id: int) -> None:
    pattern_task(pattern_id, task_id)
