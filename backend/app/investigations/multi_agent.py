import asyncio
import logging
import time
from typing import Any, AsyncGenerator
from openai import AsyncOpenAI

from app.core.config import settings
from app.investigations.agent_schemas import (
    TechnicalRCAResult,
    BusinessImpactResult,
    RemediationPlanResult,
    UnifiedDiagnosisOutput,
    CustomerImpactTier,
    EvidenceQuote,
    OffendingCommitInfo,
)

logger = logging.getLogger(__name__)


class MultiAgentOrchestrator:
    """
    DAG-Orchestrated Multi-Agent Analysis Engine.
    Executes specialized agents (RCA, Business Impact, Remediation) in parallel / DAG dependency order
    using Pydantic structured outputs.
    """

    def __init__(self):
        import sys
        if "pytest" in sys.modules or settings.ENVIRONMENT == "testing" or not settings.OPENAI_API_KEY:
            self.client = None
        else:
            self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY, timeout=5.0)

    async def run_dag_analysis(
        self,
        investigation_title: str,
        investigation_description: str,
        severity: str,
        evidence_items: list[dict[str, Any]],
        event_callback: Any | None = None,
    ) -> UnifiedDiagnosisOutput:
        start_time = time.time()

        # 1. Triage & Route
        is_dag_mode = severity.lower() in ["critical", "high"] or len(evidence_items) >= 3
        triage_mode = "DAG_MULTI_AGENT" if is_dag_mode else "FAST_PATH"

        if event_callback:
            await event_callback("triage", {
                "triage_mode": triage_mode,
                "evidence_count": len(evidence_items),
                "severity": severity,
            })

        # 2. Selective Evidence Filtering
        rca_evidence = [ev for ev in evidence_items if ev.get("type") in ["github", "jira", "alert", "push", "pull_request", "workflow_run"]]
        if not rca_evidence:
            rca_evidence = evidence_items # fallback to all if empty

        impact_evidence = [ev for ev in evidence_items if ev.get("type") in ["slack", "gmail", "alert", "message", "reaction_added"]]
        if not impact_evidence:
            impact_evidence = evidence_items

        # 3. Step 1 of DAG: Parallel Execution of RCA Agent & Business Impact Agent
        logger.info(f"Executing DAG Step 1: Running Technical RCA and Business Impact Agents in parallel...")
        rca_task = asyncio.create_task(
            self._run_technical_rca_agent(investigation_title, investigation_description, rca_evidence)
        )
        impact_task = asyncio.create_task(
            self._run_business_impact_agent(investigation_title, severity, impact_evidence)
        )

        rca_result, impact_result = await asyncio.gather(rca_task, impact_task)

        if event_callback:
            await event_callback("rca_complete", rca_result.model_dump())
            await event_callback("business_impact_complete", impact_result.model_dump())

        # 4. Step 2 of DAG: Remediation Agent (depends on RCA + Business Impact)
        logger.info("Executing DAG Step 2: Running Remediation Agent with RCA & Business Impact context...")
        remediation_result = await self._run_remediation_agent(
            investigation_title, rca_result, impact_result
        )

        if event_callback:
            await event_callback("remediation_complete", remediation_result.model_dump())

        # 5. Executive Summary Synthesis
        exec_summary = (
            f"Active {severity.upper()} incident '{investigation_title}' caused by {rca_result.root_cause_summary} "
            f"Financially exposing ${impact_result.estimated_downtime_cost_per_hour:,.2f}/hr with {impact_result.sla_breach_status} SLA status."
        )

        execution_time_ms = int((time.time() - start_time) * 1000)
        logger.info(f"✅ Multi-Agent DAG Execution completed in {execution_time_ms}ms")

        return UnifiedDiagnosisOutput(
            triage_mode=triage_mode,
            executive_summary=exec_summary,
            technical_rca=rca_result,
            business_impact=impact_result,
            remediation_plan=remediation_result,
        )

    async def _run_technical_rca_agent(
        self, title: str, description: str, evidence: list[dict[str, Any]]
    ) -> TechnicalRCAResult:
        if not self.client:
            return self._fallback_rca(title, evidence)

        timeline_str = self._format_evidence_timeline(evidence)
        prompt = (
            f"Investigation Title: {title}\n"
            f"Description: {description}\n\n"
            f"Technical Telemetry & Code Evidence:\n{timeline_str}\n"
        )

        try:
            completion = await self.client.beta.chat.completions.parse(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are the Technical Root Cause Analysis (RCA) Agent. "
                            "Examine stack traces, code diffs, and telemetry logs provided in the evidence.\n"
                            "CRITICAL TRUTHFULNESS & GROUNDING RULES:\n"
                            "1. Analyze ONLY the provided evidence logs. GROUND YOUR ANALYSIS STRICTLY IN THE PROVIDED EVIDENCE.\n"
                            "2. DO NOT fabricate, invent, or hallucinate commit hashes, commit authors, stack traces, or error signatures if they are not explicitly present in the provided evidence logs.\n"
                            "3. If NO code commit (GitHub commit hash/author) is explicitly present in the evidence logs, set `offending_commit = null`.\n"
                            "4. If NO error stack trace or exception code exists in the evidence logs, set `error_fingerprints` to an empty list [].\n"
                            "5. Extract 1-2 exact supporting quotes or text excerpts from the evidence."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format=TechnicalRCAResult,
                temperature=0.1,
            )
            return completion.choices[0].message.parsed
        except Exception as e:
            logger.error(f"Technical RCA Agent failed: {e}", exc_info=True)
            return self._fallback_rca(title, evidence)

    async def _run_business_impact_agent(
        self, title: str, severity: str, evidence: list[dict[str, Any]]
    ) -> BusinessImpactResult:
        if not self.client:
            return self._fallback_business_impact(severity)

        timeline_str = self._format_evidence_timeline(evidence)
        prompt = (
            f"Investigation Title: {title}\n"
            f"Severity: {severity}\n\n"
            f"Customer Communications & Escalation Evidence:\n{timeline_str}\n"
        )

        try:
            completion = await self.client.beta.chat.completions.parse(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are the Business Impact & Financial SLA Risk Assessment Agent.\n"
                            "CRITICAL TRUTHFULNESS & GROUNDING RULES:\n"
                            "1. Analyze ONLY the provided evidence logs and severity.\n"
                            "2. DO NOT invent arbitrary financial downtime costs or fictitious customer account numbers if not supported by the evidence.\n"
                            "3. For user inquiry messages or non-outage Slack messages with no financial impact mentioned, set `estimated_downtime_cost_per_hour = 0.0`, `financial_risk_level = 'LOW'`, and `sla_breach_status = 'NOMINAL'`.\n"
                            "4. If customer account tiers are not specified in evidence, set `affected_customer_tiers` to an empty list []."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format=BusinessImpactResult,
                temperature=0.1,
            )
            return completion.choices[0].message.parsed
        except Exception as e:
            logger.error(f"Business Impact Agent failed: {e}", exc_info=True)
            return self._fallback_business_impact(severity)

    async def _run_remediation_agent(
        self,
        title: str,
        rca: TechnicalRCAResult,
        impact: BusinessImpactResult,
    ) -> RemediationPlanResult:
        if not self.client:
            return self._fallback_remediation(rca)

        prompt = (
            f"Investigation Title: {title}\n"
            f"Technical Root Cause: {rca.root_cause_summary}\n"
            f"Offending Commit: {rca.offending_commit.hash if rca.offending_commit and rca.offending_commit.hash else 'N/A (No commit recorded)'}\n"
            f"Financial Risk Exposure: ${impact.estimated_downtime_cost_per_hour:,.2f}/hr\n"
            f"SLA Status: {impact.sla_breach_status}\n"
            f"Impacted Services: {', '.join(rca.impacted_services)}\n"
        )

        try:
            completion = await self.client.beta.chat.completions.parse(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are the Remediation & Hotfix Agent.\n"
                            "CRITICAL TRUTHFULNESS & GROUNDING RULES:\n"
                            "1. Formulate step-by-step mitigation instructions based strictly on the RCA findings.\n"
                            "2. If `offending_commit` is null or N/A (no commit hash exists in evidence), set `git_rollback_command = 'N/A - No offending commit hash identified in evidence stream'`.\n"
                            "3. DO NOT invent fake commit hashes or fake git revert commands for non-existent code commits!"
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format=RemediationPlanResult,
                temperature=0.1,
            )
            return completion.choices[0].message.parsed
        except Exception as e:
            logger.error(f"Remediation Agent failed: {e}", exc_info=True)
            return self._fallback_remediation(rca)

    def _format_evidence_timeline(self, evidence: list[dict[str, Any]]) -> str:
        lines = []
        for idx, ev in enumerate(evidence, 1):
            created = ev.get("created_at", "N/A")
            platform = ev.get("type", "unknown")
            author = ev.get("author_name", "system")
            summary = ev.get("summary", "")
            metadata = ev.get("metadata", {})
            lines.append(f"{idx}. [{created}] Platform: {platform} | Author: {author} | {summary}\n   Metadata: {metadata}")
        return "\n".join(lines) if lines else "No platform evidence collected yet."

    # --- Fallback Generators for Safe Resilience ---
    def _fallback_rca(self, title: str, evidence: list[dict[str, Any]]) -> TechnicalRCAResult:
        # Check if any evidence item is from GitHub/code commit
        github_ev = next((ev for ev in evidence if ev.get("type") in ["github", "push", "pull_request"]), None)
        
        offending_commit = None
        if github_ev:
            meta = github_ev.get("metadata", {})
            commit_hash = meta.get("commit_hash") or meta.get("hash") or "HEAD~1"
            offending_commit = OffendingCommitInfo(
                hash=commit_hash,
                author=github_ev.get("author_name", "Developer"),
                message=github_ev.get("summary", "Code push"),
                diff_summary=meta.get("diff_summary", "Updated code modules")
            )

        quotes = []
        for ev in evidence[:2]:
            quotes.append(EvidenceQuote(
                platform=ev.get("type", "telemetry"),
                quote=ev.get("summary", "Reported anomaly"),
                source_url=ev.get("source_url")
            ))

        return TechnicalRCAResult(
            root_cause_summary=f"Analysis of reported telemetry signal for '{title}'.",
            offending_commit=offending_commit,
            impacted_services=["Deployment Service"] if "department" in title.lower() or "deployment" in title.lower() else ["General System"],
            error_fingerprints=[],
            evidence_quotes=quotes
        )

    def _fallback_business_impact(self, severity: str) -> BusinessImpactResult:
        is_critical = severity.lower() == "critical"
        is_high = severity.lower() == "high"
        
        cost = 15000.0 if is_critical else (5000.0 if is_high else 0.0)
        risk_level = "CRITICAL" if is_critical else ("HIGH" if is_high else "MEDIUM" if severity.lower() == "medium" else "LOW")
        sla_status = "IMMINENT_RISK" if is_critical else ("AT_RISK" if is_high else "NOMINAL")

        return BusinessImpactResult(
            financial_risk_level=risk_level,
            estimated_downtime_cost_per_hour=cost,
            sla_breach_status=sla_status,
            affected_customer_tiers=[],
            cross_functional_blast_radius=["Platform Operations"]
        )

    def _fallback_remediation(self, rca: TechnicalRCAResult) -> RemediationPlanResult:
        commit_hash = rca.offending_commit.hash if (rca.offending_commit and rca.offending_commit.hash) else None
        
        if commit_hash and not commit_hash.startswith("N/A"):
            rollback_cmd = f"git revert {commit_hash} --no-edit && git push origin main"
            mitigation = [
                f"1. Revert offending commit {commit_hash}.",
                "2. Verify service deployment health."
            ]
        else:
            rollback_cmd = "N/A - No offending commit hash identified in evidence stream"
            mitigation = [
                "1. Review evidence telemetry logs.",
                "2. Coordinate with service owners to investigate reported deployment issues.",
                "3. Monitor service health metrics."
            ]

        return RemediationPlanResult(
            immediate_mitigation_steps=mitigation,
            git_rollback_command=rollback_cmd,
            verification_script="curl -s -f http://localhost:8000/health || exit 1",
            jira_escalation_summary=f"[INVESTIGATION] {rca.root_cause_summary}"
        )
