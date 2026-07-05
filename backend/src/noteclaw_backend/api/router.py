from __future__ import annotations

from fastapi import APIRouter

from noteclaw_backend.api.routes import (
    agents,
    chat,
    generate,
    harness,
    ingest,
    knowledge,
    nanobot,
    review,
    search,
    tasks,
    timeline,
)


api_router = APIRouter()
api_router.include_router(ingest.router, prefix="/ingest", tags=["ingest"])
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["knowledge"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(generate.router, prefix="/generate", tags=["generate"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(timeline.router, prefix="/timeline", tags=["timeline"])
api_router.include_router(harness.router, prefix="/harness", tags=["harness"])
api_router.include_router(nanobot.router, prefix="/nanobot", tags=["nanobot"])
api_router.include_router(agents.router, prefix="/agents", tags=["agents"])
api_router.include_router(review.router, prefix="/review", tags=["review"])
