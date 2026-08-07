"""Add AUGMIS Business sales workflow tables.

Revision ID: fb1c2d3e4f5a
Revises: fa0b1c2d3e4f
Create Date: 2026-08-07 11:30:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "fb1c2d3e4f5a"
down_revision: Union[str, Sequence[str], None] = "fa0b1c2d3e4f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bd_prospects",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("organization_name", sa.String(), nullable=False),
        sa.Column("organization_domain", sa.String(), nullable=True),
        sa.Column("website_url", sa.String(), nullable=True),
        sa.Column("country", sa.String(), nullable=True),
        sa.Column("region", sa.String(), nullable=True),
        sa.Column("industry", sa.String(), nullable=True),
        sa.Column("prospect_status", sa.String(), nullable=False, server_default="active"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("source_opportunity_id", sa.String(), nullable=True),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["source_opportunity_id"], ["bd_opportunities.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "organization_name",
            "organization_domain",
            name="uq_bd_prospect_tenant_name_domain",
        ),
    )
    for index_name, columns in [
        ("ix_bd_prospects_tenant_id", ["tenant_id"]),
        ("ix_bd_prospects_organization_name", ["organization_name"]),
        ("ix_bd_prospects_organization_domain", ["organization_domain"]),
        ("ix_bd_prospects_country", ["country"]),
        ("ix_bd_prospects_region", ["region"]),
        ("ix_bd_prospects_industry", ["industry"]),
        ("ix_bd_prospects_prospect_status", ["prospect_status"]),
        ("ix_bd_prospects_source_opportunity_id", ["source_opportunity_id"]),
        ("ix_bd_prospects_tenant_status", ["tenant_id", "prospect_status"]),
        ("ix_bd_prospects_tenant_domain", ["tenant_id", "organization_domain"]),
    ]:
        op.create_index(index_name, "bd_prospects", columns, unique=False)

    op.create_table(
        "bd_contacts",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("prospect_id", sa.String(), nullable=False),
        sa.Column("full_name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column("job_title", sa.String(), nullable=True),
        sa.Column("linkedin_url", sa.String(), nullable=True),
        sa.Column("contact_status", sa.String(), nullable=False, server_default="active"),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["prospect_id"], ["bd_prospects.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "prospect_id",
            "email",
            name="uq_bd_contact_tenant_prospect_email",
        ),
    )
    for index_name, columns in [
        ("ix_bd_contacts_tenant_id", ["tenant_id"]),
        ("ix_bd_contacts_prospect_id", ["prospect_id"]),
        ("ix_bd_contacts_full_name", ["full_name"]),
        ("ix_bd_contacts_email", ["email"]),
        ("ix_bd_contacts_contact_status", ["contact_status"]),
        ("ix_bd_contacts_is_primary", ["is_primary"]),
        ("ix_bd_contacts_tenant_status", ["tenant_id", "contact_status"]),
    ]:
        op.create_index(index_name, "bd_contacts", columns, unique=False)

    op.create_table(
        "bd_leads",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("opportunity_id", sa.String(), nullable=False),
        sa.Column("prospect_id", sa.String(), nullable=False),
        sa.Column("primary_contact_id", sa.String(), nullable=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("lead_stage", sa.String(), nullable=False, server_default="new"),
        sa.Column("lead_status", sa.String(), nullable=False, server_default="active"),
        sa.Column("priority", sa.String(), nullable=False, server_default="medium"),
        sa.Column("source_type", sa.String(), nullable=True),
        sa.Column("source_name", sa.String(), nullable=True),
        sa.Column("estimated_value", sa.Float(), nullable=True),
        sa.Column("weighted_value", sa.Float(), nullable=True),
        sa.Column("probability_pct", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("converted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["opportunity_id"], ["bd_opportunities.id"]),
        sa.ForeignKeyConstraint(["primary_contact_id"], ["bd_contacts.id"]),
        sa.ForeignKeyConstraint(["prospect_id"], ["bd_prospects.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for index_name, columns in [
        ("ix_bd_leads_tenant_id", ["tenant_id"]),
        ("ix_bd_leads_opportunity_id", ["opportunity_id"]),
        ("ix_bd_leads_prospect_id", ["prospect_id"]),
        ("ix_bd_leads_primary_contact_id", ["primary_contact_id"]),
        ("ix_bd_leads_title", ["title"]),
        ("ix_bd_leads_lead_stage", ["lead_stage"]),
        ("ix_bd_leads_lead_status", ["lead_status"]),
        ("ix_bd_leads_priority", ["priority"]),
        ("ix_bd_leads_source_type", ["source_type"]),
        ("ix_bd_leads_tenant_stage", ["tenant_id", "lead_stage"]),
        ("ix_bd_leads_tenant_status", ["tenant_id", "lead_status"]),
        ("ix_bd_leads_tenant_opportunity", ["tenant_id", "opportunity_id"]),
    ]:
        op.create_index(index_name, "bd_leads", columns, unique=False)

    op.create_table(
        "bd_lead_experience_matches",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("lead_id", sa.String(), nullable=False),
        sa.Column("experience_item_id", sa.String(), nullable=False),
        sa.Column("relevance_score", sa.Float(), nullable=True),
        sa.Column("match_notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["experience_item_id"], ["bd_experience_items.id"]),
        sa.ForeignKeyConstraint(["lead_id"], ["bd_leads.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "lead_id",
            "experience_item_id",
            name="uq_bd_lead_experience_match",
        ),
    )
    for index_name, columns in [
        ("ix_bd_lead_experience_matches_tenant_id", ["tenant_id"]),
        ("ix_bd_lead_experience_matches_lead_id", ["lead_id"]),
        ("ix_bd_lead_experience_matches_experience_item_id", ["experience_item_id"]),
    ]:
        op.create_index(index_name, "bd_lead_experience_matches", columns, unique=False)

    op.create_table(
        "bd_tasks",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("lead_id", sa.String(), nullable=False),
        sa.Column("opportunity_id", sa.String(), nullable=True),
        sa.Column("prospect_id", sa.String(), nullable=True),
        sa.Column("assigned_user_id", sa.String(), nullable=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("task_type", sa.String(), nullable=False, server_default="follow_up"),
        sa.Column("task_status", sa.String(), nullable=False, server_default="open"),
        sa.Column("priority", sa.String(), nullable=False, server_default="medium"),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_by", sa.String(), nullable=True),
        sa.Column("completion_notes", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["assigned_user_id"], ["users.user_id"]),
        sa.ForeignKeyConstraint(["completed_by"], ["users.user_id"]),
        sa.ForeignKeyConstraint(["lead_id"], ["bd_leads.id"]),
        sa.ForeignKeyConstraint(["opportunity_id"], ["bd_opportunities.id"]),
        sa.ForeignKeyConstraint(["prospect_id"], ["bd_prospects.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for index_name, columns in [
        ("ix_bd_tasks_tenant_id", ["tenant_id"]),
        ("ix_bd_tasks_lead_id", ["lead_id"]),
        ("ix_bd_tasks_opportunity_id", ["opportunity_id"]),
        ("ix_bd_tasks_prospect_id", ["prospect_id"]),
        ("ix_bd_tasks_assigned_user_id", ["assigned_user_id"]),
        ("ix_bd_tasks_task_type", ["task_type"]),
        ("ix_bd_tasks_task_status", ["task_status"]),
        ("ix_bd_tasks_priority", ["priority"]),
        ("ix_bd_tasks_due_at", ["due_at"]),
        ("ix_bd_tasks_completed_at", ["completed_at"]),
        ("ix_bd_tasks_completed_by", ["completed_by"]),
        ("ix_bd_tasks_tenant_status", ["tenant_id", "task_status"]),
        ("ix_bd_tasks_tenant_due", ["tenant_id", "due_at"]),
        ("ix_bd_tasks_tenant_priority", ["tenant_id", "priority"]),
    ]:
        op.create_index(index_name, "bd_tasks", columns, unique=False)

    op.create_table(
        "bd_activities",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("lead_id", sa.String(), nullable=True),
        sa.Column("opportunity_id", sa.String(), nullable=True),
        sa.Column("prospect_id", sa.String(), nullable=True),
        sa.Column("contact_id", sa.String(), nullable=True),
        sa.Column("activity_type", sa.String(), nullable=False),
        sa.Column("subject", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("activity_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("direction", sa.String(), nullable=True),
        sa.Column("outcome", sa.String(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["contact_id"], ["bd_contacts.id"]),
        sa.ForeignKeyConstraint(["lead_id"], ["bd_leads.id"]),
        sa.ForeignKeyConstraint(["opportunity_id"], ["bd_opportunities.id"]),
        sa.ForeignKeyConstraint(["prospect_id"], ["bd_prospects.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.tenant_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for index_name, columns in [
        ("ix_bd_activities_tenant_id", ["tenant_id"]),
        ("ix_bd_activities_lead_id", ["lead_id"]),
        ("ix_bd_activities_opportunity_id", ["opportunity_id"]),
        ("ix_bd_activities_prospect_id", ["prospect_id"]),
        ("ix_bd_activities_contact_id", ["contact_id"]),
        ("ix_bd_activities_activity_type", ["activity_type"]),
        ("ix_bd_activities_activity_at", ["activity_at"]),
        ("ix_bd_activities_direction", ["direction"]),
        ("ix_bd_activities_outcome", ["outcome"]),
        ("ix_bd_activities_tenant_type", ["tenant_id", "activity_type"]),
        ("ix_bd_activities_tenant_activity_at", ["tenant_id", "activity_at"]),
    ]:
        op.create_index(index_name, "bd_activities", columns, unique=False)


def downgrade() -> None:
    for index_name in [
        "ix_bd_activities_tenant_activity_at",
        "ix_bd_activities_tenant_type",
        "ix_bd_activities_outcome",
        "ix_bd_activities_direction",
        "ix_bd_activities_activity_at",
        "ix_bd_activities_activity_type",
        "ix_bd_activities_contact_id",
        "ix_bd_activities_prospect_id",
        "ix_bd_activities_opportunity_id",
        "ix_bd_activities_lead_id",
        "ix_bd_activities_tenant_id",
    ]:
        op.drop_index(index_name, table_name="bd_activities")
    op.drop_table("bd_activities")

    for index_name in [
        "ix_bd_tasks_tenant_priority",
        "ix_bd_tasks_tenant_due",
        "ix_bd_tasks_tenant_status",
        "ix_bd_tasks_completed_by",
        "ix_bd_tasks_completed_at",
        "ix_bd_tasks_due_at",
        "ix_bd_tasks_priority",
        "ix_bd_tasks_task_status",
        "ix_bd_tasks_task_type",
        "ix_bd_tasks_assigned_user_id",
        "ix_bd_tasks_prospect_id",
        "ix_bd_tasks_opportunity_id",
        "ix_bd_tasks_lead_id",
        "ix_bd_tasks_tenant_id",
    ]:
        op.drop_index(index_name, table_name="bd_tasks")
    op.drop_table("bd_tasks")

    for index_name in [
        "ix_bd_lead_experience_matches_experience_item_id",
        "ix_bd_lead_experience_matches_lead_id",
        "ix_bd_lead_experience_matches_tenant_id",
    ]:
        op.drop_index(index_name, table_name="bd_lead_experience_matches")
    op.drop_table("bd_lead_experience_matches")

    for index_name in [
        "ix_bd_leads_tenant_opportunity",
        "ix_bd_leads_tenant_status",
        "ix_bd_leads_tenant_stage",
        "ix_bd_leads_source_type",
        "ix_bd_leads_priority",
        "ix_bd_leads_lead_status",
        "ix_bd_leads_lead_stage",
        "ix_bd_leads_title",
        "ix_bd_leads_primary_contact_id",
        "ix_bd_leads_prospect_id",
        "ix_bd_leads_opportunity_id",
        "ix_bd_leads_tenant_id",
    ]:
        op.drop_index(index_name, table_name="bd_leads")
    op.drop_table("bd_leads")

    for index_name in [
        "ix_bd_contacts_tenant_status",
        "ix_bd_contacts_is_primary",
        "ix_bd_contacts_contact_status",
        "ix_bd_contacts_email",
        "ix_bd_contacts_full_name",
        "ix_bd_contacts_prospect_id",
        "ix_bd_contacts_tenant_id",
    ]:
        op.drop_index(index_name, table_name="bd_contacts")
    op.drop_table("bd_contacts")

    for index_name in [
        "ix_bd_prospects_tenant_domain",
        "ix_bd_prospects_tenant_status",
        "ix_bd_prospects_source_opportunity_id",
        "ix_bd_prospects_prospect_status",
        "ix_bd_prospects_industry",
        "ix_bd_prospects_region",
        "ix_bd_prospects_country",
        "ix_bd_prospects_organization_domain",
        "ix_bd_prospects_organization_name",
        "ix_bd_prospects_tenant_id",
    ]:
        op.drop_index(index_name, table_name="bd_prospects")
    op.drop_table("bd_prospects")
