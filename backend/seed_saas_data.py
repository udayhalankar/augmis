from datetime import date
from uuid import uuid4

from app.core.database import SessionLocal
from app.db_models import (
    BusinessDevelopmentExperienceItem,
    Plan,
    Tenant,
    TenantUsage,
    User,
)


AUGMIS_BUSINESS_MODULE = "augmis_business"
AUGMIS_BUSINESS_PERMISSIONS = [
    "business_development:read",
    "business_development:create",
    "business_development:update",
    "business_development:delete",
    "business_development:scan",
    "business_development:qualify",
    "business_development:outreach",
    "business_development:admin",
]

EXPERIENCE_CATALOGUE_ITEMS = [
    {
        "category": "Workflow and approvals",
        "name": "Digital MOC Form",
        "description": "Structured management-of-change intake and approval workflow for controlled operational changes.",
        "business_problems_json": ["manual approval routing", "untracked change requests"],
        "features_json": ["form orchestration", "approval checkpoints", "status tracking"],
        "technologies_json": ["workflow automation", "web forms", "audit trails"],
        "industries_json": ["operations", "engineering", "industrial services"],
        "keywords_json": ["moc", "change control", "approval"],
        "reusable_capabilities_json": ["workflow engine", "approval routing", "audit timeline"],
        "confidentiality_safe_summary": "Digitizes controlled change-request submission, review, and approval routing.",
    },
    {
        "category": "Workflow and approvals",
        "name": "Waiver Workflow",
        "description": "Governed waiver submission and approval process with traceable decision history.",
        "business_problems_json": ["email-based waivers", "missing decision traceability"],
        "features_json": ["workflow states", "review comments", "approval records"],
        "technologies_json": ["workflow automation", "role-based access", "notifications"],
        "industries_json": ["compliance", "operations", "enterprise services"],
        "keywords_json": ["waiver", "exception", "approval"],
        "reusable_capabilities_json": ["approval routing", "decision logging", "exception tracking"],
        "confidentiality_safe_summary": "Provides a governed exception and waiver approval workflow with clear accountability.",
    },
    {
        "category": "Workflow and approvals",
        "name": "Document Approval Module",
        "description": "Configurable multi-step document review and approval experience for enterprise records.",
        "business_problems_json": ["slow document reviews", "approval bottlenecks"],
        "features_json": ["review queues", "approval routing", "version-aware actions"],
        "technologies_json": ["document workflows", "role controls", "status automation"],
        "industries_json": ["document control", "engineering", "compliance"],
        "keywords_json": ["document approval", "review", "workflow"],
        "reusable_capabilities_json": ["approval routing", "task queues", "status transitions"],
        "confidentiality_safe_summary": "Supports governed document review and approval with stage-aware routing.",
    },
    {
        "category": "Workflow and approvals",
        "name": "Engineering Services Request",
        "description": "Request intake and coordination workflow for engineering support services.",
        "business_problems_json": ["unstructured engineering requests", "unclear work ownership"],
        "features_json": ["request intake", "assignment tracking", "service status"],
        "technologies_json": ["work management", "forms", "dashboards"],
        "industries_json": ["engineering", "operations", "project delivery"],
        "keywords_json": ["engineering request", "service workflow", "assignment"],
        "reusable_capabilities_json": ["request intake", "assignment routing", "status dashboards"],
        "confidentiality_safe_summary": "Organizes engineering-service requests with clear intake, assignment, and tracking.",
    },
    {
        "category": "Workflow and approvals",
        "name": "Operational Excellence and Loss Prevention Compliance Review",
        "description": "Compliance review workflow for operational controls and risk prevention checkpoints.",
        "business_problems_json": ["manual compliance reviews", "inconsistent control evidence"],
        "features_json": ["review templates", "control checkpoints", "review outcomes"],
        "technologies_json": ["compliance workflows", "forms", "audit tracking"],
        "industries_json": ["operations", "risk management", "industrial services"],
        "keywords_json": ["compliance review", "loss prevention", "controls"],
        "reusable_capabilities_json": ["review workflow", "evidence capture", "outcome tracking"],
        "confidentiality_safe_summary": "Standardizes operational compliance review activities and evidence capture.",
    },
    {
        "category": "Workflow and approvals",
        "name": "ECR Application Lifecycle Manager",
        "description": "Lifecycle management for controlled change requests across review, approval, and implementation stages.",
        "business_problems_json": ["fragmented change lifecycle", "poor stage visibility"],
        "features_json": ["lifecycle stages", "approval history", "status monitoring"],
        "technologies_json": ["workflow engine", "dashboards", "audit logging"],
        "industries_json": ["engineering", "operations", "project controls"],
        "keywords_json": ["ecr", "change request", "lifecycle"],
        "reusable_capabilities_json": ["stage workflows", "approval trails", "status visibility"],
        "confidentiality_safe_summary": "Tracks the lifecycle of formal change requests from submission through closure.",
    },
    {
        "category": "Operational applications",
        "name": "Dorra Operations Readiness Software",
        "description": "Readiness-tracking application for operational launch, commissioning, or handover activities.",
        "business_problems_json": ["readiness gaps", "disconnected launch checklists"],
        "features_json": ["readiness checklists", "status dashboards", "issue visibility"],
        "technologies_json": ["operational dashboards", "workflow tracking", "reporting"],
        "industries_json": ["operations", "asset readiness", "project delivery"],
        "keywords_json": ["readiness", "operations", "checklists"],
        "reusable_capabilities_json": ["checklist tracking", "status dashboards", "issue reporting"],
        "confidentiality_safe_summary": "Improves visibility into operational readiness activities and outstanding actions.",
    },
    {
        "category": "Operational applications",
        "name": "Maintenance Task Tracker and Management System",
        "description": "Task-tracking system for recurring and corrective maintenance work.",
        "business_problems_json": ["manual maintenance tracking", "missed maintenance actions"],
        "features_json": ["task logs", "status tracking", "assignment views"],
        "technologies_json": ["work management", "dashboards", "notifications"],
        "industries_json": ["maintenance", "operations", "asset management"],
        "keywords_json": ["maintenance", "tasks", "work orders"],
        "reusable_capabilities_json": ["task tracking", "assignment routing", "status reporting"],
        "confidentiality_safe_summary": "Tracks maintenance tasks, ownership, and completion progress in one system.",
    },
    {
        "category": "Operational applications",
        "name": "Production Data Management System",
        "description": "Operational data capture and reporting surface for production performance visibility.",
        "business_problems_json": ["fragmented production data", "slow operational reporting"],
        "features_json": ["data capture", "operational reporting", "trend visibility"],
        "technologies_json": ["dashboards", "forms", "data aggregation"],
        "industries_json": ["production", "operations", "industrial services"],
        "keywords_json": ["production data", "operations reporting", "performance"],
        "reusable_capabilities_json": ["data capture", "dashboard reporting", "trend analysis"],
        "confidentiality_safe_summary": "Centralizes production reporting and operational performance visibility.",
    },
    {
        "category": "Operational applications",
        "name": "Active Contract Management",
        "description": "Operational tracker for active contract status, milestones, and accountability.",
        "business_problems_json": ["limited contract visibility", "missed contract actions"],
        "features_json": ["contract register", "milestone tracking", "status dashboards"],
        "technologies_json": ["tracking dashboards", "workflow states", "reporting"],
        "industries_json": ["commercial operations", "contracts", "enterprise services"],
        "keywords_json": ["contracts", "milestones", "tracking"],
        "reusable_capabilities_json": ["tracking registers", "status dashboards", "workflow alerts"],
        "confidentiality_safe_summary": "Provides visibility into active contract status, milestones, and follow-up needs.",
    },
    {
        "category": "Operational applications",
        "name": "Contract Employee Management",
        "description": "Administrative workflow for onboarding, tracking, and status visibility of contract workers.",
        "business_problems_json": ["manual contractor tracking", "incomplete workforce visibility"],
        "features_json": ["worker records", "status tracking", "workflow checkpoints"],
        "technologies_json": ["workflow forms", "dashboards", "record tracking"],
        "industries_json": ["workforce operations", "hr services", "enterprise administration"],
        "keywords_json": ["contract employee", "tracking", "onboarding"],
        "reusable_capabilities_json": ["record management", "workflow status", "dashboard visibility"],
        "confidentiality_safe_summary": "Helps manage contract workforce records and workflow status safely.",
    },
    {
        "category": "Operational applications",
        "name": "Follow-on Tender Tracking",
        "description": "Tracker for follow-on tender opportunities and related workflow milestones.",
        "business_problems_json": ["missed tender follow-up", "manual tender monitoring"],
        "features_json": ["opportunity tracking", "status updates", "deadline visibility"],
        "technologies_json": ["pipeline tracking", "dashboards", "alerts"],
        "industries_json": ["business development", "commercial operations", "procurement support"],
        "keywords_json": ["tender tracking", "pipeline", "deadlines"],
        "reusable_capabilities_json": ["pipeline views", "deadline tracking", "status alerts"],
        "confidentiality_safe_summary": "Tracks tender follow-up activities and key commercial milestones.",
    },
    {
        "category": "Dashboards and reports",
        "name": "ESD Manager Dashboard",
        "description": "Manager-facing dashboard for performance monitoring and action visibility.",
        "business_problems_json": ["slow management reporting", "low visibility into operational KPIs"],
        "features_json": ["kpi cards", "trend views", "status drilldowns"],
        "technologies_json": ["dashboards", "visual analytics", "reporting"],
        "industries_json": ["management reporting", "operations", "enterprise services"],
        "keywords_json": ["dashboard", "kpi", "manager"],
        "reusable_capabilities_json": ["dashboard cards", "filters", "visual analytics"],
        "confidentiality_safe_summary": "Presents management KPIs and operational indicators in a single dashboard.",
    },
    {
        "category": "Dashboards and reports",
        "name": "ELD KPI Dashboard",
        "description": "Performance dashboard focused on KPI monitoring and periodic trend visibility.",
        "business_problems_json": ["manual KPI consolidation", "limited reporting cadence"],
        "features_json": ["kpi visualization", "trend summaries", "status filtering"],
        "technologies_json": ["dashboard analytics", "reporting", "charts"],
        "industries_json": ["performance management", "operations", "enterprise services"],
        "keywords_json": ["kpi dashboard", "performance", "analytics"],
        "reusable_capabilities_json": ["kpi cards", "filters", "trend visualizations"],
        "confidentiality_safe_summary": "Consolidates KPI monitoring into a reusable dashboard experience.",
    },
    {
        "category": "Dashboards and reports",
        "name": "LFD Statistics Dashboard",
        "description": "Statistics and performance dashboard for operational reporting and trend review.",
        "business_problems_json": ["fragmented metrics", "slow statistics reporting"],
        "features_json": ["statistical summaries", "charts", "period comparisons"],
        "technologies_json": ["dashboards", "charting", "report aggregation"],
        "industries_json": ["operations reporting", "analytics", "enterprise services"],
        "keywords_json": ["statistics", "dashboard", "reporting"],
        "reusable_capabilities_json": ["dashboard charts", "summary metrics", "time filtering"],
        "confidentiality_safe_summary": "Improves access to statistical reporting and operational trend analysis.",
    },
    {
        "category": "Dashboards and reports",
        "name": "Weather Report Dashboard",
        "description": "Weather-oriented operational dashboard for monitoring and reporting conditions.",
        "business_problems_json": ["distributed weather reporting", "limited visibility into environmental conditions"],
        "features_json": ["status cards", "historical trends", "summary reporting"],
        "technologies_json": ["dashboards", "data visualization", "reporting"],
        "industries_json": ["operations", "field services", "environmental monitoring"],
        "keywords_json": ["weather", "dashboard", "monitoring"],
        "reusable_capabilities_json": ["dashboards", "trend charts", "report summaries"],
        "confidentiality_safe_summary": "Provides centralized visibility into weather-related operational reporting.",
    },
    {
        "category": "Dashboards and reports",
        "name": "Hourly Operational Report",
        "description": "Structured reporting workflow for periodic operational updates and status communication.",
        "business_problems_json": ["manual hourly reporting", "inconsistent operational updates"],
        "features_json": ["scheduled reporting forms", "summary views", "status logs"],
        "technologies_json": ["forms", "dashboards", "report workflows"],
        "industries_json": ["operations", "control rooms", "industrial services"],
        "keywords_json": ["hourly report", "operations", "status update"],
        "reusable_capabilities_json": ["report forms", "status summaries", "periodic dashboards"],
        "confidentiality_safe_summary": "Standardizes recurring operational reporting and summary communication.",
    },
    {
        "category": "Dashboards and reports",
        "name": "ECD Dashboard and CRUD Table",
        "description": "Operational dashboard paired with structured CRUD data management views.",
        "business_problems_json": ["split reporting and data maintenance", "manual data tables"],
        "features_json": ["dashboard KPIs", "editable tables", "record tracking"],
        "technologies_json": ["dashboards", "crud interfaces", "data grids"],
        "industries_json": ["operations", "administration", "enterprise services"],
        "keywords_json": ["crud", "dashboard", "records"],
        "reusable_capabilities_json": ["dashboard shell", "data grids", "record maintenance"],
        "confidentiality_safe_summary": "Combines dashboard reporting with structured record-management tables.",
    },
    {
        "category": "Inspection and environmental applications",
        "name": "Catering Inspection Report",
        "description": "Inspection workflow and reporting interface for service-quality reviews.",
        "business_problems_json": ["paper inspections", "inconsistent inspection reporting"],
        "features_json": ["inspection forms", "status scoring", "report export"],
        "technologies_json": ["mobile forms", "workflow tracking", "reports"],
        "industries_json": ["inspection", "quality assurance", "service operations"],
        "keywords_json": ["inspection", "report", "compliance"],
        "reusable_capabilities_json": ["inspection forms", "scoring", "report generation"],
        "confidentiality_safe_summary": "Digitizes inspection reporting and standardizes outcome capture.",
    },
    {
        "category": "Inspection and environmental applications",
        "name": "Indoor Air Quality Monitoring Report",
        "description": "Monitoring and reporting workflow for indoor environmental quality observations.",
        "business_problems_json": ["manual environmental reporting", "limited condition history"],
        "features_json": ["measurement logs", "status tracking", "trend reporting"],
        "technologies_json": ["monitoring dashboards", "forms", "reports"],
        "industries_json": ["environmental monitoring", "facilities", "operations"],
        "keywords_json": ["air quality", "monitoring", "report"],
        "reusable_capabilities_json": ["measurement capture", "trend charts", "report outputs"],
        "confidentiality_safe_summary": "Supports structured indoor-air-quality reporting and visibility.",
    },
    {
        "category": "Inspection and environmental applications",
        "name": "Noise Measurement Report",
        "description": "Reporting workflow for noise observations, readings, and environmental review.",
        "business_problems_json": ["scattered noise records", "manual measurement reporting"],
        "features_json": ["reading logs", "report summaries", "trend views"],
        "technologies_json": ["forms", "dashboards", "report generation"],
        "industries_json": ["environmental monitoring", "operations", "compliance"],
        "keywords_json": ["noise", "measurement", "report"],
        "reusable_capabilities_json": ["measurement forms", "reports", "trend dashboards"],
        "confidentiality_safe_summary": "Improves the consistency and traceability of noise measurement reporting.",
    },
    {
        "category": "Inspection and environmental applications",
        "name": "Crude Oil Analysis Report",
        "description": "Structured reporting interface for laboratory or analytical review results.",
        "business_problems_json": ["manual analytical reports", "poor result traceability"],
        "features_json": ["report templates", "result capture", "summary outputs"],
        "technologies_json": ["forms", "data capture", "reporting"],
        "industries_json": ["laboratory operations", "analysis", "industrial services"],
        "keywords_json": ["analysis", "report", "laboratory"],
        "reusable_capabilities_json": ["templated reporting", "result capture", "record outputs"],
        "confidentiality_safe_summary": "Standardizes analytical-report capture and reporting workflows.",
    },
    {
        "category": "Inspection and environmental applications",
        "name": "Instruments Calibration Schedule",
        "description": "Scheduling and tracking application for calibration planning and due-date visibility.",
        "business_problems_json": ["missed calibration dates", "manual schedule tracking"],
        "features_json": ["schedule register", "due-date visibility", "status filters"],
        "technologies_json": ["tracking tables", "alerts", "dashboards"],
        "industries_json": ["maintenance", "quality assurance", "laboratory operations"],
        "keywords_json": ["calibration", "schedule", "tracking"],
        "reusable_capabilities_json": ["schedule tracking", "alerts", "status dashboards"],
        "confidentiality_safe_summary": "Tracks calibration schedules and upcoming deadlines for instruments.",
    },
    {
        "category": "Inspection and environmental applications",
        "name": "Laboratory Analysis Forms",
        "description": "Digital forms for capturing laboratory workflow data and review results.",
        "business_problems_json": ["paper analysis forms", "manual result consolidation"],
        "features_json": ["form capture", "workflow checkpoints", "result records"],
        "technologies_json": ["digital forms", "record capture", "workflow status"],
        "industries_json": ["laboratory operations", "quality assurance", "testing services"],
        "keywords_json": ["laboratory forms", "analysis", "capture"],
        "reusable_capabilities_json": ["forms engine", "result capture", "workflow status"],
        "confidentiality_safe_summary": "Digitizes laboratory form workflows and improves result traceability.",
    },
    {
        "category": "Trackers and communication applications",
        "name": "ASD Correspondence Tracker",
        "description": "Structured tracker for inbound and outbound business correspondence.",
        "business_problems_json": ["untracked correspondence", "limited communication visibility"],
        "features_json": ["register views", "status tracking", "searchable records"],
        "technologies_json": ["tracking systems", "dashboards", "search"],
        "industries_json": ["administration", "communications", "enterprise services"],
        "keywords_json": ["correspondence", "tracker", "register"],
        "reusable_capabilities_json": ["tracking registers", "search", "status workflows"],
        "confidentiality_safe_summary": "Tracks correspondence status and history in a structured register.",
    },
    {
        "category": "Trackers and communication applications",
        "name": "CPD Communication Tracker",
        "description": "Communication tracking workspace for business follow-up and visibility.",
        "business_problems_json": ["missed communication follow-ups", "fragmented status tracking"],
        "features_json": ["communication logs", "status views", "search filters"],
        "technologies_json": ["tracking registers", "dashboards", "filters"],
        "industries_json": ["administration", "communications", "business operations"],
        "keywords_json": ["communication", "tracker", "follow-up"],
        "reusable_capabilities_json": ["tracking logs", "search filters", "status dashboards"],
        "confidentiality_safe_summary": "Improves communication follow-up and tracking visibility.",
    },
    {
        "category": "Trackers and communication applications",
        "name": "Incoming and Outgoing Official Correspondence Tracker",
        "description": "Central register for official inbound and outbound correspondence workflows.",
        "business_problems_json": ["split incoming and outgoing logs", "manual correspondence reporting"],
        "features_json": ["dual registers", "status monitoring", "search and filters"],
        "technologies_json": ["tracking systems", "dashboards", "record search"],
        "industries_json": ["administration", "document control", "enterprise services"],
        "keywords_json": ["official correspondence", "incoming", "outgoing"],
        "reusable_capabilities_json": ["register management", "filters", "search"],
        "confidentiality_safe_summary": "Maintains structured visibility over official correspondence flows.",
    },
    {
        "category": "Trackers and communication applications",
        "name": "Correspondence Management System",
        "description": "Broader correspondence management platform for workflow, search, and reporting.",
        "business_problems_json": ["manual correspondence lifecycle", "limited status traceability"],
        "features_json": ["record lifecycle", "searchable register", "dashboard reporting"],
        "technologies_json": ["record systems", "workflow routing", "search"],
        "industries_json": ["administration", "communications", "document services"],
        "keywords_json": ["correspondence management", "workflow", "search"],
        "reusable_capabilities_json": ["workflow tracking", "searchable registers", "status reporting"],
        "confidentiality_safe_summary": "Supports end-to-end correspondence management with traceable workflow states.",
    },
    {
        "category": "Reservation and service applications",
        "name": "Cultural Tent Reservation System",
        "description": "Reservation workflow for venue or shared-space booking requests.",
        "business_problems_json": ["manual reservation requests", "booking conflicts"],
        "features_json": ["reservation intake", "availability status", "approval workflow"],
        "technologies_json": ["booking systems", "workflow forms", "status dashboards"],
        "industries_json": ["facilities", "events", "shared services"],
        "keywords_json": ["reservation", "booking", "workflow"],
        "reusable_capabilities_json": ["request intake", "calendar-like status", "approval routing"],
        "confidentiality_safe_summary": "Digitizes reservation requests and improves booking visibility.",
    },
    {
        "category": "Reservation and service applications",
        "name": "Media and Support Services Application",
        "description": "Service-request workflow for media, support, or operational assistance needs.",
        "business_problems_json": ["unstructured support requests", "unclear service status"],
        "features_json": ["service intake", "assignment routing", "request tracking"],
        "technologies_json": ["workflow forms", "dashboards", "task tracking"],
        "industries_json": ["shared services", "support operations", "enterprise administration"],
        "keywords_json": ["service request", "support", "workflow"],
        "reusable_capabilities_json": ["request workflows", "assignment tracking", "status dashboards"],
        "confidentiality_safe_summary": "Improves visibility and routing for shared-service requests.",
    },
    {
        "category": "Reservation and service applications",
        "name": "IDEAHub Idea Submission and Reporting Platform",
        "description": "Idea intake and review platform for innovation submissions and follow-up reporting.",
        "business_problems_json": ["email-based idea capture", "poor innovation tracking"],
        "features_json": ["submission forms", "review workflows", "reporting dashboards"],
        "technologies_json": ["forms", "workflow review", "dashboards"],
        "industries_json": ["innovation management", "enterprise services", "continuous improvement"],
        "keywords_json": ["ideas", "submission", "innovation"],
        "reusable_capabilities_json": ["submission intake", "review workflow", "reporting dashboards"],
        "confidentiality_safe_summary": "Captures innovation ideas with structured review and reporting workflows.",
    },
    {
        "category": "Migration and document applications",
        "name": "Legacy Contracts Migration and Search",
        "description": "Migration and searchable access layer for legacy contract records.",
        "business_problems_json": ["hard-to-find legacy contracts", "manual contract retrieval"],
        "features_json": ["migration support", "searchable repository", "record indexing"],
        "technologies_json": ["migration utilities", "search", "document indexing"],
        "industries_json": ["document services", "contracts", "records management"],
        "keywords_json": ["migration", "contracts", "search"],
        "reusable_capabilities_json": ["migration patterns", "search interfaces", "indexed records"],
        "confidentiality_safe_summary": "Supports migration and retrieval of legacy contract information.",
    },
    {
        "category": "Migration and document applications",
        "name": "Data Migration Tool",
        "description": "General-purpose migration utility for structured business records and documents.",
        "business_problems_json": ["manual migration effort", "inconsistent migration tracking"],
        "features_json": ["mapping support", "batch processing", "status reporting"],
        "technologies_json": ["migration tooling", "batch utilities", "status dashboards"],
        "industries_json": ["data migration", "enterprise services", "system modernization"],
        "keywords_json": ["data migration", "batch", "mapping"],
        "reusable_capabilities_json": ["migration workflows", "batch processing", "status monitoring"],
        "confidentiality_safe_summary": "Provides repeatable migration utilities for structured data movement.",
    },
    {
        "category": "Migration and document applications",
        "name": "Excel Bulk Upload Utility",
        "description": "Bulk-upload utility for spreadsheet-driven record creation and updates.",
        "business_problems_json": ["manual data entry", "slow bulk record updates"],
        "features_json": ["bulk import", "validation checks", "error feedback"],
        "technologies_json": ["spreadsheet ingestion", "validation", "batch processing"],
        "industries_json": ["administration", "data operations", "enterprise services"],
        "keywords_json": ["excel", "bulk upload", "validation"],
        "reusable_capabilities_json": ["bulk import", "validation", "error reporting"],
        "confidentiality_safe_summary": "Accelerates spreadsheet-driven bulk data capture with validation support.",
    },
    {
        "category": "Migration and document applications",
        "name": "Engineering Project Document Migration",
        "description": "Migration workflow for engineering project documentation into governed repositories.",
        "business_problems_json": ["legacy document sprawl", "difficult project-document migration"],
        "features_json": ["migration tracking", "document indexing", "status reporting"],
        "technologies_json": ["migration utilities", "document indexing", "tracking dashboards"],
        "industries_json": ["engineering", "document control", "project delivery"],
        "keywords_json": ["document migration", "engineering", "indexing"],
        "reusable_capabilities_json": ["migration tracking", "document indexing", "status dashboards"],
        "confidentiality_safe_summary": "Supports controlled migration of engineering project documents.",
    },
    {
        "category": "Migration and document applications",
        "name": "OpenText API Integrations",
        "description": "Integration patterns for document-oriented enterprise systems using API-driven connectivity.",
        "business_problems_json": ["manual document exchange", "disconnected content systems"],
        "features_json": ["api connectivity", "workflow triggers", "content synchronization"],
        "technologies_json": ["api integrations", "document platforms", "workflow automation"],
        "industries_json": ["document services", "system integration", "enterprise platforms"],
        "keywords_json": ["api integration", "content systems", "automation"],
        "reusable_capabilities_json": ["api orchestration", "document workflow triggers", "sync patterns"],
        "confidentiality_safe_summary": "Demonstrates reusable integration patterns for enterprise content platforms.",
    },
    {
        "category": "Migration and document applications",
        "name": "OpenText Extended ECM for SAP ERP",
        "description": "Enterprise content integration pattern aligned to ERP-adjacent document workflows.",
        "business_problems_json": ["separated content and erp records", "manual supporting-document handling"],
        "features_json": ["content linkage", "workflow visibility", "document access"],
        "technologies_json": ["enterprise content integration", "workflow linking", "document access"],
        "industries_json": ["enterprise systems", "document services", "process operations"],
        "keywords_json": ["ecm", "erp", "integration"],
        "reusable_capabilities_json": ["content linkage", "workflow integration", "document access patterns"],
        "confidentiality_safe_summary": "Represents document-integration experience for ERP-adjacent workflows.",
    },
    {
        "category": "Migration and document applications",
        "name": "OpenText Extended ECM for SAP SRM",
        "description": "Enterprise content integration pattern aligned to sourcing or supplier-related workflows.",
        "business_problems_json": ["disconnected sourcing content", "manual document retrieval"],
        "features_json": ["content linkage", "workflow support", "document accessibility"],
        "technologies_json": ["enterprise content integration", "workflow support", "document access"],
        "industries_json": ["enterprise systems", "sourcing support", "document services"],
        "keywords_json": ["ecm", "srm", "integration"],
        "reusable_capabilities_json": ["content linkage", "workflow support", "document access patterns"],
        "confidentiality_safe_summary": "Captures reusable document-integration experience for sourcing-related workflows.",
    },
]


def _merge_unique(values: list[str], required: list[str]) -> list[str]:
    return list(dict.fromkeys([*values, *required]))


def _ensure_experience_catalogue(db):
    tenants = db.query(Tenant).all()
    for tenant in tenants:
        for item in EXPERIENCE_CATALOGUE_ITEMS:
            existing = (
                db.query(BusinessDevelopmentExperienceItem)
                .filter(
                    BusinessDevelopmentExperienceItem.tenant_id == tenant.tenant_id,
                    BusinessDevelopmentExperienceItem.name == item["name"],
                )
                .first()
            )

            if not existing:
                existing = BusinessDevelopmentExperienceItem(
                    id=f"BD-EXP-{str(uuid4())[:12].upper()}",
                    tenant_id=tenant.tenant_id,
                    created_by="seed_saas_data",
                )
                db.add(existing)

            existing.category = item["category"]
            existing.name = item["name"]
            existing.description = item["description"]
            existing.business_problems_json = item["business_problems_json"]
            existing.features_json = item["features_json"]
            existing.technologies_json = item["technologies_json"]
            existing.industries_json = item["industries_json"]
            existing.keywords_json = item["keywords_json"]
            existing.reusable_capabilities_json = item["reusable_capabilities_json"]
            existing.confidentiality_safe_summary = item["confidentiality_safe_summary"]
            existing.status = "active"


def seed():
    db = SessionLocal()

    try:
        plan_definitions = [
            {
                "plan_id": "PLAN-STARTER",
                "plan_name": "Starter",
                "price_monthly": 500,
                "currency": "INR",
                "max_users": 5,
                "max_documents": 100,
                "max_storage_mb": 500,
                "monthly_ai_tokens": 100000,
                "allowed_modules": ["dashboard", "copilot", "documents"],
                "features": ["AI Copilot", "Document Intelligence", "Executive Dashboard"],
            },
            {
                "plan_id": "PLAN-PROFESSIONAL",
                "plan_name": "Professional",
                "price_monthly": 2500,
                "currency": "INR",
                "max_users": 25,
                "max_documents": 1000,
                "max_storage_mb": 5120,
                "monthly_ai_tokens": 1000000,
                "allowed_modules": ["dashboard", "copilot", "documents", "escalations"],
                "features": ["Business Area Intelligence", "Escalation Intelligence"],
            },
            {
                "plan_id": "PLAN-ENTERPRISE",
                "plan_name": "Enterprise",
                "price_monthly": 0,
                "currency": "INR",
                "max_users": 9999,
                "max_documents": 999999,
                "max_storage_mb": 102400,
                "monthly_ai_tokens": 99999999,
                "allowed_modules": [
                    "dashboard",
                    "copilot",
                    "documents",
                    "escalations",
                    AUGMIS_BUSINESS_MODULE,
                    "settings",
                ],
                "features": [
                    "All Modules",
                    "Advanced Governance",
                    "Custom Billing",
                    "Dedicated Support",
                ],
            },
        ]

        for definition in plan_definitions:
            plan = db.query(Plan).filter(Plan.plan_id == definition["plan_id"]).first()
            if not plan:
                plan = Plan(plan_id=definition["plan_id"])
                db.add(plan)

            plan.plan_name = definition["plan_name"]
            plan.price_monthly = definition["price_monthly"]
            plan.currency = definition["currency"]
            plan.max_users = definition["max_users"]
            plan.max_documents = definition["max_documents"]
            plan.max_storage_mb = definition["max_storage_mb"]
            plan.monthly_ai_tokens = definition["monthly_ai_tokens"]
            plan.allowed_modules = definition["allowed_modules"]
            plan.features = definition["features"]

        if not db.query(Tenant).filter(Tenant.tenant_id == "TENANT-001").first():
            db.add(
                Tenant(
                    tenant_id="TENANT-001",
                    tenant_name="Infomentica Demo Tenant",
                    status="ACTIVE",
                    plan_id="PLAN-ENTERPRISE",
                    subscription_status="ACTIVE",
                    billing_status="PAID",
                    subscription_start="2026-06-01",
                    subscription_end="2026-07-01",
                )
            )

        if not db.query(Tenant).filter(Tenant.tenant_id == "AUGMIS-PLATFORM").first():
            db.add(
                Tenant(
                    tenant_id="AUGMIS-PLATFORM",
                    tenant_name="AUGMIS Platform",
                    status="ACTIVE",
                    plan_id="PLAN-ENTERPRISE",
                    subscription_status="ACTIVE",
                    billing_status="PAID",
                    subscription_start="2026-06-01",
                    subscription_end="2027-06-01",
                )
            )

        tenant_admin = db.query(User).filter(User.email == "admin@infomentica.com").first()
        if not tenant_admin:
            tenant_admin = User(
                user_id="USR-0001",
                email="admin@infomentica.com",
                password_hash="$2b$12$IBxtGX7IWuBL52l6gprpYu1eezAZuFqbLvfl1KTOWpDCvsytGED6y",
            )
            db.add(tenant_admin)
        tenant_admin.tenant_id = "TENANT-001"
        tenant_admin.tenant_name = "Infomentica Demo Tenant"
        tenant_admin.name = "Tenant Admin"
        tenant_admin.role = "TENANT_ADMIN"
        tenant_admin.status = "ACTIVE"
        tenant_admin.allowed_modules = _merge_unique(
            tenant_admin.allowed_modules or [],
            ["dashboard", "copilot", "documents", "escalations", AUGMIS_BUSINESS_MODULE, "settings"],
        )
        tenant_admin.permissions = _merge_unique(
            tenant_admin.permissions or [],
            [
                "dashboard:view",
                "copilot:use",
                "documents:read",
                "documents:upload",
                "escalation:read",
                "escalation:manage",
                *AUGMIS_BUSINESS_PERMISSIONS,
                "admin:users",
                "admin:settings",
            ],
        )

        super_admin = db.query(User).filter(User.email == "superadmin@augmis.com").first()
        if not super_admin:
            super_admin = User(
                user_id="USR-AUGMIS-0001",
                email="superadmin@augmis.com",
                password_hash="$2b$12$IBxtGX7IWuBL52l6gprpYu1eezAZuFqbLvfl1KTOWpDCvsytGED6y",
            )
            db.add(super_admin)
        super_admin.tenant_id = "AUGMIS-PLATFORM"
        super_admin.tenant_name = "AUGMIS Platform"
        super_admin.name = "AUGMIS Super Admin"
        super_admin.role = "SUPER_ADMIN"
        super_admin.status = "ACTIVE"
        super_admin.allowed_modules = _merge_unique(
            super_admin.allowed_modules or [],
            ["dashboard", "copilot", "documents", "escalations", AUGMIS_BUSINESS_MODULE, "settings"],
        )
        super_admin.permissions = _merge_unique(
            super_admin.permissions or [],
            [
                "dashboard:view",
                "copilot:use",
                "documents:read",
                "documents:upload",
                "escalation:read",
                "escalation:manage",
                *AUGMIS_BUSINESS_PERMISSIONS,
                "admin:users",
                "admin:settings",
            ],
        )

        if not db.query(TenantUsage).filter(
            TenantUsage.tenant_id == "TENANT-001",
            TenantUsage.period == date.today().strftime("%Y-%m"),
        ).first():
            db.add(
                TenantUsage(
                    usage_id=f"USAGE-{str(uuid4())[:8].upper()}",
                    tenant_id="TENANT-001",
                    users_count=1,
                    documents_count=0,
                    storage_used_mb=0,
                    ai_tokens_used=0,
                    period=date.today().strftime("%Y-%m"),
                )
            )
        _ensure_experience_catalogue(db)
        db.commit()
        print("SaaS seed data created successfully.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
