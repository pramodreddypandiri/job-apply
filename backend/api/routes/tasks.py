"""Task status routes — Celery task polling for frontend."""

from fastapi import APIRouter, Depends
from backend.api.middleware.auth import get_current_user
from backend.tasks.celery_app import celery_app

router = APIRouter()


@router.get("/{task_id}")
async def get_task_status(task_id: str, user: dict = Depends(get_current_user)):
    """Returns Celery task status for frontend polling."""
    result = celery_app.AsyncResult(task_id)

    response = {
        "task_id": task_id,
        "status": result.status,
    }

    if result.status == "SUCCESS":
        response["result"] = result.result
    elif result.status == "FAILURE":
        response["error"] = str(result.result)
    elif result.status == "STARTED":
        response["progress"] = getattr(result, "info", {}).get("progress", 0) if result.info else 0

    return response
