from typing import Literal, Any
from pydantic import BaseModel, Field


class OffendingCommitInfo(BaseModel):
    hash: str | None = Field(default=None, description="Git commit SHA hash if identified")
    author: str | None = Field(default=None, description="Author of the offending commit")
    message: str | None = Field(default=None, description="Commit message summary")
    diff_summary: str | None = Field(default=None, description="Key files or lines changed")


class EvidenceQuote(BaseModel):
    platform: str = Field(..., description="Platform name: github, slack, jira, gmail, alert")
    quote: str = Field(..., description="Exact relevant excerpt or log line")
    source_url: str | None = Field(default=None, description="Permalink URL to the evidence item")


class TechnicalRCAResult(BaseModel):
    root_cause_summary: str = Field(..., description="Technical explanation of the root cause based on telemetry evidence")
    offending_commit: OffendingCommitInfo | None = Field(default=None, description="Offending code change details")
    impacted_services: list[str] = Field(default_factory=list, description="List of microservices or system components affected")
    error_fingerprints: list[str] = Field(default_factory=list, description="Stack trace signatures or error codes identified")
    evidence_quotes: list[EvidenceQuote] = Field(default_factory=list, description="Supporting log quotes or telemetry excerpts")


class CustomerImpactTier(BaseModel):
    tier: str = Field(..., description="Customer tier: Enterprise, Growth, Starter")
    account_count: int = Field(default=1, description="Estimated number of affected tenant accounts")
    impact_summary: str = Field(..., description="Specific business or operational impact on this tier")


class BusinessImpactResult(BaseModel):
    financial_risk_level: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"] = Field(..., description="Overall financial exposure level")
    estimated_downtime_cost_per_hour: float = Field(..., description="Estimated dollar cost of downtime per hour")
    sla_breach_status: Literal["BREACHED", "IMMINENT_RISK", "AT_RISK", "NOMINAL"] = Field(..., description="SLA compliance status")
    affected_customer_tiers: list[CustomerImpactTier] = Field(default_factory=list, description="Breakdown of customer tiers impacted")
    cross_functional_blast_radius: list[str] = Field(default_factory=list, description="Impacted internal teams (e.g. Payments, Platform Core)")


class RemediationPlanResult(BaseModel):
    immediate_mitigation_steps: list[str] = Field(..., description="Numbered step-by-step hotfix instructions")
    git_rollback_command: str = Field(..., description="Exact git revert or rollout command to execute")
    verification_script: str = Field(..., description="Shell script or curl command to verify the hotfix")
    jira_escalation_summary: str = Field(..., description="Formated summary for Jira ticket creation")


class UnifiedDiagnosisOutput(BaseModel):
    triage_mode: Literal["DAG_MULTI_AGENT", "FAST_PATH"] = Field(default="DAG_MULTI_AGENT", description="Execution path chosen by triage router")
    executive_summary: str = Field(..., description="High-level 2-sentence executive summary for on-call engineers")
    technical_rca: TechnicalRCAResult = Field(..., description="Detailed technical root cause analysis")
    business_impact: BusinessImpactResult = Field(..., description="Business, financial, and SLA impact assessment")
    remediation_plan: RemediationPlanResult = Field(..., description="Actionable hotfix and remediation steps")
