from __future__ import annotations

import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from openai import APITimeoutError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.routes import augmis_business as augmis_business_routes
from app.core.database import Base, get_db
from app.core.security import get_current_user
from app.db_models import (
    AuditLog,
    BusinessDevelopmentExperienceItem,
    BusinessDevelopmentOpportunity,
    BusinessDevelopmentOpportunityAIAssessment,
    BusinessDevelopmentOpportunityExperienceMatch,
    Tenant,
    User,
)
from app.models.augmis_business_models import (
    AugmisBusinessBuyerRoleRecommendation,
    AugmisBusinessQualificationResult,
)
from app.services import augmis_business_ai_service as ai_service


def _fake_response(content: str, prompt_tokens: int = 100, completion_tokens: int = 40):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=SimpleNamespace(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        ),
    )


class _FakeCompletions:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = 0

    def create(self, **kwargs):
        self.calls += 1
        if not self._responses:
            raise AssertionError("No fake responses remaining")
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        if callable(response):
            return response(**kwargs)
        return response


class _FakeClient:
    def __init__(self, responses):
        self.chat = SimpleNamespace(completions=_FakeCompletions(responses))


class AugmisBusinessAIServiceTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(
            self.engine,
            tables=[
                Tenant.__table__,
                User.__table__,
                AuditLog.__table__,
                BusinessDevelopmentOpportunity.__table__,
                BusinessDevelopmentExperienceItem.__table__,
                BusinessDevelopmentOpportunityAIAssessment.__table__,
                BusinessDevelopmentOpportunityExperienceMatch.__table__,
            ],
        )
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.fixed_now = datetime(2026, 8, 7, 9, 0, 0, tzinfo=timezone.utc)
        self.original_now = ai_service._now
        self.original_api_key = ai_service.settings.OPENAI_API_KEY
        self.original_model = ai_service.settings.OPENAI_MODEL
        ai_service._now = lambda: self.fixed_now
        ai_service.settings.OPENAI_API_KEY = "test-key"
        ai_service.settings.OPENAI_MODEL = "gpt-4o-mini"
        self.current_user = {
            "tenant_id": "TENANT-1",
            "user_id": "USER-1",
            "email": "bd.admin@example.com",
            "permissions": [
                "business_development:read",
                "business_development:create",
                "business_development:update",
                "business_development:delete",
                "business_development:qualify",
            ],
            "allowed_modules": ["augmis_business"],
        }
        self._seed_core()

    def tearDown(self):
        ai_service._now = self.original_now
        ai_service.settings.OPENAI_API_KEY = self.original_api_key
        ai_service.settings.OPENAI_MODEL = self.original_model
        self.db.close()

    def _seed_core(self):
        self.db.add_all(
            [
                Tenant(tenant_id="TENANT-1", tenant_name="Tenant 1"),
                Tenant(tenant_id="TENANT-2", tenant_name="Tenant 2"),
                User(
                    user_id="USER-1",
                    tenant_id="TENANT-1",
                    name="Business Admin",
                    email="bd.admin@example.com",
                    password_hash="x",
                    role="tenant_admin",
                    status="ACTIVE",
                ),
                BusinessDevelopmentOpportunity(
                    id="BD-OPP-1",
                    tenant_id="TENANT-1",
                    source_type="portal",
                    source_name="Tender Board",
                    source_url="https://example.com/opportunities/1",
                    title="Document control workflow modernization",
                    organization_name="Acme Energy",
                    organization_domain="acme.example",
                    country="Saudi Arabia",
                    region="Riyadh",
                    industry="Energy",
                    raw_summary="The buyer needs document control and engineering workflow digitization.",
                    requirement_summary="Assess and improve document control workflows.",
                    business_problem="Manual routing slows approvals.",
                    expected_deliverables_json=["Assessment report", "Workflow design"],
                    required_technologies_json=["SharePoint", "Dashboards"],
                    published_budget=125000.0,
                    published_currency="USD",
                    closing_at=datetime(2026, 8, 20, 12, 0, 0, tzinfo=timezone.utc),
                    opportunity_status="under_review",
                    source_evidence_json=[{"summary": "Document control modernization"}],
                    created_by="USER-1",
                    updated_at=self.fixed_now,
                ),
                BusinessDevelopmentOpportunity(
                    id="BD-OPP-2",
                    tenant_id="TENANT-2",
                    source_type="portal",
                    source_name="Other Board",
                    title="Other tenant opportunity",
                    organization_name="Other Org",
                    requirement_summary="Other tenant scope.",
                    expected_deliverables_json=[],
                    required_technologies_json=[],
                    opportunity_status="new",
                    source_evidence_json=[],
                    created_by="USER-1",
                    updated_at=self.fixed_now,
                ),
                BusinessDevelopmentExperienceItem(
                    id="EXP-1",
                    tenant_id="TENANT-1",
                    name="Document Control Accelerator",
                    category="Document Control",
                    description="Workflow redesign and automation for document control teams.",
                    business_problems_json=["Slow approvals", "Manual document routing"],
                    features_json=["Routing", "Approvals"],
                    technologies_json=["SharePoint", "Power BI"],
                    industries_json=["Energy"],
                    keywords_json=["document", "workflow", "control"],
                    reusable_capabilities_json=["Workflow design", "Approval routing"],
                    confidentiality_safe_summary="Reusable document-control workflow accelerator.",
                    status="active",
                    created_by="USER-1",
                    updated_at=self.fixed_now,
                ),
                BusinessDevelopmentExperienceItem(
                    id="EXP-2",
                    tenant_id="TENANT-1",
                    name="Operations Dashboard",
                    category="Dashboards",
                    description="Operational KPI dashboards for industrial clients.",
                    business_problems_json=["Poor KPI visibility"],
                    features_json=["Executive views"],
                    technologies_json=["Dashboards", "Power BI"],
                    industries_json=["Energy"],
                    keywords_json=["dashboard", "kpi", "operations"],
                    reusable_capabilities_json=["Visualization"],
                    confidentiality_safe_summary="Reusable dashboard patterns.",
                    status="active",
                    created_by="USER-1",
                    updated_at=self.fixed_now,
                ),
            ]
        )
        self.db.commit()

    def _assessment_responses(self):
        return [
            _fake_response(
                """
                {
                  "requirement_summary": "Assess and improve document control workflows.",
                  "business_problem": "Manual routing slows approvals.",
                  "required_deliverables": ["Assessment report", "Workflow design"],
                  "required_technologies": ["SharePoint", "Dashboards"],
                  "functional_requirements": ["Workflow approvals"],
                  "non_functional_requirements": ["Operational continuity"],
                  "timeline_constraints": ["Award within current quarter"],
                  "eligibility_constraints": [],
                  "budget_information": {"value": 125000, "currency": "USD", "source_supported": true},
                  "missing_information": ["Decision-maker roles"],
                  "source_evidence": ["Assess and improve document control workflows."],
                  "confidence": 82
                }
                """
            ),
            _fake_response(
                """
                {
                  "matches": [
                    {
                      "experience_item_id": "EXP-1",
                      "name": "Document Control Accelerator",
                      "category": "Document Control",
                      "match_score": 91,
                      "matching_capabilities": ["Workflow design", "Approval routing"],
                      "matching_technologies": ["SharePoint"],
                      "business_problem_similarity": "Both address manual document approval bottlenecks.",
                      "explanation": "Closest prior capability set for the stated workflow problem."
                    },
                    {
                      "experience_item_id": "EXP-2",
                      "name": "Operations Dashboard",
                      "category": "Dashboards",
                      "match_score": 74,
                      "matching_capabilities": ["Visualization"],
                      "matching_technologies": ["Dashboards"],
                      "business_problem_similarity": "Useful for reporting outputs after workflow redesign.",
                      "explanation": "Supports reporting deliverables but is secondary to workflow expertise."
                    }
                  ]
                }
                """
            ),
            _fake_response(
                """
                {
                  "experience_relevance": {"score": 90, "explanation": "Strong overlap with prior workflow modernization work."},
                  "technology_match": {"score": 78, "explanation": "SharePoint and dashboard capabilities are available."},
                  "budget_attractiveness": {"score": 72, "explanation": "Budget appears viable for the scope but lacks detail."},
                  "delivery_feasibility": {"score": 76, "explanation": "A small team can likely deliver this scope."},
                  "buyer_accessibility": {"score": 64, "explanation": "Likely reachable roles are identifiable but unnamed."},
                  "deadline_feasibility": {"score": 68, "explanation": "Closing window is manageable but not generous."},
                  "market_payment_risk": {"score": 70, "explanation": "Public enterprise buyer suggests moderate commercial confidence."},
                  "delivery_profile": {
                    "delivery_model": "small_team",
                    "reasoning": "Workflow redesign plus reporting is feasible for a compact delivery team.",
                    "complexity_score": 61,
                    "estimated_delivery_weeks": 10,
                    "key_delivery_risks": ["Approval stakeholder availability"]
                  },
                  "recommendation": "pursue",
                  "explanation": "Capability fit is strong and the opportunity is commercially plausible.",
                  "risks": ["Unclear sponsor availability"],
                  "missing_information": ["Confirmed stakeholder map"],
                  "confidence": 77
                }
                """
            ),
            _fake_response(
                """
                {
                  "economic_buyer": {"role": "Operations Director", "reason": "Budget ownership often sits with operations leadership for workflow modernization.", "confidence": 72},
                  "operational_owner": {"role": "Document Control Manager", "reason": "This role owns the day-to-day process bottleneck described.", "confidence": 88},
                  "technical_evaluator": {"role": "IT Applications Manager", "reason": "Application integration and platform fit need technical review.", "confidence": 74},
                  "procurement_contact": {"role": "Procurement Manager", "reason": "Formal sourcing is likely handled through procurement.", "confidence": 69}
                }
                """
            ),
        ]

    def _patch_dependencies(self, responses):
        fake_client = _FakeClient(responses)
        return patch.multiple(
            ai_service,
            openai_client=fake_client,
            validate_usage_limit=lambda tenant_id, limit_name, db: None,
            add_ai_token_usage=lambda tenant_id, tokens_used, db: {
                "tenant_id": tenant_id,
                "tokens_used": tokens_used,
            },
        )

    def test_weighted_final_score_calculation(self):
        qualification = AugmisBusinessQualificationResult.model_validate(
            {
                "experience_relevance": {"score": 90, "explanation": "x"},
                "technology_match": {"score": 80, "explanation": "x"},
                "budget_attractiveness": {"score": 70, "explanation": "x"},
                "delivery_feasibility": {"score": 60, "explanation": "x"},
                "buyer_accessibility": {"score": 50, "explanation": "x"},
                "deadline_feasibility": {"score": 40, "explanation": "x"},
                "market_payment_risk": {"score": 30, "explanation": "x"},
                "delivery_profile": {
                    "delivery_model": "small_team",
                    "reasoning": "x",
                    "complexity_score": 55,
                    "estimated_delivery_weeks": 8,
                    "key_delivery_risks": [],
                },
                "recommendation": "review",
                "explanation": "x",
                "risks": [],
                "missing_information": [],
                "confidence": 60,
            }
        )
        self.assertEqual(ai_service._calculate_fit_score(qualification), 66.0)

    def test_invalid_component_score_and_recommendation_are_rejected(self):
        with self.assertRaises(Exception):
            AugmisBusinessQualificationResult.model_validate(
                {
                    "experience_relevance": {"score": 120, "explanation": "x"},
                    "technology_match": {"score": 80, "explanation": "x"},
                    "budget_attractiveness": {"score": 70, "explanation": "x"},
                    "delivery_feasibility": {"score": 60, "explanation": "x"},
                    "buyer_accessibility": {"score": 50, "explanation": "x"},
                    "deadline_feasibility": {"score": 40, "explanation": "x"},
                    "market_payment_risk": {"score": 30, "explanation": "x"},
                    "delivery_profile": {
                        "delivery_model": "solo",
                        "reasoning": "x",
                        "complexity_score": 40,
                        "estimated_delivery_weeks": 6,
                        "key_delivery_risks": [],
                    },
                    "recommendation": "review",
                    "explanation": "x",
                    "risks": [],
                    "missing_information": [],
                    "confidence": 60,
                }
            )

        with self.assertRaises(Exception):
            AugmisBusinessQualificationResult.model_validate(
                {
                    "experience_relevance": {"score": 80, "explanation": "x"},
                    "technology_match": {"score": 80, "explanation": "x"},
                    "budget_attractiveness": {"score": 70, "explanation": "x"},
                    "delivery_feasibility": {"score": 60, "explanation": "x"},
                    "buyer_accessibility": {"score": 50, "explanation": "x"},
                    "deadline_feasibility": {"score": 40, "explanation": "x"},
                    "market_payment_risk": {"score": 30, "explanation": "x"},
                    "delivery_profile": {
                        "delivery_model": "solo",
                        "reasoning": "x",
                        "complexity_score": 40,
                        "estimated_delivery_weeks": 6,
                        "key_delivery_risks": [],
                    },
                    "recommendation": "invalid",
                    "explanation": "x",
                    "risks": [],
                    "missing_information": [],
                    "confidence": 60,
                }
            )

    def test_buyer_role_schema_rejects_named_contacts(self):
        with self.assertRaises(Exception):
            AugmisBusinessBuyerRoleRecommendation(
                role="John Smith",
                reason="A named contact is not allowed here.",
                confidence=60,
            )

    def test_experience_shortlist_prefers_relevant_items(self):
        opportunity = self.db.query(BusinessDevelopmentOpportunity).filter_by(id="BD-OPP-1").first()
        items = self.db.query(BusinessDevelopmentExperienceItem).order_by(
            BusinessDevelopmentExperienceItem.id.asc()
        ).all()
        shortlisted = ai_service._shortlist_experience_items(opportunity, items, limit=1)
        self.assertEqual(shortlisted[0]["experience_item_id"], "EXP-1")

    def test_assessment_persists_history_and_experience_matches(self):
        with self._patch_dependencies(self._assessment_responses()):
            result = ai_service.assess_opportunity_ai(
                self.db,
                "TENANT-1",
                "BD-OPP-1",
                self.current_user,
            )

        assessment = result["data"]
        self.assertEqual(assessment["assessment_version"], 1)
        self.assertEqual(assessment["recommendation"], "pursue")
        self.assertEqual(len(assessment["experience_matches"]), 2)
        self.assertEqual(self.db.query(BusinessDevelopmentOpportunityAIAssessment).count(), 1)
        self.assertEqual(self.db.query(BusinessDevelopmentOpportunityExperienceMatch).count(), 2)

        latest = ai_service.get_latest_opportunity_ai_assessment(self.db, "TENANT-1", "BD-OPP-1")
        history = ai_service.list_opportunity_ai_assessment_history(self.db, "TENANT-1", "BD-OPP-1")
        matches = ai_service.list_latest_opportunity_experience_matches(
            self.db, "TENANT-1", "BD-OPP-1"
        )

        self.assertEqual(latest["data"]["assessment_version"], 1)
        self.assertEqual(len(history["data"]), 1)
        self.assertEqual(matches["data"][0]["experience_item_id"], "EXP-1")

    def test_rerun_creates_new_version(self):
        with self._patch_dependencies(self._assessment_responses()):
            ai_service.assess_opportunity_ai(self.db, "TENANT-1", "BD-OPP-1", self.current_user)
        with self._patch_dependencies(self._assessment_responses()):
            second = ai_service.assess_opportunity_ai(
                self.db, "TENANT-1", "BD-OPP-1", self.current_user
            )

        history = ai_service.list_opportunity_ai_assessment_history(self.db, "TENANT-1", "BD-OPP-1")
        self.assertEqual(second["data"]["assessment_version"], 2)
        self.assertEqual([row["assessment_version"] for row in history["data"]], [2, 1])

    def test_nonexistent_experience_ids_are_rejected(self):
        bad_responses = self._assessment_responses()
        bad_responses[1] = _fake_response(
            """
            {
              "matches": [
                {
                  "experience_item_id": "EXP-404",
                  "name": "Missing Item",
                  "category": "Dashboards",
                  "match_score": 80,
                  "matching_capabilities": ["Visualization"],
                  "matching_technologies": ["Dashboards"],
                  "business_problem_similarity": "Similar enough.",
                  "explanation": "Bad id for validation."
                }
              ]
            }
            """
        )
        with self._patch_dependencies(bad_responses):
            with self.assertRaises(Exception) as exc:
                ai_service.assess_opportunity_ai(
                    self.db, "TENANT-1", "BD-OPP-1", self.current_user
                )

        self.assertIn("Experience item not found", str(exc.exception))
        self.assertEqual(self.db.query(BusinessDevelopmentOpportunityAIAssessment).count(), 0)

    def test_missing_api_key_and_provider_timeout_are_handled(self):
        ai_service.settings.OPENAI_API_KEY = ""
        with self.assertRaises(Exception) as exc:
            ai_service.assess_opportunity_ai(self.db, "TENANT-1", "BD-OPP-1", self.current_user)
        self.assertIn("OpenAI API key", str(exc.exception))

        ai_service.settings.OPENAI_API_KEY = "test-key"
        with self._patch_dependencies([APITimeoutError("timeout"), APITimeoutError("timeout")]):
            with self.assertRaises(Exception) as timeout_exc:
                ai_service._run_json_agent(
                    tenant_id="TENANT-1",
                    user_id="USER-1",
                    opportunity_id="BD-OPP-1",
                    agent_type="requirement_extraction",
                    prompt_version="requirement_extraction_v1",
                    prompt="{}",
                    response_model=AugmisBusinessQualificationResult,
                    db=self.db,
                )
        self.assertIn("timed out", str(timeout_exc.exception))

    def test_invalid_json_and_invalid_schema_are_rejected(self):
        with self._patch_dependencies([_fake_response("not json")]):
            with self.assertRaises(Exception) as invalid_json_exc:
                ai_service._run_json_agent(
                    tenant_id="TENANT-1",
                    user_id="USER-1",
                    opportunity_id="BD-OPP-1",
                    agent_type="requirement_extraction",
                    prompt_version="requirement_extraction_v1",
                    prompt="{}",
                    response_model=AugmisBusinessQualificationResult,
                    db=self.db,
                )
        self.assertIn("invalid JSON", str(invalid_json_exc.exception))

        with self._patch_dependencies([_fake_response('{"recommendation":"pursue"}')]):
            with self.assertRaises(Exception) as invalid_schema_exc:
                ai_service._run_json_agent(
                    tenant_id="TENANT-1",
                    user_id="USER-1",
                    opportunity_id="BD-OPP-1",
                    agent_type="opportunity_qualification",
                    prompt_version="opportunity_qualification_v1",
                    prompt="{}",
                    response_model=AugmisBusinessQualificationResult,
                    db=self.db,
                )
        self.assertIn("invalid structured output", str(invalid_schema_exc.exception))

    def test_failed_rerun_preserves_previous_assessment(self):
        with self._patch_dependencies(self._assessment_responses()):
            ai_service.assess_opportunity_ai(self.db, "TENANT-1", "BD-OPP-1", self.current_user)

        with self._patch_dependencies([_fake_response("not json")]):
            with self.assertRaises(Exception):
                ai_service.assess_opportunity_ai(self.db, "TENANT-1", "BD-OPP-1", self.current_user)

        history = ai_service.list_opportunity_ai_assessment_history(self.db, "TENANT-1", "BD-OPP-1")
        self.assertEqual(len(history["data"]), 1)
        self.assertEqual(history["data"][0]["assessment_version"], 1)

    def test_tenant_isolation_returns_404(self):
        with self._patch_dependencies(self._assessment_responses()):
            ai_service.assess_opportunity_ai(self.db, "TENANT-1", "BD-OPP-1", self.current_user)

        with self.assertRaises(Exception) as exc:
            ai_service.get_latest_opportunity_ai_assessment(self.db, "TENANT-2", "BD-OPP-1")
        self.assertIn("Opportunity not found", str(exc.exception))

    def test_route_authorization_requires_qualify_permission(self):
        app = FastAPI()
        app.include_router(augmis_business_routes.router)
        app.dependency_overrides[get_db] = lambda: iter([self.db])

        def denied_user():
            return {
                **self.current_user,
                "permissions": ["business_development:read"],
            }

        app.dependency_overrides[get_current_user] = denied_user
        client = TestClient(app)

        with patch("app.core.security.validate_module_entitlement", lambda tenant_id, module_name: None):
            response = client.post("/api/augmis-business/opportunities/BD-OPP-1/ai-assess")

        self.assertEqual(response.status_code, 403)
        self.assertIn("Missing permission", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
