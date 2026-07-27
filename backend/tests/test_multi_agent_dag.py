import pytest
import uuid
from unittest.mock import AsyncMock, patch

from app.investigations.multi_agent import MultiAgentOrchestrator
from app.investigations.agent_schemas import UnifiedDiagnosisOutput, TechnicalRCAResult, BusinessImpactResult, RemediationPlanResult


@pytest.mark.asyncio
async def test_multi_agent_orchestrator_fallback():
    """Verify MultiAgentOrchestrator returns safe structured fallback outputs when OpenAI is unconfigured."""
    orchestrator = MultiAgentOrchestrator()
    orchestrator.client = None # Force fallback mode

    evidence_items = [
        {"type": "github", "summary": "PR #42 merged into main: fix/auth-gateway-oom", "author_name": "adhish1478"},
        {"type": "slack", "summary": "Alert: API Latency > 2000ms on /checkout", "author_name": "slackbot"},
        {"type": "jira", "summary": "KAN-3: Critical Database Connection Pool Exhausted", "author_name": "Jira Bot"},
    ]

    events_logged = []
    async def mock_callback(event, data):
        events_logged.append(event)

    result = await orchestrator.run_dag_analysis(
        investigation_title="Database Pool Exhaustion on Gateway",
        investigation_description="Severe latency spikes reported across API Gateway endpoints.",
        severity="critical",
        evidence_items=evidence_items,
        event_callback=mock_callback,
    )

    assert isinstance(result, UnifiedDiagnosisOutput)
    assert result.triage_mode == "DAG_MULTI_AGENT"
    assert isinstance(result.technical_rca, TechnicalRCAResult)
    assert isinstance(result.business_impact, BusinessImpactResult)
    assert isinstance(result.remediation_plan, RemediationPlanResult)

    # Check parallel execution events
    assert "triage" in events_logged
    assert "rca_complete" in events_logged
    assert "business_impact_complete" in events_logged
    assert "remediation_complete" in events_logged

    # Check fallback values
    assert result.business_impact.financial_risk_level == "CRITICAL"
    assert result.business_impact.estimated_downtime_cost_per_hour == 15000.0
    assert "git revert" in result.remediation_plan.git_rollback_command


@pytest.mark.asyncio
async def test_multi_agent_triage_fast_path():
    """Verify low-severity investigations with minimal evidence route through fast-path triage."""
    orchestrator = MultiAgentOrchestrator()
    orchestrator.client = None

    evidence_items = [
        {"type": "alert", "summary": "Low priority disk warning", "author_name": "system"},
    ]

    result = await orchestrator.run_dag_analysis(
        investigation_title="Disk Warning",
        investigation_description="Disk space 80% full",
        severity="low",
        evidence_items=evidence_items,
    )

    assert result.triage_mode == "FAST_PATH"
