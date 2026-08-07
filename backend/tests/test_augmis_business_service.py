from datetime import datetime, timezone
import unittest

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.db_models import (
    AuditLog,
    BusinessDevelopmentActivity,
    BusinessDevelopmentContact,
    BusinessDevelopmentExperienceItem,
    BusinessDevelopmentLead,
    BusinessDevelopmentLeadExperienceMatch,
    BusinessDevelopmentOpportunity,
    BusinessDevelopmentProspect,
    BusinessDevelopmentTask,
    Tenant,
    User,
)
from app.models.augmis_business_models import (
    AugmisBusinessBuildLeadRequest,
    AugmisBusinessContactCreateRequest,
    AugmisBusinessContactUpdateRequest,
    AugmisBusinessProspectCreateRequest,
    AugmisBusinessProspectUpdateRequest,
    AugmisBusinessTaskCreateRequest,
    AugmisBusinessTaskUpdateRequest,
)
from app.services import augmis_business_service as service


class AugmisBusinessServiceTest(unittest.TestCase):
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
                BusinessDevelopmentExperienceItem.__table__,
                BusinessDevelopmentOpportunity.__table__,
                BusinessDevelopmentProspect.__table__,
                BusinessDevelopmentContact.__table__,
                BusinessDevelopmentLead.__table__,
                BusinessDevelopmentLeadExperienceMatch.__table__,
                BusinessDevelopmentTask.__table__,
                BusinessDevelopmentActivity.__table__,
            ],
        )
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.fixed_now = datetime(2026, 8, 7, 9, 0, 0, tzinfo=timezone.utc)
        self.original_now = service._now
        service._now = lambda: self.fixed_now
        self.current_user = {
            "tenant_id": "TENANT-1",
            "user_id": "USER-1",
            "permissions": [
                "business_development:read",
                "business_development:create",
                "business_development:update",
                "business_development:delete",
            ],
            "allowed_modules": ["augmis_business"],
        }
        self._seed_core()

    def tearDown(self):
        service._now = self.original_now
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
                User(
                    user_id="USR-0002",
                    tenant_id="TENANT-1",
                    name="Uday Halankar",
                    email="uday@example.com",
                    password_hash="x",
                    role="manager",
                    status="ACTIVE",
                ),
                User(
                    user_id="USR-0003",
                    tenant_id="TENANT-1",
                    name="Inactive User",
                    email="inactive@example.com",
                    password_hash="x",
                    role="viewer",
                    status="INACTIVE",
                ),
                User(
                    user_id="USR-9001",
                    tenant_id="TENANT-2",
                    name="Other Tenant User",
                    email="other@example.com",
                    password_hash="x",
                    role="manager",
                    status="ACTIVE",
                ),
                BusinessDevelopmentOpportunity(
                    id="BD-OPP-1",
                    tenant_id="TENANT-1",
                    source_type="portal",
                    source_name="Tender Board",
                    source_url="https://example.com/opportunities/1",
                    title="Operational readiness assessment",
                    organization_name="Acme Energy",
                    organization_domain="acme.example",
                    country="Saudi Arabia",
                    region="Riyadh",
                    industry="Energy",
                    requirement_summary="Assess readiness workflows and launch controls.",
                    expected_deliverables_json=["Assessment report"],
                    required_technologies_json=["Dashboards"],
                    published_budget=125000.0,
                    estimated_value_min=100000.0,
                    estimated_value_max=150000.0,
                    estimated_currency="USD",
                    opportunity_status="qualified",
                    source_evidence_json=[],
                    created_by="USER-1",
                    updated_at=self.fixed_now,
                ),
                BusinessDevelopmentOpportunity(
                    id="BD-OPP-2",
                    tenant_id="TENANT-2",
                    source_type="portal",
                    source_name="Tenant 2 Board",
                    title="Tenant 2 opportunity",
                    organization_name="Tenant 2 Org",
                    requirement_summary="Other tenant",
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
                    name="Readiness Dashboard",
                    category="Dashboards",
                    description="Readiness reporting experience.",
                    business_problems_json=[],
                    features_json=[],
                    technologies_json=[],
                    industries_json=[],
                    keywords_json=[],
                    reusable_capabilities_json=[],
                    confidentiality_safe_summary="Reusable readiness dashboard.",
                    status="active",
                    created_by="USER-1",
                    updated_at=self.fixed_now,
                ),
            ]
        )
        self.db.commit()

    def _create_prospect(self, **overrides):
        payload = AugmisBusinessProspectCreateRequest(
            organization_name="Prospect One",
            organization_domain="prospect-one.example",
            country="Saudi Arabia",
            **overrides,
        )
        return service.create_prospect(self.db, "TENANT-1", self.current_user, payload)["data"]

    def _create_contact(self, prospect_id: str, **overrides):
        payload_data = {
            "full_name": "Prospect Contact",
            "email": "prospect.contact@example.com",
        }
        payload_data.update(overrides)
        payload = AugmisBusinessContactCreateRequest(**payload_data)
        return service.create_contact(self.db, "TENANT-1", prospect_id, self.current_user, payload)["data"]

    def test_prospect_extended_fields_round_trip(self):
        created = self._create_prospect(
            city="Riyadh",
            organization_type="enterprise",
            employee_range="1000-5000",
            general_email="hello@prospect-one.example",
            general_phone="+966500000000",
            estimated_account_potential_min=250000.0,
            estimated_account_potential_max=400000.0,
            estimated_currency="usd",
        )

        self.assertEqual(created["city"], "Riyadh")
        self.assertEqual(created["organization_type"], "enterprise")
        self.assertEqual(created["employee_range"], "1000-5000")
        self.assertEqual(created["general_email"], "hello@prospect-one.example")
        self.assertEqual(created["estimated_currency"], "USD")

        updated = service.update_prospect(
            self.db,
            "TENANT-1",
            created["id"],
            self.current_user,
            AugmisBusinessProspectUpdateRequest(
                city="Jeddah",
                estimated_account_potential_max=450000.0,
            ),
        )["data"]
        self.assertEqual(updated["city"], "Jeddah")
        self.assertEqual(updated["estimated_account_potential_max"], 450000.0)

    def test_prospect_schema_validation_rejects_invalid_email_and_range(self):
        with self.assertRaises(ValidationError):
            AugmisBusinessProspectCreateRequest(
                organization_name="Bad Prospect",
                general_email="not-an-email",
            )

        with self.assertRaises(ValidationError):
            AugmisBusinessProspectCreateRequest(
                organization_name="Bad Prospect",
                estimated_account_potential_min=500.0,
                estimated_account_potential_max=100.0,
            )

    def test_prospect_duplicate_detection_uses_domain_then_name_and_country(self):
        service.create_prospect(
            self.db,
            "TENANT-1",
            self.current_user,
            AugmisBusinessProspectCreateRequest(
                organization_name="Acme Energy",
                organization_domain="acme.example",
                country="Saudi Arabia",
            ),
        )

        with self.assertRaises(HTTPException) as domain_exc:
            service.create_prospect(
                self.db,
                "TENANT-1",
                self.current_user,
                AugmisBusinessProspectCreateRequest(
                    organization_name="Different Acme Label",
                    organization_domain="acme.example",
                    country="UAE",
                ),
            )
        self.assertEqual(domain_exc.exception.status_code, 409)

        service.create_prospect(
            self.db,
            "TENANT-1",
            self.current_user,
            AugmisBusinessProspectCreateRequest(
                organization_name="Global Systems",
                organization_domain=None,
                country="Saudi Arabia",
            ),
        )
        created = service.create_prospect(
            self.db,
            "TENANT-1",
            self.current_user,
            AugmisBusinessProspectCreateRequest(
                organization_name="Global Systems",
                organization_domain=None,
                country="UAE",
            ),
        )["data"]
        self.assertEqual(created["country"], "UAE")

        with self.assertRaises(HTTPException) as country_exc:
            service.create_prospect(
                self.db,
                "TENANT-1",
                self.current_user,
                AugmisBusinessProspectCreateRequest(
                    organization_name="Global Systems",
                    organization_domain=None,
                    country="Saudi Arabia",
                ),
            )
        self.assertEqual(country_exc.exception.status_code, 409)

    def test_domain_duplicate_detects_casing_and_whitespace(self):
        service.create_prospect(
            self.db,
            "TENANT-1",
            self.current_user,
            AugmisBusinessProspectCreateRequest(
                organization_name="Acme Energy",
                organization_domain="  ACME.EXAMPLE  ",
            ),
        )

        with self.assertRaises(HTTPException) as exc:
            service.create_prospect(
                self.db,
                "TENANT-1",
                self.current_user,
                AugmisBusinessProspectCreateRequest(
                    organization_name="Another Name",
                    organization_domain="acme.example",
                ),
            )

        self.assertEqual(exc.exception.status_code, 409)

    def test_name_and_country_duplicate_detects_casing_and_whitespace(self):
        service.create_prospect(
            self.db,
            "TENANT-1",
            self.current_user,
            AugmisBusinessProspectCreateRequest(
                organization_name="  Abcdcsvvd  ",
                country="  INDIA  ",
            ),
        )

        with self.assertRaises(HTTPException) as exc:
            service.create_prospect(
                self.db,
                "TENANT-1",
                self.current_user,
                AugmisBusinessProspectCreateRequest(
                    organization_name="abCDcsvvd",
                    country="india",
                ),
            )

        self.assertEqual(exc.exception.status_code, 409)

    def test_same_name_different_country_is_allowed(self):
        service.create_prospect(
            self.db,
            "TENANT-1",
            self.current_user,
            AugmisBusinessProspectCreateRequest(
                organization_name="Shared Name",
                country="India",
            ),
        )

        created = service.create_prospect(
            self.db,
            "TENANT-1",
            self.current_user,
            AugmisBusinessProspectCreateRequest(
                organization_name="  Shared   Name ",
                country="Saudi Arabia",
            ),
        )["data"]

        self.assertEqual(created["country"], "Saudi Arabia")

    def test_same_name_without_country_is_not_auto_merged(self):
        service.create_prospect(
            self.db,
            "TENANT-1",
            self.current_user,
            AugmisBusinessProspectCreateRequest(
                organization_name="Countryless Org",
                country="India",
            ),
        )

        created = service.create_prospect(
            self.db,
            "TENANT-1",
            self.current_user,
            AugmisBusinessProspectCreateRequest(
                organization_name="  Countryless   Org ",
                country=None,
            ),
        )["data"]

        self.assertIsNone(created["country"])

    def test_older_stored_rows_are_matched_after_runtime_normalization(self):
        self.db.add(
            BusinessDevelopmentProspect(
                id="BD-PRS-LEGACY-1",
                tenant_id="TENANT-1",
                organization_name="Legacy   Prospect",
                organization_domain=None,
                country="  INDIA  ",
                prospect_status="active",
                created_by="USER-1",
                updated_at=self.fixed_now,
            )
        )
        self.db.commit()

        with self.assertRaises(HTTPException) as exc:
            service.create_prospect(
                self.db,
                "TENANT-1",
                self.current_user,
                AugmisBusinessProspectCreateRequest(
                    organization_name=" legacy prospect ",
                    country="india",
                ),
            )

        self.assertEqual(exc.exception.status_code, 409)

    def test_role_only_contact_creation_and_default_verification_status(self):
        prospect = self._create_prospect()
        created = service.create_contact(
            self.db,
            "TENANT-1",
            prospect["id"],
            self.current_user,
            AugmisBusinessContactCreateRequest(
                full_name=None,
                email=None,
                phone=None,
                job_title="Head of Procurement",
                buyer_role="economic_buyer",
                is_primary=True,
            ),
        )["data"]

        self.assertIsNone(created["full_name"])
        self.assertEqual(created["job_title"], "Head of Procurement")
        self.assertEqual(created["buyer_role"], "economic_buyer")
        self.assertEqual(created["verification_status"], "unverified")

    def test_contact_schema_validation_rejects_empty_and_bad_enums(self):
        with self.assertRaises(ValidationError):
            AugmisBusinessContactCreateRequest(
                full_name=None,
                email=None,
                phone=None,
                job_title=None,
            )

        with self.assertRaises(ValidationError):
            AugmisBusinessContactCreateRequest(
                full_name="Valid",
                buyer_role="bad_role",
            )

        with self.assertRaises(ValidationError):
            AugmisBusinessContactCreateRequest(
                full_name="Valid",
                verification_status="maybe",
            )

        with self.assertRaises(ValidationError):
            AugmisBusinessContactCreateRequest(
                full_name="Valid",
                confidence_score=101,
            )

    def test_primary_contact_reassignment_enforces_single_primary(self):
        prospect = self._create_prospect()
        first = self._create_contact(prospect["id"], is_primary=True)
        second = self._create_contact(
            prospect["id"],
            full_name="Second Contact",
            email="second.contact@example.com",
            is_primary=True,
        )

        refreshed_first = service.get_prospect(self.db, "TENANT-1", prospect["id"])["data"]["contacts"][1]
        refreshed_second = service.get_prospect(self.db, "TENANT-1", prospect["id"])["data"]["contacts"][0]
        self.assertFalse(refreshed_first["is_primary"])
        self.assertTrue(refreshed_second["is_primary"])

        reselected = service.update_contact(
            self.db,
            "TENANT-1",
            first["id"],
            self.current_user,
            AugmisBusinessContactUpdateRequest(is_primary=True),
        )["data"]
        contacts = service.list_prospect_contacts(self.db, "TENANT-1", prospect["id"])["data"]
        primary_count = sum(1 for row in contacts if row["is_primary"])
        self.assertTrue(reselected["is_primary"])
        self.assertEqual(primary_count, 1)

    def test_delete_contact_is_blocked_when_referenced_by_lead(self):
        created = service.build_lead(
            self.db,
            "TENANT-1",
            "BD-OPP-1",
            self.current_user,
            AugmisBusinessBuildLeadRequest(
                contact_name="Nora Sales",
                contact_email="nora.sales@acme.example",
            ),
        )["data"]
        contact_id = created["lead"]["primary_contact"]["id"]

        with self.assertRaises(HTTPException) as exc:
            service.delete_contact(self.db, "TENANT-1", contact_id, self.current_user)

        self.assertEqual(exc.exception.status_code, 409)
        self.assertIn("Reassign any lead primary contact first", exc.exception.detail)

    def test_build_lead_supports_role_only_contact(self):
        result = service.build_lead(
            self.db,
            "TENANT-1",
            "BD-OPP-1",
            self.current_user,
            AugmisBusinessBuildLeadRequest(
                contact_name=None,
                contact_email=None,
                contact_phone=None,
                contact_job_title="VP Transformation",
                selected_experience_matches=[
                    {"experience_item_id": "EXP-1", "relevance_score": 0.9}
                ],
                first_task_priority="high",
            ),
        )["data"]

        self.assertEqual(result["opportunity"]["opportunity_status"], "converted")
        self.assertEqual(result["lead"]["primary_contact"]["job_title"], "VP Transformation")
        self.assertIsNone(result["lead"]["primary_contact"]["full_name"])
        self.assertEqual(result["lead"]["primary_contact"]["verification_status"], "unverified")

    def test_build_lead_rolls_back_when_match_lookup_fails(self):
        with self.assertRaises(HTTPException) as exc:
            service.build_lead(
                self.db,
                "TENANT-1",
                "BD-OPP-1",
                self.current_user,
                AugmisBusinessBuildLeadRequest(
                    contact_name="Nora Sales",
                    contact_email="nora.sales@acme.example",
                    selected_experience_matches=[{"experience_item_id": "EXP-MISSING"}],
                ),
            )

        self.assertEqual(exc.exception.status_code, 404)
        self.assertEqual(self.db.query(BusinessDevelopmentProspect).count(), 0)
        self.assertEqual(self.db.query(BusinessDevelopmentContact).count(), 0)
        self.assertEqual(self.db.query(BusinessDevelopmentLead).count(), 0)

    def test_list_prospect_related_records(self):
        build_result = service.build_lead(
            self.db,
            "TENANT-1",
            "BD-OPP-1",
            self.current_user,
            AugmisBusinessBuildLeadRequest(
                contact_name="Nora Sales",
                contact_email="nora.sales@acme.example",
            ),
        )["data"]
        prospect_id = build_result["lead"]["prospect"]["id"]

        contacts = service.list_prospect_contacts(self.db, "TENANT-1", prospect_id)["data"]
        opportunities = service.list_prospect_opportunities(self.db, "TENANT-1", prospect_id)["data"]
        leads = service.list_prospect_leads(self.db, "TENANT-1", prospect_id)["data"]
        activities = service.list_prospect_activities(self.db, "TENANT-1", prospect_id)["data"]

        self.assertEqual(len(contacts), 1)
        self.assertEqual(len(opportunities), 1)
        self.assertEqual(opportunities[0]["id"], "BD-OPP-1")
        self.assertEqual(len(leads), 1)
        self.assertEqual(leads[0]["opportunity_id"], "BD-OPP-1")
        self.assertGreaterEqual(len(activities), 4)
        self.assertEqual(activities, sorted(activities, key=lambda row: row["created_at"], reverse=True))

    def test_prospect_related_endpoints_are_tenant_scoped(self):
        prospect = self._create_prospect()

        for func in (
            service.get_prospect,
            service.list_prospect_contacts,
            service.list_prospect_opportunities,
            service.list_prospect_leads,
            service.list_prospect_activities,
        ):
            with self.assertRaises(HTTPException) as exc:
                func(self.db, "TENANT-2", prospect["id"])
            self.assertEqual(exc.exception.status_code, 404)

    def test_working_day_due_date_calculation(self):
        due_at = service.calculate_working_day_due_at(self.fixed_now, "high")
        self.assertEqual(due_at.date().isoformat(), "2026-08-11")
        self.assertEqual(due_at.hour, 17)

    def test_create_task_rejects_unknown_assigned_user(self):
        build_result = service.build_lead(
            self.db,
            "TENANT-1",
            "BD-OPP-1",
            self.current_user,
            AugmisBusinessBuildLeadRequest(
                contact_name="Nora Sales",
                contact_email="nora.sales@acme.example",
            ),
        )["data"]

        with self.assertRaises(HTTPException) as exc:
            service.create_task(
                self.db,
                "TENANT-1",
                self.current_user,
                AugmisBusinessTaskCreateRequest(
                    lead_id=build_result["lead"]["id"],
                    title="Invalid assignee task",
                    assigned_user_id="12345",
                ),
            )

        self.assertEqual(exc.exception.status_code, 400)
        self.assertIn("Assigned user not found for tenant", exc.exception.detail)

    def test_update_task_rejects_unknown_assigned_user(self):
        build_result = service.build_lead(
            self.db,
            "TENANT-1",
            "BD-OPP-1",
            self.current_user,
            AugmisBusinessBuildLeadRequest(
                contact_name="Nora Sales",
                contact_email="nora.sales@acme.example",
            ),
        )["data"]
        task_id = build_result["first_task"]["id"]

        with self.assertRaises(HTTPException) as exc:
            service.update_task(
                self.db,
                "TENANT-1",
                task_id,
                self.current_user,
                AugmisBusinessTaskUpdateRequest(assigned_user_id="12345"),
            )

        self.assertEqual(exc.exception.status_code, 400)
        self.assertIn("Assigned user not found for tenant", exc.exception.detail)

    def test_build_lead_rejects_unknown_assigned_user_for_first_task(self):
        with self.assertRaises(HTTPException) as exc:
            service.build_lead(
                self.db,
                "TENANT-1",
                "BD-OPP-1",
                self.current_user,
                AugmisBusinessBuildLeadRequest(
                    contact_name="Nora Sales",
                    contact_email="nora.sales@acme.example",
                    assigned_user_id="12345",
                ),
            )

        self.assertEqual(exc.exception.status_code, 400)
        self.assertIn("Assigned user not found for tenant", exc.exception.detail)
        self.assertEqual(self.db.query(BusinessDevelopmentLead).count(), 0)
        self.assertEqual(self.db.query(BusinessDevelopmentTask).count(), 0)

    def test_list_assignable_users_is_tenant_scoped_and_searchable(self):
        by_name = service.list_assignable_users(
            self.db,
            "TENANT-1",
            search="Uday",
        )["data"]
        self.assertEqual([row["user_id"] for row in by_name], ["USR-0002"])

        by_email = service.list_assignable_users(
            self.db,
            "TENANT-1",
            search="uday@example.com",
        )["data"]
        self.assertEqual([row["user_id"] for row in by_email], ["USR-0002"])

        by_user_id = service.list_assignable_users(
            self.db,
            "TENANT-1",
            search="USR-0002",
        )["data"]
        self.assertEqual([row["user_id"] for row in by_user_id], ["USR-0002"])

        no_cross_tenant = service.list_assignable_users(
            self.db,
            "TENANT-1",
            search="Other Tenant User",
        )["data"]
        self.assertEqual(no_cross_tenant, [])

    def test_list_assignable_users_excludes_inactive_by_default_and_can_include_them(self):
        default_rows = service.list_assignable_users(
            self.db,
            "TENANT-1",
            search="inactive",
        )["data"]
        self.assertEqual(default_rows, [])

        included_rows = service.list_assignable_users(
            self.db,
            "TENANT-1",
            search="inactive",
            include_inactive=True,
        )["data"]
        self.assertEqual([row["user_id"] for row in included_rows], ["USR-0003"])
        self.assertEqual(included_rows[0]["status"], "INACTIVE")

    def test_task_search_matches_title_description_and_filters(self):
        build_one = service.build_lead(
            self.db,
            "TENANT-1",
            "BD-OPP-1",
            self.current_user,
            AugmisBusinessBuildLeadRequest(
                contact_name="Nora Sales",
                contact_email="nora.sales@acme.example",
                lead_title="Lead One",
            ),
        )["data"]
        first_lead_id = build_one["lead"]["id"]

        service.create_task(
            self.db,
            "TENANT-1",
            self.current_user,
            AugmisBusinessTaskCreateRequest(
                lead_id=first_lead_id,
                title="Follow-up workshop",
                description="Coordinate follow-up workshop notes",
                task_type="follow_up",
                priority="high",
                assigned_user_id="USR-0002",
            ),
        )
        second_task = service.create_task(
            self.db,
            "TENANT-1",
            self.current_user,
            AugmisBusinessTaskCreateRequest(
                lead_id=first_lead_id,
                title="Proposal draft",
                description="Prepare commercial pricing pack",
                task_type="proposal",
                priority="low",
            ),
        )["data"]
        service.update_task(
            self.db,
            "TENANT-1",
            second_task["id"],
            self.current_user,
            AugmisBusinessTaskUpdateRequest(task_status="in_progress"),
        )

        title_match = service.list_tasks(
            self.db,
            "TENANT-1",
            search="workshop",
        )["data"]
        self.assertEqual(len(title_match), 1)
        self.assertEqual(title_match[0]["title"], "Follow-up workshop")

        description_match = service.list_tasks(
            self.db,
            "TENANT-1",
            search="pricing pack",
        )["data"]
        self.assertEqual(len(description_match), 1)
        self.assertEqual(description_match[0]["title"], "Proposal draft")

        combined_filter = service.list_tasks(
            self.db,
            "TENANT-1",
            search="follow-up",
            status_filter="open",
            priority="high",
            lead_id=first_lead_id,
        )["data"]
        self.assertEqual(len(combined_filter), 1)
        self.assertEqual(combined_filter[0]["title"], "Follow-up workshop")

        status_combined_filter = service.list_tasks(
            self.db,
            "TENANT-1",
            search="pricing pack",
            status_filter="in_progress",
            lead_id=first_lead_id,
        )["data"]
        self.assertEqual(len(status_combined_filter), 1)
        self.assertEqual(status_combined_filter[0]["title"], "Proposal draft")

    def test_task_search_omitted_preserves_existing_behavior(self):
        build_one = service.build_lead(
            self.db,
            "TENANT-1",
            "BD-OPP-1",
            self.current_user,
            AugmisBusinessBuildLeadRequest(
                contact_name="Nora Sales",
                contact_email="nora.sales@acme.example",
            ),
        )["data"]

        service.create_task(
            self.db,
            "TENANT-1",
            self.current_user,
            AugmisBusinessTaskCreateRequest(
                lead_id=build_one["lead"]["id"],
                title="Generic task",
            ),
        )

        result = service.list_tasks(self.db, "TENANT-1")
        self.assertGreaterEqual(result["pagination"]["total"], 2)


if __name__ == "__main__":
    unittest.main()
