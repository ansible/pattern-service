from dispatcherd.publish import submit_task
from dispatcherd.publish import task

DISPATCHERD_DEFAULT_CHANNEL = "pattern-service-tasks"


@task(queue=DISPATCHERD_DEFAULT_CHANNEL, decorate=False)
def print_text(text: str) -> None:
    print(text)


def sumbit_hello_world(text: str):  # type: ignore
    job_data, queue = submit_task(
        print_text,
        queue=DISPATCHERD_DEFAULT_CHANNEL,
        args=(text,),
    )
    return job_data["uuid"]
