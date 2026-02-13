import uuid
import threading
from app.models.pipeline_jobs import (
    create_job,
    update_job
)
from app.services.pipeline_service import run_pipeline

def start_pipeline_job():
    job_id = str(uuid.uuid4())

    create_job(job_id)

    t = threading.Thread(
        target=_run_pipeline_job,
        args=(job_id,),
        daemon=True
    )
    t.start()

    return job_id


def _run_pipeline_job(job_id: str):
    update_job(job_id, "running")

    try:
        result = run_pipeline()
        update_job(job_id, "completed", result=result)
    except Exception as e:
        update_job(job_id, "failed", error=str(e))