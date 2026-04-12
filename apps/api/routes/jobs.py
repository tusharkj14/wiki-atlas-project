"""
Manual trigger for background jobs.

POST /jobs/sync — run a one-shot Redis→PostgreSQL sync.
"""

import logging

from fastapi import APIRouter, BackgroundTasks

from jobs.sync_redis_to_postgres import sync_once

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/sync")
async def trigger_sync(background_tasks: BackgroundTasks):
    """Trigger a Redis→PostgreSQL sync in the background."""
    background_tasks.add_task(sync_once)
    return {"status": "sync started"}
