from __future__ import annotations

from fastapi import APIRouter

from noteclaw_backend.api.routes import chat, generate, harness, ingest, knowledge, nanobot, search, tasks


api_router = APIRouter()
api_router.include_router(ingest.router, prefix="/ingest", tags=["ingest"])
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["knowledge"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(generate.router, prefix="/generate", tags=["generate"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(harness.router, prefix="/harness", tags=["harness"])
api_router.include_router(nanobot.router, prefix="/nanobot", tags=["nanobot"])
