from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from noteclaw_backend.schemas.agents import (
    AgentWorkflowListResponse,
    AgentWorkflowRequest,
    AgentWorkflowResponse,
)
from noteclaw_backend.services.multi_agent import multi_agent_workflow_service


router = APIRouter()


@router.post("/workflows", response_model=AgentWorkflowResponse)
async def run_agent_workflow(request: AgentWorkflowRequest) -> AgentWorkflowResponse:
    return await multi_agent_workflow_service.run(request)


@router.get("/workflows", response_model=AgentWorkflowListResponse)
async def list_agent_workflows(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> AgentWorkflowListResponse:
    items, total = multi_agent_workflow_service.list_workflows(limit=limit, offset=offset)
    return AgentWorkflowListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/workflows/{workflow_id}", response_model=AgentWorkflowResponse)
async def get_agent_workflow(workflow_id: str) -> AgentWorkflowResponse:
    workflow = multi_agent_workflow_service.get_workflow(workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Agent workflow not found")
    return workflow
