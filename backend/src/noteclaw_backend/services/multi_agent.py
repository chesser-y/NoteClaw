from __future__ import annotations

from datetime import date
from typing import Any

from noteclaw_backend.domain.enums import (
    AgentRole,
    TaskStatus,
    TaskType,
    TimelineItemStatus,
    TimelineKind,
    WorkItemStatus,
)
from noteclaw_backend.schemas.agents import (
    AgentReview,
    AgentStep,
    AgentWorkflowRequest,
    AgentWorkflowResponse,
)
from noteclaw_backend.schemas.nanobot import NanobotResearchRequest, NanobotResearchResponse
from noteclaw_backend.schemas.tasks import TaskWorkItemUpdate
from noteclaw_backend.schemas.timeline import TimelineItemCreate
from noteclaw_backend.services.nanobot_research import nanobot_research_service
from noteclaw_backend.services.providers import get_llm_provider
from noteclaw_backend.services.task_service import task_service
from noteclaw_backend.services.timeline_service import timeline_service
from noteclaw_backend.settings import get_settings
from noteclaw_backend.schemas.common import new_id


class MultiAgentWorkflowService:
    """Evidence-grounded multi-agent workflow orchestrator for deep knowledge tasks."""

    def __init__(self) -> None:
        self._workflows: dict[str, AgentWorkflowResponse] = {}
        self._workflow_order: list[str] = []

    def get_workflow(self, workflow_id: str) -> AgentWorkflowResponse | None:
        return self._workflows.get(workflow_id)

    def list_workflows(self, *, limit: int = 20, offset: int = 0) -> tuple[list[AgentWorkflowResponse], int]:
        ids = [workflow_id for workflow_id in self._workflow_order if workflow_id in self._workflows]
        workflows = [self._workflows[workflow_id] for workflow_id in ids]
        return workflows[offset : offset + limit], len(workflows)

    async def run(
        self,
        request: AgentWorkflowRequest,
        *,
        progress_cb=None,
    ) -> AgentWorkflowResponse:
        workflow_id = new_id("workflow")
        task_id: str | None = None
        work_item_id: str | None = None
        timeline_item_id: str | None = None
        steps: list[AgentStep] = []

        if request.create_work_item:
            task = task_service.create_task(
                TaskType.AGENT_WORKFLOW,
                "Multi-agent workflow queued",
                work_item_title=request.goal[:120],
                tags=["agent", request.output_format, "workflow"],
                material_count=request.top_k,
                current_stage="Coordinator planning agents",
                requires_confirmation=True,
                metadata={
                    "workflow_id": workflow_id,
                    "use_web": request.use_web,
                    "output_format": request.output_format,
                },
            )
            task_id = task.id
            work_item_id = task_service._task_to_work_item.get(task.id)
            task_service.mark_running(task.id, "Coordinator planning agents")

        async def _emit(role: str, phase: str, **extra):
            if progress_cb is None:
                return
            try:
                await progress_cb(role, phase, extra)
            except Exception:
                pass

        try:
            await _emit("coordinator", "running")
            plan = await self._coordinator_plan(request)
            steps.append(
                AgentStep(
                    index=1,
                    role=AgentRole.COORDINATOR,
                    title="Plan workflow",
                    action="Decompose the user goal into searchable objectives",
                    input_summary=request.goal,
                    output_summary="; ".join(plan[:4]),
                    artifacts={"plan": plan},
                )
            )
            await _emit("coordinator", "done", plan=plan, output="; ".join(plan[:4]))
            self._update_task(task_id, 0.25, "Researcher collecting and structuring evidence")

            await _emit("researcher", "running")
            research = await self._research(request, plan)
            claims = await self._evidence_claims(request.goal, research)
            steps.append(
                AgentStep(
                    index=2,
                    role=AgentRole.RESEARCHER,
                    title="Collect evidence",
                    action="Search local/web sources and extract citation-backed claims",
                    input_summary=f"{len(plan)} objectives · web={request.use_web}",
                    output_summary=(
                        f"{len(research.citations)} local citations · "
                        f"{len(research.web_sources)} web sources · "
                        f"{len(research.evidence_anchors)} anchors · "
                        f"{len(claims)} claims"
                    ),
                    artifacts={"trace": research.trace, "claims": claims},
                )
            )
            await _emit(
                "researcher",
                "done",
                output=(
                    f"{len(research.citations)} citations · "
                    f"{len(research.web_sources)} web · "
                    f"{len(claims)} claims"
                ),
                citations=[c.model_dump(mode="json") for c in research.citations[:6]],
            )
            if work_item_id:
                task_service.update_work_item(
                    work_item_id,
                    TaskWorkItemUpdate(
                        material_count=len(research.citations) + len(research.web_sources),
                        metadata={"web_source_count": len(research.web_sources)},
                    ),
                )
            self._update_task(task_id, 0.58, "Reasoner synthesizing final output")

            await _emit("reasoner", "running")
            synthesis = await self._reason(request.goal, plan, claims, research)
            final_answer = await self._write(request, synthesis, claims, research)
            steps.append(
                AgentStep(
                    index=3,
                    role=AgentRole.REASONER,
                    title="Synthesize answer",
                    action=f"Compare evidence and produce {request.output_format}",
                    input_summary=f"{len(claims)} grounded claims",
                    output_summary=final_answer[:360],
                    artifacts={"output_format": request.output_format, "synthesis": synthesis[:1200]},
                )
            )
            await _emit("reasoner", "done", output=final_answer[:360])
            self._update_task(task_id, 0.86, "Reviewer checking citations and risks")

            await _emit("reviewer", "running")
            review = await self._review(request.goal, final_answer, claims, research)
            steps.append(
                AgentStep(
                    index=4,
                    role=AgentRole.REVIEWER,
                    title="Review result",
                    action="Check evidence coverage, risks, and whether user confirmation is needed",
                    output_summary=f"{review.verdict} · confidence={review.confidence:.2f}",
                    artifacts=review.model_dump(mode="json"),
                )
            )
            await _emit(
                "reviewer",
                "done",
                output=f"{review.verdict} · confidence={review.confidence:.2f}",
                review=review.model_dump(mode="json"),
            )

            if request.create_timeline_item:
                timeline_item = timeline_service.create_item(
                    TimelineItemCreate(
                        kind=TimelineKind.OUTPUT,
                        title=request.goal[:160],
                        lane="Multi-agent workflow",
                        start_date=date.today(),
                        end_date=date.today(),
                        progress=1.0 if review.verdict == "approved" else 0.85,
                        status=(
                            TimelineItemStatus.DONE
                            if review.verdict == "approved"
                            else TimelineItemStatus.MILESTONE
                        ),
                        milestone_date=date.today(),
                        tags=["agent", request.output_format],
                        source_note_ids=[citation.note_id for citation in research.citations[:12]],
                        source_task_ids=[task_id] if task_id else [],
                        current_stage=(
                            "Reviewed · ready"
                            if review.verdict == "approved"
                            else "Needs user review"
                        ),
                        result_url=f"/api/agents/workflows/{workflow_id}",
                        result_label="Open agent workflow",
                        metadata={
                            "workflow_id": workflow_id,
                            "agent_count": len(steps),
                            "web_source_count": len(research.web_sources),
                            "evidence_anchor_count": len(research.evidence_anchors),
                        },
                    )
                )
                timeline_item_id = timeline_item.id

            result_payload = {
                "workflow_id": workflow_id,
                "answer": final_answer,
                "review": review.model_dump(mode="json"),
                "steps": [step.model_dump(mode="json") for step in steps],
            }
            if task_id:
                task_service.mark_succeeded(
                    task_id,
                    message="Multi-agent workflow completed",
                    result=result_payload,
                )
                if work_item_id:
                    task_service.update_work_item(
                        work_item_id,
                        TaskWorkItemUpdate(
                            status=(
                                WorkItemStatus.DONE
                                if review.verdict == "approved" and not review.requires_confirmation
                                else WorkItemStatus.NEED_REVIEW
                            ),
                            current_stage=(
                                "Reviewed · ready"
                                if review.verdict == "approved"
                                else "Reviewer flagged items · waiting for user"
                            ),
                            result_url=f"/api/agents/workflows/{workflow_id}",
                            result_label="Open agent workflow",
                            metadata={"timeline_item_id": timeline_item_id} if timeline_item_id else {},
                        ),
                    )

            response = AgentWorkflowResponse(
                workflow_id=workflow_id,
                task_id=task_id,
                work_item_id=work_item_id,
                timeline_item_id=timeline_item_id,
                goal=request.goal,
                final_answer=final_answer,
                steps=steps,
                plan=plan,
                citations=research.citations,
                evidence_anchors=research.evidence_anchors,
                web_sources=research.web_sources,
                review=review,
                trace={
                    "strategy": "evidence_grounded_multi_agent_workflow",
                    "roles": [role.value for role in AgentRole],
                    "use_web": request.use_web,
                    "model": get_settings().llm_model or "fallback-local",
                    "task_id": task_id,
                    "work_item_id": work_item_id,
                    "timeline_item_id": timeline_item_id,
                },
            )
            self._store_response(response)
            return response
        except Exception as exc:
            if task_id:
                task_service.mark_failed(task_id, str(exc))
            raise

    async def _coordinator_plan(self, request: AgentWorkflowRequest) -> list[str]:
        data = await get_llm_provider().complete_json(
            [
                {
                    "role": "system",
                    "content": (
                        "You are the Coordinator Agent for NoteClaw. "
                        "Return JSON only: {\"steps\": [\"focused objective\", ...]}. "
                        "Steps should be searchable in a knowledge base or on the web."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Max steps: {request.max_steps}\n"
                        f"Output format: {request.output_format}\n"
                        f"Goal: {request.goal}"
                    ),
                },
            ],
            schema={"type": "object", "properties": {"steps": {"type": "array"}}},
        )
        raw_steps = data.get("steps") or data.get("sub_questions") or []
        steps = self._clean_steps([str(step) for step in raw_steps], request.max_steps)
        return steps or self._fallback_plan(request.goal, request.max_steps)

    async def _research(self, request: AgentWorkflowRequest, plan: list[str]) -> NanobotResearchResponse:
        question = request.goal
        if plan:
            question = request.goal + "\nResearch objectives:\n" + "\n".join(f"- {step}" for step in plan)
        return await nanobot_research_service.research(
            NanobotResearchRequest(
                question=question,
                retrieval_mode=request.retrieval_mode,
                scope=request.scope,
                top_k=request.top_k,
                max_steps=request.max_steps,
                max_sub_questions=request.max_steps,
                use_web=request.use_web,
                web_results=request.web_results,
                fetch_web_pages=request.fetch_web_pages,
                save_web_evidence=False,
            )
        )

    async def _evidence_claims(
        self,
        goal: str,
        research: NanobotResearchResponse,
    ) -> list[dict[str, Any]]:
        anchor_text = "\n".join(
            f"- {anchor.id} {anchor.source_type} {anchor.title}: {anchor.snippet}"
            for anchor in research.evidence_anchors[:18]
        )
        if not anchor_text:
            return []
        try:
            data = await get_llm_provider().complete_json(
                [
                    {
                        "role": "system",
                        "content": (
                            "You are NoteClaw Researcher Agent. Extract citation-backed claims. "
                            "Return JSON only: {\"claims\": [{\"claim\": str, \"evidence_ids\": [str], \"confidence\": number}]}"
                        ),
                    },
                    {"role": "user", "content": f"Goal: {goal}\nEvidence anchors:\n{anchor_text}"},
                ],
                schema={"type": "object", "properties": {"claims": {"type": "array"}}},
            )
            claims = data.get("claims") if isinstance(data, dict) else None
            if isinstance(claims, list):
                return [claim for claim in claims[:12] if isinstance(claim, dict)]
        except Exception:
            pass
        return [
            {
                "claim": anchor.snippet,
                "evidence_ids": [anchor.id],
                "confidence": anchor.score if anchor.score is not None else 0.5,
            }
            for anchor in research.evidence_anchors[:8]
        ]

    async def _reason(
        self,
        goal: str,
        plan: list[str],
        claims: list[dict[str, Any]],
        research: NanobotResearchResponse,
    ) -> str:
        claims_text = "\n".join(
            f"- {claim.get('claim')} (evidence: {', '.join(map(str, claim.get('evidence_ids', [])))})"
            for claim in claims[:12]
        )
        messages = [
            {
                "role": "system",
                "content": (
                    "You are NoteClaw Reasoner Agent. Synthesize across claims and sources. "
                    "Use evidence ids and citations; note uncertainty instead of overclaiming."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Goal:\n"
                    + goal
                    + "\n\nPlan:\n"
                    + "\n".join(f"- {step}" for step in plan)
                    + "\n\nClaims:\n"
                    + (claims_text or "No structured claims extracted.")
                    + "\n\nResearch synthesis:\n"
                    + research.answer[:6000]
                ),
            },
        ]
        return (await get_llm_provider().complete_text(messages, max_tokens=1400)).strip()

    async def _write(
        self,
        request: AgentWorkflowRequest,
        synthesis: str,
        claims: list[dict[str, Any]],
        research: NanobotResearchResponse,
    ) -> str:
        if request.output_format == "answer":
            return synthesis
        claims_text = "\n".join(f"- {claim.get('claim')}" for claim in claims[:10])
        messages = [
            {
                "role": "system",
                "content": (
                    "You are NoteClaw Reasoner Agent. Produce the requested output format from grounded synthesis. "
                    "Keep citations/evidence references when relevant."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Output format: {request.output_format}\n"
                    f"Goal: {request.goal}\n\n"
                    f"Synthesis:\n{synthesis}\n\n"
                    f"Grounded claims:\n{claims_text}\n\n"
                    f"Citation count: {len(research.citations)}"
                ),
            },
        ]
        return (await get_llm_provider().complete_text(messages, max_tokens=1800)).strip()

    async def _review(
        self,
        goal: str,
        final_answer: str,
        claims: list[dict[str, Any]],
        research: NanobotResearchResponse,
    ) -> AgentReview:
        try:
            data = await get_llm_provider().complete_json(
                [
                    {
                        "role": "system",
                        "content": (
                            "You are NoteClaw Reviewer Agent. Check evidence sufficiency and risks. "
                            "Return JSON only with verdict approved|need_review, confidence 0-1, risks, suggestions."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Goal: {goal}\n"
                            f"Claim count: {len(claims)}\n"
                            f"Citation count: {len(research.citations)}\n"
                            f"Web source count: {len(research.web_sources)}\n"
                            f"Answer:\n{final_answer[:5000]}"
                        ),
                    },
                ],
                schema={"type": "object"},
            )
            verdict = str(data.get("verdict") or "need_review").lower()
            if verdict not in {"approved", "need_review"}:
                verdict = "need_review"
            risks = data.get("risks") if isinstance(data.get("risks"), list) else []
            suggestions = data.get("suggestions") if isinstance(data.get("suggestions"), list) else []
            confidence = float(data.get("confidence") or 0.5)
            return AgentReview(
                verdict=verdict,
                requires_confirmation=verdict != "approved",
                confidence=max(0.0, min(1.0, confidence)),
                risks=[str(risk)[:180] for risk in risks[:6]],
                suggestions=[str(item)[:180] for item in suggestions[:6]],
            )
        except Exception:
            pass
        enough_evidence = len(claims) >= 2 and len(research.citations) >= 2
        return AgentReview(
            verdict="approved" if enough_evidence else "need_review",
            requires_confirmation=not enough_evidence,
            confidence=0.72 if enough_evidence else 0.45,
            risks=[] if enough_evidence else ["Evidence is sparse; user review is recommended."],
            suggestions=[] if enough_evidence else ["Add more documents or enable web research for stronger grounding."],
        )

    def _update_task(self, task_id: str | None, progress: float, message: str) -> None:
        if task_id:
            task_service.update_task(
                task_id,
                status=TaskStatus.RUNNING,
                progress=progress,
                message=message,
            )

    def _clean_steps(self, raw_steps: list[str], limit: int) -> list[str]:
        seen: set[str] = set()
        steps: list[str] = []
        for raw_step in raw_steps:
            step = " ".join(raw_step.split()).strip(" -")
            if len(step) < 4:
                continue
            key = step.lower()
            if key in seen:
                continue
            seen.add(key)
            steps.append(step)
            if len(steps) >= limit:
                break
        return steps

    def _store_response(self, response: AgentWorkflowResponse) -> None:
        self._workflows[response.workflow_id] = response
        self._workflow_order = [response.workflow_id] + [
            workflow_id for workflow_id in self._workflow_order if workflow_id != response.workflow_id
        ]
        self._workflow_order = self._workflow_order[:100]

    def _fallback_plan(self, goal: str, limit: int) -> list[str]:
        base = " ".join(goal.split()).strip()
        return [
            f"Find local knowledge relevant to: {base}",
            f"Extract evidence and citations for: {base}",
            f"Synthesize cross-source reasoning for: {base}",
            f"Review risks and missing evidence for: {base}",
        ][:limit]


multi_agent_workflow_service = MultiAgentWorkflowService()
