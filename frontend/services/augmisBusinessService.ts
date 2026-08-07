import apiClient from "./apiClient";

export type AugmisBusinessOpportunity = {
  id: string;
  external_id: string | null;
  source_type: string;
  source_name: string;
  source_url: string | null;
  title: string;
  organization_name: string;
  organization_domain: string | null;
  country: string | null;
  region: string | null;
  industry: string | null;
  published_at: string | null;
  closing_at: string | null;
  raw_summary: string | null;
  requirement_summary: string;
  business_problem: string | null;
  expected_deliverables_json: string[];
  required_technologies_json: string[];
  published_budget: number | null;
  published_currency: string | null;
  estimated_value_min: number | null;
  estimated_value_max: number | null;
  estimated_currency: string | null;
  fit_score: number | null;
  confidence_score: number | null;
  ai_recommendation: string | null;
  opportunity_status: string;
  source_evidence_json: Array<Record<string, string>>;
  created_by: string | null;
  created_at: string | null;
  updated_at: string | null;
};

export type AugmisBusinessExperienceItem = {
  id: string;
  tenant_id: string;
  name: string;
  category: string;
  description: string;
  business_problems_json: string[];
  features_json: string[];
  technologies_json: string[];
  industries_json: string[];
  keywords_json: string[];
  reusable_capabilities_json: string[];
  confidentiality_safe_summary: string;
  status: string;
  created_by: string | null;
  created_at: string | null;
  updated_at: string | null;
};

export type AugmisBusinessRequirementBudgetInfo = {
  value: number | null;
  currency: string | null;
  source_supported: boolean;
};

export type AugmisBusinessRequirementExtractionResult = {
  requirement_summary: string;
  business_problem: string;
  required_deliverables: string[];
  required_technologies: string[];
  functional_requirements: string[];
  non_functional_requirements: string[];
  timeline_constraints: string[];
  eligibility_constraints: string[];
  budget_information: AugmisBusinessRequirementBudgetInfo;
  missing_information: string[];
  source_evidence: string[];
  confidence: number;
};

export type AugmisBusinessQualificationComponentScore = {
  score: number;
  explanation: string;
};

export type AugmisBusinessDeliveryFeasibilityResult = {
  delivery_model: "solo" | "solo_with_support" | "small_team" | "partner_required";
  reasoning: string;
  complexity_score: number;
  estimated_delivery_weeks: number | null;
  key_delivery_risks: string[];
};

export type AugmisBusinessQualificationResult = {
  experience_relevance: AugmisBusinessQualificationComponentScore;
  technology_match: AugmisBusinessQualificationComponentScore;
  budget_attractiveness: AugmisBusinessQualificationComponentScore;
  delivery_feasibility: AugmisBusinessQualificationComponentScore;
  buyer_accessibility: AugmisBusinessQualificationComponentScore;
  deadline_feasibility: AugmisBusinessQualificationComponentScore;
  market_payment_risk: AugmisBusinessQualificationComponentScore;
  delivery_profile: AugmisBusinessDeliveryFeasibilityResult;
  recommendation: string;
  explanation: string;
  risks: string[];
  missing_information: string[];
  confidence: number;
};

export type AugmisBusinessBuyerRoleRecommendation = {
  role: string;
  reason: string;
  confidence: number;
};

export type AugmisBusinessBuyerRolesResult = {
  economic_buyer: AugmisBusinessBuyerRoleRecommendation;
  operational_owner: AugmisBusinessBuyerRoleRecommendation;
  technical_evaluator: AugmisBusinessBuyerRoleRecommendation;
  procurement_contact: AugmisBusinessBuyerRoleRecommendation;
};

export type AugmisBusinessOpportunityExperienceMatch = {
  experience_item_id: string;
  name: string;
  category: string;
  match_score: number;
  matching_capabilities: string[];
  matching_technologies: string[];
  business_problem_similarity: string;
  explanation: string;
};

export type AugmisBusinessOpportunityAIAssessmentSummary = {
  id: string;
  opportunity_id: string;
  assessment_version: number;
  provider: string;
  model: string;
  prompt_bundle_version: string;
  final_fit_score: number | null;
  confidence_score: number | null;
  recommendation: string | null;
  created_at: string | null;
};

export type AugmisBusinessOpportunityAIAssessment =
  AugmisBusinessOpportunityAIAssessmentSummary & {
    requirement_extraction_json: AugmisBusinessRequirementExtractionResult;
    qualification_json: AugmisBusinessQualificationResult;
    buyer_roles_json: AugmisBusinessBuyerRolesResult;
    risks_json: string[];
    missing_information_json: string[];
    experience_matches: AugmisBusinessOpportunityExperienceMatch[];
    ai_run_summary_json: Record<string, unknown>;
  };

export type AugmisBusinessOutreachType =
  | "initial_email"
  | "linkedin_message"
  | "executive_intro"
  | "follow_up_email"
  | "procurement_clarification";

export type AugmisBusinessGenerationTone =
  | "concise"
  | "consultative"
  | "executive"
  | "technical"
  | "procurement";

export type AugmisBusinessGenerationStatus =
  | "draft"
  | "reviewed"
  | "approved"
  | "rejected"
  | "superseded";

export type AugmisBusinessOutreachTargetSummary = {
  organization_name: string;
  contact_name: string | null;
  contact_job_title: string | null;
  buyer_role: string | null;
  department: string | null;
  verification_status: string | null;
  contact_verification_notice: string | null;
};

export type AugmisBusinessOutreachContent = {
  subject_options: string[];
  recommended_subject: string | null;
  opening: string;
  body: string;
  call_to_action: string;
  full_message: string;
  personalization_points: string[];
  claims_used: string[];
  facts_requiring_verification: string[];
  tone: AugmisBusinessGenerationTone;
  uses_named_contact: boolean;
  contact_name_used: string | null;
};

export type AugmisBusinessOutreachGenerationResult = {
  outreach_type: AugmisBusinessOutreachType;
  target_summary: AugmisBusinessOutreachTargetSummary;
  content: AugmisBusinessOutreachContent;
};

export type AugmisBusinessOutreachDraftSummary = {
  id: string;
  opportunity_id: string;
  lead_id: string | null;
  prospect_id: string | null;
  contact_id: string | null;
  outreach_type: AugmisBusinessOutreachType;
  tone: AugmisBusinessGenerationTone;
  subject: string | null;
  generation_version: number;
  provider: string;
  model: string;
  prompt_bundle_version: string;
  status: AugmisBusinessGenerationStatus;
  created_by: string | null;
  created_at: string | null;
  updated_at: string | null;
};

export type AugmisBusinessOutreachDraft = AugmisBusinessOutreachDraftSummary & {
  body: string;
  structured_content_json: AugmisBusinessOutreachGenerationResult;
};

export type AugmisBusinessDiscoveryQuestion = {
  question: string;
  category: string;
  priority: "high" | "medium" | "low";
  why_it_matters: string;
};

export type AugmisBusinessMiniSolutionModule = {
  name: string;
  purpose: string;
  key_features: string[];
};

export type AugmisBusinessMiniSolutionExperienceReference = {
  experience_item_id: string;
  name: string;
  category: string;
  relevant_capabilities: string[];
  matching_technologies: string[];
  safe_summary: string;
};

export type AugmisBusinessMiniSolutionEstimatedDelivery = {
  weeks_min: number | null;
  weeks_max: number | null;
  confidence: number;
  assumptions: string[];
};

export type AugmisBusinessMiniSolutionContent = {
  title: string;
  executive_summary: string;
  problem_understanding: string;
  proposed_solution: string;
  solution_modules: AugmisBusinessMiniSolutionModule[];
  suggested_workflow: string[];
  suggested_user_roles: string[];
  suggested_technology_stack: string[];
  integration_points: string[];
  delivery_approach: string[];
  estimated_delivery: AugmisBusinessMiniSolutionEstimatedDelivery;
  experience_references: AugmisBusinessMiniSolutionExperienceReference[];
  risks: string[];
  assumptions: string[];
  open_questions: string[];
  discovery_questions: AugmisBusinessDiscoveryQuestion[];
  next_step: string;
};

export type AugmisBusinessMiniSolutionSummary = {
  id: string;
  opportunity_id: string;
  lead_id: string | null;
  assessment_id: string | null;
  title: string;
  generation_version: number;
  provider: string;
  model: string;
  prompt_bundle_version: string;
  status: AugmisBusinessGenerationStatus;
  created_by: string | null;
  created_at: string | null;
  updated_at: string | null;
};

export type AugmisBusinessMiniSolution = AugmisBusinessMiniSolutionSummary & {
  solution_json: AugmisBusinessMiniSolutionContent;
};

export type AugmisBusinessContact = {
  id: string;
  tenant_id: string;
  prospect_id: string;
  full_name: string | null;
  email: string | null;
  phone: string | null;
  job_title: string | null;
  department: string | null;
  buyer_role: string | null;
  linkedin_url: string | null;
  company_profile_url: string | null;
  contact_source: string | null;
  source_url: string | null;
  evidence_text: string | null;
  verification_status: string;
  confidence_score: number | null;
  contact_status: string;
  is_primary: boolean;
  notes: string | null;
  created_by: string | null;
  created_at: string | null;
  updated_at: string | null;
};

export type AugmisBusinessProspect = {
  id: string;
  tenant_id: string;
  organization_name: string;
  organization_domain: string | null;
  website_url: string | null;
  country: string | null;
  region: string | null;
  city: string | null;
  industry: string | null;
  organization_type: string | null;
  employee_range: string | null;
  general_email: string | null;
  general_phone: string | null;
  prospect_status: string;
  estimated_account_potential_min: number | null;
  estimated_account_potential_max: number | null;
  estimated_currency: string | null;
  notes: string | null;
  source_opportunity_id: string | null;
  created_by: string | null;
  created_at: string | null;
  updated_at: string | null;
  contacts?: AugmisBusinessContact[];
};

export type AugmisBusinessProspectOpportunity = {
  id: string;
  title: string;
  organization_name: string;
  source_type: string;
  source_name: string;
  country: string | null;
  region: string | null;
  industry: string | null;
  opportunity_status: string;
  estimated_value_min: number | null;
  estimated_value_max: number | null;
  estimated_currency: string | null;
  closing_at: string | null;
  updated_at: string | null;
};

export type AugmisBusinessProspectLead = {
  id: string;
  title: string;
  lead_stage: string;
  lead_status: string;
  priority: string;
  opportunity_id: string;
  opportunity_title: string | null;
  estimated_value: number | null;
  estimated_currency: string | null;
  probability_pct: number | null;
  next_action: string | null;
  next_action_due_at: string | null;
  created_at: string | null;
  updated_at: string | null;
};

export type AugmisBusinessProspectActivity = {
  id: string;
  activity_type: string;
  activity_summary: string;
  activity_details_json: {
    description: string | null;
    direction: string | null;
    outcome: string | null;
    metadata_json: Record<string, unknown>;
  };
  performed_by: string | null;
  created_at: string | null;
};

export type AugmisBusinessActivity = {
  id: string;
  tenant_id: string;
  lead_id: string | null;
  opportunity_id: string | null;
  prospect_id: string | null;
  contact_id: string | null;
  activity_type: string;
  subject: string;
  description: string | null;
  activity_at: string | null;
  direction: string | null;
  outcome: string | null;
  metadata_json: Record<string, unknown>;
  created_by: string | null;
  created_at: string | null;
  updated_at: string | null;
};

export type AugmisBusinessLeadExperienceMatch = {
  id: string;
  tenant_id: string;
  lead_id: string;
  experience_item_id: string;
  relevance_score: number | null;
  match_notes: string | null;
  created_by: string | null;
  created_at: string | null;
  updated_at: string | null;
};

export type AugmisBusinessLead = {
  id: string;
  tenant_id: string;
  opportunity_id: string;
  prospect_id: string;
  primary_contact_id: string | null;
  title: string;
  lead_stage: string;
  lead_status: string;
  priority: string;
  source_type: string | null;
  source_name: string | null;
  estimated_value: number | null;
  weighted_value: number | null;
  probability_pct: number | null;
  notes: string | null;
  converted_at: string | null;
  created_by: string | null;
  created_at: string | null;
  updated_at: string | null;
  prospect: AugmisBusinessProspect | null;
  primary_contact: AugmisBusinessContact | null;
  opportunity: AugmisBusinessOpportunity | null;
  experience_matches: AugmisBusinessLeadExperienceMatch[];
};

export type AugmisBusinessTask = {
  id: string;
  tenant_id: string;
  lead_id: string;
  opportunity_id: string | null;
  prospect_id: string | null;
  assigned_user_id: string | null;
  title: string;
  description: string | null;
  task_type: string;
  task_status: string;
  priority: string;
  due_at: string | null;
  completed_at: string | null;
  completed_by: string | null;
  completion_notes: string | null;
  metadata_json: Record<string, unknown>;
  created_by: string | null;
  created_at: string | null;
  updated_at: string | null;
};

export type AugmisBusinessAssignableUser = {
  user_id: string;
  name: string;
  email: string;
  role: string;
  status: string;
};

export type AugmisBusinessSearchProfile = {
  id: string;
  tenant_id: string;
  name: string;
  enabled: boolean;
  target_regions_json: string[];
  target_countries_json: string[];
  target_industries_json: string[];
  include_keywords_json: string[];
  include_technologies_json: string[];
  include_capabilities_json: string[];
  exclude_keywords_json: string[];
  excluded_domains_json: string[];
  excluded_categories_json: string[];
  minimum_budget: number | null;
  currencies_json: string[];
  allow_budget_unknown: boolean;
  solo_feasibility_preference: string | null;
  small_team_allowed: boolean;
  max_delivery_months: number | null;
  max_age_days: number | null;
  created_by: string | null;
  created_at: string | null;
  updated_at: string | null;
};

export type AugmisBusinessConnectorMetadata = {
  connector_type: string;
  name: string;
  source_category: string;
  description: string;
  capabilities: string[];
  configuration_schema: Record<string, unknown>;
  supports_scheduled_scan: boolean;
  supports_manual_scan: boolean;
  supports_incremental_scan: boolean;
  status: string;
  is_test_connector: boolean;
  default_provider?: string;
  supported_providers?: string[];
  provider_statuses?: Record<
    string,
    {
      label: string;
      configured: boolean;
      message: string;
    }
  >;
};

export type AugmisBusinessConnector = {
  id: string;
  tenant_id: string;
  search_profile_id: string | null;
  connector_type: string;
  name: string;
  source_category: string;
  status: string;
  enabled: boolean;
  schedule_enabled: boolean;
  schedule_expression: string | null;
  configuration_json: Record<string, unknown>;
  search_criteria_json: Record<string, unknown>;
  capability_flags_json: Record<string, unknown>;
  last_scan_at: string | null;
  last_success_at: string | null;
  last_error_at: string | null;
  last_error_message: string | null;
  created_by: string | null;
  created_at: string | null;
  updated_at: string | null;
  metadata: AugmisBusinessConnectorMetadata | null;
};

export type AugmisBusinessConnectorRun = {
  id: string;
  tenant_id: string;
  connector_id: string;
  run_type: string;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  items_found: number;
  items_new: number;
  items_duplicate: number;
  items_filtered: number;
  items_failed: number;
  error_summary: string | null;
  run_metadata_json: Record<string, unknown>;
  initiated_by: string | null;
  created_at: string | null;
};

export type AugmisBusinessConnectorCredentialStatus = {
  provider: string;
  credential_type: string;
  configured: boolean;
  credential_source: "tenant_secret" | "environment" | "none" | "transient";
  masked_hint: string | null;
  last_updated_at: string | null;
  last_tested_at: string | null;
  last_test_status: string | null;
  last_test_error: string | null;
  storage_available: boolean;
  storage_message: string | null;
};

export type AugmisBusinessDiscovery = {
  id: string;
  tenant_id: string;
  connector_id: string;
  connector_run_id: string | null;
  external_id: string | null;
  source_type: string;
  source_name: string;
  source_url: string | null;
  canonical_source_url: string | null;
  source_domain: string | null;
  source_country: string | null;
  title: string;
  normalized_title: string;
  organization_name: string | null;
  normalized_organization_name: string | null;
  published_date: string | null;
  closing_date: string | null;
  raw_summary: string | null;
  requirement_summary: string | null;
  raw_content_json: Record<string, unknown>;
  raw_text: string | null;
  country: string | null;
  region: string | null;
  industry: string | null;
  budget_min: number | null;
  budget_max: number | null;
  currency: string | null;
  discovered_at: string | null;
  retrieval_timestamp: string | null;
  discovery_status: string;
  duplicate_of_discovery_id: string | null;
  possible_duplicate_of_discovery_id: string | null;
  imported_opportunity_id: string | null;
  preliminary_relevance_score: number | null;
  relevance_reasons_json: string[];
  matched_keywords_json: string[];
  evidence_json: Array<Record<string, unknown>>;
  normalized_search_text: string | null;
  url_fingerprint: string | null;
  composite_fingerprint: string | null;
  created_at: string | null;
  updated_at: string | null;
};

export type ConnectorListSummary = {
  active_connectors: number;
  last_scan: string | null;
  discoveries_today: number;
  new_discoveries: number;
  failed_runs: number;
};

export type DiscoveryListParams = {
  page?: number;
  page_size?: number;
  search?: string;
  status?: string;
  connector_id?: string;
  source_category?: string;
  country?: string;
  minimum_score?: number;
};

export type CreateAugmisBusinessSearchProfilePayload = Omit<
  AugmisBusinessSearchProfile,
  "id" | "tenant_id" | "created_by" | "created_at" | "updated_at"
>;

export type UpdateAugmisBusinessSearchProfilePayload = Partial<CreateAugmisBusinessSearchProfilePayload>;

export type CreateAugmisBusinessConnectorPayload = {
  name: string;
  connector_type: string;
  source_category: string;
  enabled?: boolean;
  schedule_enabled?: boolean;
  schedule_expression?: string | null;
  configuration_json?: Record<string, unknown>;
  search_criteria_json?: Record<string, unknown>;
  capability_flags_json?: Record<string, unknown>;
  search_profile_id?: string | null;
};

export type UpdateAugmisBusinessConnectorPayload = Partial<CreateAugmisBusinessConnectorPayload> & {
  status?: string | null;
};

export type UpdateAugmisBusinessDiscoveryPayload = {
  discovery_status?: string | null;
  requirement_summary?: string | null;
  country?: string | null;
  region?: string | null;
  industry?: string | null;
  budget_min?: number | null;
  budget_max?: number | null;
  currency?: string | null;
};

export type OpportunityListParams = {
  page?: number;
  page_size?: number;
  search?: string;
  status?: string;
  source_type?: string;
  country?: string;
  region?: string;
  organization?: string;
  sort_by?: string;
  sort_order?: "asc" | "desc";
};

export type ProspectListParams = {
  page?: number;
  page_size?: number;
  search?: string;
  status?: string;
};

export type LeadListParams = {
  page?: number;
  page_size?: number;
  search?: string;
  stage?: string;
  status?: string;
  prospect_id?: string;
  opportunity_id?: string;
};

export type TaskListParams = {
  page?: number;
  page_size?: number;
  search?: string;
  status?: string;
  priority?: string;
  lead_id?: string;
};

export type CreateAugmisBusinessProspectPayload = {
  organization_name: string;
  organization_domain?: string | null;
  website_url?: string | null;
  country?: string | null;
  region?: string | null;
  city?: string | null;
  industry?: string | null;
  organization_type?: string | null;
  employee_range?: string | null;
  general_email?: string | null;
  general_phone?: string | null;
  prospect_status?: string;
  estimated_account_potential_min?: number | null;
  estimated_account_potential_max?: number | null;
  estimated_currency?: string | null;
  notes?: string | null;
  source_opportunity_id?: string | null;
};

export type CreateAugmisBusinessContactPayload = {
  full_name?: string | null;
  email?: string | null;
  phone?: string | null;
  job_title?: string | null;
  department?: string | null;
  buyer_role?: string | null;
  linkedin_url?: string | null;
  company_profile_url?: string | null;
  contact_source?: string | null;
  source_url?: string | null;
  evidence_text?: string | null;
  verification_status?: string;
  confidence_score?: number | null;
  contact_status?: string;
  is_primary?: boolean;
  notes?: string | null;
};

export type CreateAugmisBusinessOpportunityPayload = {
  external_id?: string | null;
  source_type: string;
  source_name: string;
  source_url?: string | null;
  title: string;
  organization_name: string;
  organization_domain?: string | null;
  country?: string | null;
  region?: string | null;
  industry?: string | null;
  published_at?: string | null;
  closing_at?: string | null;
  raw_summary?: string | null;
  requirement_summary: string;
  business_problem?: string | null;
  expected_deliverables_json?: string[];
  required_technologies_json?: string[];
  published_budget?: number | null;
  published_currency?: string | null;
  estimated_value_min?: number | null;
  estimated_value_max?: number | null;
  estimated_currency?: string | null;
  fit_score?: number | null;
  confidence_score?: number | null;
  ai_recommendation?: string | null;
  opportunity_status: string;
  source_evidence_json?: Array<Record<string, string>>;
};

export type BuildLeadExperienceMatchPayload = {
  experience_item_id: string;
  relevance_score?: number | null;
  match_notes?: string | null;
};

export type BuildLeadPayload = {
  contact_id?: string | null;
  contact_name?: string | null;
  contact_email?: string | null;
  contact_phone?: string | null;
  contact_job_title?: string | null;
  lead_title?: string | null;
  lead_priority: string;
  lead_stage: string;
  lead_notes?: string | null;
  probability_pct?: number | null;
  selected_experience_matches?: BuildLeadExperienceMatchPayload[];
  first_task_title?: string | null;
  first_task_description?: string | null;
  first_task_priority: string;
  first_task_due_at?: string | null;
  assigned_user_id?: string | null;
};

export type GenerateAugmisBusinessOutreachPayload = {
  outreach_type: AugmisBusinessOutreachType;
  tone: AugmisBusinessGenerationTone;
  lead_id?: string | null;
  prospect_id?: string | null;
  contact_id?: string | null;
};

export type UpdateAugmisBusinessOutreachPayload = {
  subject?: string | null;
  body?: string | null;
  structured_content_json?: AugmisBusinessOutreachGenerationResult;
  status?: AugmisBusinessGenerationStatus;
};

export type GenerateAugmisBusinessMiniSolutionPayload = {
  lead_id?: string | null;
  tone?: AugmisBusinessGenerationTone;
};

export type UpdateAugmisBusinessMiniSolutionPayload = {
  title?: string | null;
  solution_json?: AugmisBusinessMiniSolutionContent;
  status?: AugmisBusinessGenerationStatus;
};

export type AugmisBusinessStatusActionPayload = {
  notes?: string | null;
};

export type UpdateAugmisBusinessLeadPayload = {
  title?: string | null;
  primary_contact_id?: string | null;
  priority?: string | null;
  lead_status?: string | null;
  estimated_value?: number | null;
  probability_pct?: number | null;
  notes?: string | null;
};

export type UpdateAugmisBusinessLeadStagePayload = {
  lead_stage: string;
};

export type CreateAugmisBusinessLeadActivityPayload = {
  activity_type: string;
  subject: string;
  description?: string | null;
  activity_at?: string | null;
  direction?: string | null;
  outcome?: string | null;
  contact_id?: string | null;
  metadata_json?: Record<string, string | number | boolean | null>;
};

export type CreateAugmisBusinessTaskPayload = {
  lead_id: string;
  opportunity_id?: string | null;
  prospect_id?: string | null;
  assigned_user_id?: string | null;
  title: string;
  description?: string | null;
  task_type?: string;
  priority?: string;
  due_at?: string | null;
  metadata_json?: Record<string, string | number | boolean | null>;
};

export type UpdateAugmisBusinessTaskPayload = {
  assigned_user_id?: string | null;
  title?: string | null;
  description?: string | null;
  task_type?: string | null;
  task_status?: string | null;
  priority?: string | null;
  due_at?: string | null;
  metadata_json?: Record<string, string | number | boolean | null> | null;
};

export type CompleteAugmisBusinessTaskPayload = {
  completion_notes?: string | null;
};

export type AugmisBusinessReplyChannel =
  | "email"
  | "linkedin"
  | "phone_summary"
  | "meeting_note"
  | "website_message"
  | "procurement_portal"
  | "other";

export type AugmisBusinessReplyStatus =
  | "received"
  | "analyzed"
  | "action_required"
  | "responded"
  | "archived";

export type AugmisBusinessReplyIntent =
  | "interested"
  | "needs_more_information"
  | "meeting_requested"
  | "demo_requested"
  | "proposal_requested"
  | "pricing_requested"
  | "technical_questions"
  | "procurement_process"
  | "legal_compliance"
  | "objection"
  | "defer"
  | "not_interested"
  | "wrong_contact"
  | "referral"
  | "out_of_office"
  | "neutral"
  | "unclear";

export type AugmisBusinessReplySentiment =
  | "positive"
  | "neutral"
  | "negative"
  | "mixed"
  | "unclear";

export type AugmisBusinessReplyEngagementLevel =
  | "high"
  | "medium"
  | "low"
  | "none"
  | "unclear";

export type AugmisBusinessReplyUrgency = "urgent" | "high" | "normal" | "low";

export type AugmisBusinessReplyResponseStrategy =
  | "concise"
  | "consultative"
  | "technical"
  | "executive"
  | "objection_handling"
  | "procurement";

export type AugmisBusinessReplyObjection = {
  category: string;
  concern: string;
  evidence: string;
  suggested_response_approach: string;
};

export type AugmisBusinessReplyRecommendedTask = {
  title: string;
  task_type: string;
  priority: "high" | "medium" | "low";
  due_in_days: number | null;
  reason: string;
};

export type AugmisBusinessReplyAnalysisResult = {
  intent: AugmisBusinessReplyIntent;
  sentiment: AugmisBusinessReplySentiment;
  engagement_level: AugmisBusinessReplyEngagementLevel;
  urgency: AugmisBusinessReplyUrgency;
  summary: string;
  key_points: string[];
  questions_from_prospect: string[];
  objections: AugmisBusinessReplyObjection[];
  buying_signals: string[];
  risks: string[];
  requested_actions: string[];
  recommended_next_action: string;
  recommended_pipeline_stage: string | null;
  recommended_probability: number | null;
  recommended_task: AugmisBusinessReplyRecommendedTask | null;
  response_strategy: AugmisBusinessReplyResponseStrategy;
  confidence: number;
};

export type AugmisBusinessReplyAnalysisSummary = {
  id: string;
  reply_id: string;
  analysis_version: number;
  provider: string;
  model: string;
  prompt_bundle_version: string;
  intent: AugmisBusinessReplyIntent;
  sentiment: AugmisBusinessReplySentiment;
  engagement_level: AugmisBusinessReplyEngagementLevel;
  urgency: AugmisBusinessReplyUrgency;
  objection_category: string | null;
  recommended_pipeline_stage: string | null;
  recommended_next_action: string;
  confidence_score: number;
  created_by: string | null;
  created_at: string | null;
};

export type AugmisBusinessReplyAnalysis = AugmisBusinessReplyAnalysisSummary & {
  analysis_json: AugmisBusinessReplyAnalysisResult;
};

export type AugmisBusinessReply = {
  id: string;
  opportunity_id: string | null;
  lead_id: string;
  prospect_id: string | null;
  contact_id: string | null;
  outreach_id: string | null;
  channel: AugmisBusinessReplyChannel;
  subject: string | null;
  raw_message: string;
  sender_display: string | null;
  received_at: string | null;
  reply_status: AugmisBusinessReplyStatus;
  notes: string | null;
  created_by: string | null;
  created_at: string | null;
  updated_at: string | null;
  lead_title: string | null;
  prospect_name: string | null;
  contact_name: string | null;
  latest_intent: AugmisBusinessReplyIntent | null;
  latest_engagement_level: AugmisBusinessReplyEngagementLevel | null;
  latest_urgency: AugmisBusinessReplyUrgency | null;
  latest_sentiment: AugmisBusinessReplySentiment | null;
  latest_analysis_id: string | null;
  latest_analysis_created_at: string | null;
  latest_response_id: string | null;
  latest_response_status: AugmisBusinessGenerationStatus | null;
  latest_response_created_at: string | null;
  lead?: AugmisBusinessLead | null;
  prospect?: AugmisBusinessProspect | null;
  contact?: AugmisBusinessContact | null;
  opportunity?: AugmisBusinessOpportunity | null;
};

export type AugmisBusinessReplyResponseContent = {
  subject: string | null;
  opening: string;
  response_body: string;
  call_to_action: string;
  full_message: string;
  questions_answered: string[];
  questions_not_answered: string[];
  facts_requiring_verification: string[];
  recommended_attachments: string[];
  tone: AugmisBusinessReplyResponseStrategy;
};

export type AugmisBusinessReplyResponseDraftSummary = {
  id: string;
  reply_id: string;
  opportunity_id: string | null;
  lead_id: string;
  prospect_id: string | null;
  contact_id: string | null;
  analysis_id: string | null;
  tone: AugmisBusinessReplyResponseStrategy;
  subject: string | null;
  generation_version: number;
  provider: string;
  model: string;
  prompt_bundle_version: string;
  status: AugmisBusinessGenerationStatus;
  created_by: string | null;
  created_at: string | null;
  updated_at: string | null;
};

export type AugmisBusinessReplyResponseDraft = AugmisBusinessReplyResponseDraftSummary & {
  body: string;
  structured_content_json: AugmisBusinessReplyResponseContent;
};

export type ReplyListParams = {
  page?: number;
  page_size?: number;
  search?: string;
  status?: AugmisBusinessReplyStatus | "all";
  intent?: AugmisBusinessReplyIntent | "all";
  lead_id?: string;
};

export type CreateAugmisBusinessReplyPayload = {
  lead_id: string;
  contact_id?: string | null;
  outreach_id?: string | null;
  channel: AugmisBusinessReplyChannel;
  subject?: string | null;
  raw_message: string;
  sender_display?: string | null;
  received_at: string;
  notes?: string | null;
};

export type UpdateAugmisBusinessReplyPayload = {
  contact_id?: string | null;
  outreach_id?: string | null;
  channel?: AugmisBusinessReplyChannel;
  subject?: string | null;
  raw_message?: string | null;
  sender_display?: string | null;
  received_at?: string | null;
  reply_status?: AugmisBusinessReplyStatus;
  notes?: string | null;
};

export type GenerateAugmisBusinessReplyResponsePayload = {
  strategy: AugmisBusinessReplyResponseStrategy;
};

export type UpdateAugmisBusinessReplyResponsePayload = {
  subject?: string | null;
  body?: string | null;
  structured_content_json?: AugmisBusinessReplyResponseContent;
  status?: AugmisBusinessGenerationStatus;
};

export type AugmisBusinessDashboard = {
  open_opportunities: number;
  converted_opportunities: number;
  active_prospects: number;
  open_leads: number;
  pipeline_value: number;
  weighted_pipeline_value: number;
  tasks_due_today: number;
  overdue_tasks: number;
  opportunities_closing_soon: {
    count: number;
    items: AugmisBusinessOpportunity[];
  };
  leads_by_stage: Array<{
    lead_stage: string;
    count: number;
  }>;
  opportunities_by_source: Array<{
    source_type: string;
    count: number;
  }>;
  opportunities_by_market: Array<{
    market: string;
    count: number;
  }>;
  recent_activities: AugmisBusinessActivity[];
};

export async function getAugmisBusinessHealth() {
  const response = await apiClient.get("/api/augmis-business/health");
  return response.data;
}

export async function getAugmisBusinessDashboard() {
  const response = await apiClient.get("/api/augmis-business/dashboard");
  return response.data as {
    success: boolean;
    data: AugmisBusinessDashboard;
  };
}

export async function listAugmisBusinessOpportunities(params: OpportunityListParams = {}) {
  const response = await apiClient.get("/api/augmis-business/opportunities", { params });
  return response.data as {
    success: boolean;
    data: AugmisBusinessOpportunity[];
    pagination: {
      page: number;
      page_size: number;
      total: number;
      total_pages: number;
    };
  };
}

export async function createAugmisBusinessOpportunity(
  payload: CreateAugmisBusinessOpportunityPayload
) {
  const response = await apiClient.post("/api/augmis-business/opportunities", payload);
  return response.data as {
    success: boolean;
    data: AugmisBusinessOpportunity;
  };
}

export async function getAugmisBusinessOpportunity(opportunityId: string) {
  const response = await apiClient.get(
    `/api/augmis-business/opportunities/${encodeURIComponent(opportunityId)}`
  );
  return response.data as {
    success: boolean;
    data: AugmisBusinessOpportunity;
  };
}

export async function updateAugmisBusinessOpportunity(
  opportunityId: string,
  payload: Partial<CreateAugmisBusinessOpportunityPayload>
) {
  const response = await apiClient.patch(
    `/api/augmis-business/opportunities/${encodeURIComponent(opportunityId)}`,
    payload
  );
  return response.data as {
    success: boolean;
    data: AugmisBusinessOpportunity;
  };
}

export async function deleteAugmisBusinessOpportunity(opportunityId: string) {
  const response = await apiClient.delete(
    `/api/augmis-business/opportunities/${encodeURIComponent(opportunityId)}`
  );
  return response.data as {
    success: boolean;
    deleted: number;
    data?: {
      id: string;
      title: string;
      source_type: string;
    };
  };
}

export async function listAugmisBusinessExperienceItems(params?: {
  category?: string;
  status?: string;
}) {
  const response = await apiClient.get("/api/augmis-business/experience-items", { params });
  return response.data as {
    success: boolean;
    data: AugmisBusinessExperienceItem[];
  };
}

export async function listAugmisBusinessSearchProfiles() {
  const response = await apiClient.get("/api/augmis-business/search-profiles");
  return response.data as {
    success: boolean;
    data: AugmisBusinessSearchProfile[];
  };
}

export async function createAugmisBusinessSearchProfile(
  payload: CreateAugmisBusinessSearchProfilePayload
) {
  const response = await apiClient.post("/api/augmis-business/search-profiles", payload);
  return response.data as {
    success: boolean;
    data: AugmisBusinessSearchProfile;
  };
}

export async function updateAugmisBusinessSearchProfile(
  profileId: string,
  payload: UpdateAugmisBusinessSearchProfilePayload
) {
  const response = await apiClient.patch(
    `/api/augmis-business/search-profiles/${encodeURIComponent(profileId)}`,
    payload
  );
  return response.data as {
    success: boolean;
    data: AugmisBusinessSearchProfile;
  };
}

export async function listAugmisBusinessConnectors() {
  const response = await apiClient.get("/api/augmis-business/connectors");
  return response.data as {
    success: boolean;
    data: AugmisBusinessConnector[];
    summary: ConnectorListSummary;
  };
}

export async function createAugmisBusinessConnector(
  payload: CreateAugmisBusinessConnectorPayload
) {
  const response = await apiClient.post("/api/augmis-business/connectors", payload);
  return response.data as {
    success: boolean;
    data: AugmisBusinessConnector;
  };
}

export async function getAugmisBusinessConnector(connectorId: string) {
  const response = await apiClient.get(
    `/api/augmis-business/connectors/${encodeURIComponent(connectorId)}`
  );
  return response.data as {
    success: boolean;
    data: AugmisBusinessConnector;
  };
}

export async function updateAugmisBusinessConnector(
  connectorId: string,
  payload: UpdateAugmisBusinessConnectorPayload
) {
  const response = await apiClient.patch(
    `/api/augmis-business/connectors/${encodeURIComponent(connectorId)}`,
    payload
  );
  return response.data as {
    success: boolean;
    data: AugmisBusinessConnector;
  };
}

export async function testAugmisBusinessConnector(connectorId: string) {
  const response = await apiClient.post(
    `/api/augmis-business/connectors/${encodeURIComponent(connectorId)}/test`
  );
  return response.data as {
    success: boolean;
    data: {
      connector: AugmisBusinessConnector;
      result: {
        success: boolean;
        message: string;
      };
    };
  };
}

export async function listAugmisBusinessConnectorCredentials() {
  const response = await apiClient.get("/api/augmis-business/connector-credentials");
  return response.data as {
    success: boolean;
    data: AugmisBusinessConnectorCredentialStatus[];
  };
}

export async function getAugmisBusinessConnectorCredential(provider: string) {
  const response = await apiClient.get(
    `/api/augmis-business/connector-credentials/${encodeURIComponent(provider)}`
  );
  return response.data as {
    success: boolean;
    data: AugmisBusinessConnectorCredentialStatus;
  };
}

export async function saveAugmisBusinessConnectorCredential(
  provider: string,
  payload: { api_key: string }
) {
  const response = await apiClient.post(
    `/api/augmis-business/connector-credentials/${encodeURIComponent(provider)}`,
    payload
  );
  return response.data as {
    success: boolean;
    data: AugmisBusinessConnectorCredentialStatus;
  };
}

export async function deleteAugmisBusinessConnectorCredential(provider: string) {
  const response = await apiClient.delete(
    `/api/augmis-business/connector-credentials/${encodeURIComponent(provider)}`
  );
  return response.data as {
    success: boolean;
    deleted: number;
    data: AugmisBusinessConnectorCredentialStatus;
  };
}

export async function testAugmisBusinessConnectorCredential(
  provider: string,
  payload: { api_key?: string } = {}
) {
  const response = await apiClient.post(
    `/api/augmis-business/connector-credentials/${encodeURIComponent(provider)}/test`,
    payload
  );
  return response.data as {
    success: boolean;
    data: AugmisBusinessConnectorCredentialStatus & {
      result: {
        success: boolean;
        provider: string;
        message: string;
        result_count?: number;
      };
    };
  };
}

export async function scanAugmisBusinessConnector(
  connectorId: string,
  payload: { run_type?: string } = {}
) {
  const response = await apiClient.post(
    `/api/augmis-business/connectors/${encodeURIComponent(connectorId)}/scan`,
    payload
  );
  return response.data as {
    success: boolean;
    data: {
      connector: AugmisBusinessConnector;
      run: AugmisBusinessConnectorRun;
      discoveries: AugmisBusinessDiscovery[];
    };
  };
}

export async function listAugmisBusinessConnectorRuns(
  connectorId: string,
  params: { page?: number; page_size?: number } = {}
) {
  const response = await apiClient.get(
    `/api/augmis-business/connectors/${encodeURIComponent(connectorId)}/runs`,
    { params }
  );
  return response.data as {
    success: boolean;
    data: AugmisBusinessConnectorRun[];
    pagination: {
      page: number;
      page_size: number;
      total: number;
      total_pages: number;
    };
  };
}

export async function listAugmisBusinessDiscoveries(params: DiscoveryListParams = {}) {
  const response = await apiClient.get("/api/augmis-business/discoveries", { params });
  return response.data as {
    success: boolean;
    data: AugmisBusinessDiscovery[];
    pagination: {
      page: number;
      page_size: number;
      total: number;
      total_pages: number;
    };
  };
}

export async function getAugmisBusinessDiscovery(discoveryId: string) {
  const response = await apiClient.get(
    `/api/augmis-business/discoveries/${encodeURIComponent(discoveryId)}`
  );
  return response.data as {
    success: boolean;
    data: AugmisBusinessDiscovery;
    duplicates: AugmisBusinessDiscovery[];
  };
}

export async function updateAugmisBusinessDiscovery(
  discoveryId: string,
  payload: UpdateAugmisBusinessDiscoveryPayload
) {
  const response = await apiClient.patch(
    `/api/augmis-business/discoveries/${encodeURIComponent(discoveryId)}`,
    payload
  );
  return response.data as {
    success: boolean;
    data: AugmisBusinessDiscovery;
  };
}

export async function shortlistAugmisBusinessDiscovery(discoveryId: string) {
  const response = await apiClient.post(
    `/api/augmis-business/discoveries/${encodeURIComponent(discoveryId)}/shortlist`
  );
  return response.data as {
    success: boolean;
    data: AugmisBusinessDiscovery;
  };
}

export async function rejectAugmisBusinessDiscovery(discoveryId: string) {
  const response = await apiClient.post(
    `/api/augmis-business/discoveries/${encodeURIComponent(discoveryId)}/reject`
  );
  return response.data as {
    success: boolean;
    data: AugmisBusinessDiscovery;
  };
}

export async function importAugmisBusinessDiscovery(discoveryId: string) {
  const response = await apiClient.post(
    `/api/augmis-business/discoveries/${encodeURIComponent(discoveryId)}/import`
  );
  return response.data as {
    success: boolean;
    data: {
      discovery: AugmisBusinessDiscovery;
      opportunity: AugmisBusinessOpportunity;
    };
  };
}

export async function listAugmisBusinessDiscoveryDuplicates(discoveryId: string) {
  const response = await apiClient.get(
    `/api/augmis-business/discoveries/${encodeURIComponent(discoveryId)}/duplicates`
  );
  return response.data as {
    success: boolean;
    data: AugmisBusinessDiscovery[];
  };
}

export async function generateAugmisBusinessOpportunityOutreach(
  opportunityId: string,
  payload: GenerateAugmisBusinessOutreachPayload
) {
  const response = await apiClient.post(
    `/api/augmis-business/opportunities/${encodeURIComponent(opportunityId)}/outreach/generate`,
    payload
  );
  return response.data as {
    success: boolean;
    data: AugmisBusinessOutreachDraft;
  };
}

export async function generateAugmisBusinessLeadOutreach(
  leadId: string,
  payload: GenerateAugmisBusinessOutreachPayload
) {
  const response = await apiClient.post(
    `/api/augmis-business/leads/${encodeURIComponent(leadId)}/outreach/generate`,
    payload
  );
  return response.data as {
    success: boolean;
    data: AugmisBusinessOutreachDraft;
  };
}

export async function listAugmisBusinessOpportunityOutreach(opportunityId: string) {
  const response = await apiClient.get(
    `/api/augmis-business/opportunities/${encodeURIComponent(opportunityId)}/outreach`
  );
  return response.data as {
    success: boolean;
    data: AugmisBusinessOutreachDraftSummary[];
  };
}

export async function getAugmisBusinessOutreach(outreachId: string) {
  const response = await apiClient.get(
    `/api/augmis-business/outreach/${encodeURIComponent(outreachId)}`
  );
  return response.data as {
    success: boolean;
    data: AugmisBusinessOutreachDraft;
  };
}

export async function updateAugmisBusinessOutreach(
  outreachId: string,
  payload: UpdateAugmisBusinessOutreachPayload
) {
  const response = await apiClient.patch(
    `/api/augmis-business/outreach/${encodeURIComponent(outreachId)}`,
    payload
  );
  return response.data as {
    success: boolean;
    data: AugmisBusinessOutreachDraft;
  };
}

export async function approveAugmisBusinessOutreach(
  outreachId: string,
  payload: AugmisBusinessStatusActionPayload = {}
) {
  const response = await apiClient.post(
    `/api/augmis-business/outreach/${encodeURIComponent(outreachId)}/approve`,
    payload
  );
  return response.data as {
    success: boolean;
    data: AugmisBusinessOutreachDraft;
  };
}

export async function rejectAugmisBusinessOutreach(
  outreachId: string,
  payload: AugmisBusinessStatusActionPayload = {}
) {
  const response = await apiClient.post(
    `/api/augmis-business/outreach/${encodeURIComponent(outreachId)}/reject`,
    payload
  );
  return response.data as {
    success: boolean;
    data: AugmisBusinessOutreachDraft;
  };
}

export async function generateAugmisBusinessOpportunityMiniSolution(
  opportunityId: string,
  payload: GenerateAugmisBusinessMiniSolutionPayload = {}
) {
  const response = await apiClient.post(
    `/api/augmis-business/opportunities/${encodeURIComponent(opportunityId)}/mini-solution/generate`,
    payload
  );
  return response.data as {
    success: boolean;
    data: AugmisBusinessMiniSolution;
  };
}

export async function generateAugmisBusinessLeadMiniSolution(
  leadId: string,
  payload: GenerateAugmisBusinessMiniSolutionPayload = {}
) {
  const response = await apiClient.post(
    `/api/augmis-business/leads/${encodeURIComponent(leadId)}/mini-solution/generate`,
    payload
  );
  return response.data as {
    success: boolean;
    data: AugmisBusinessMiniSolution;
  };
}

export async function listAugmisBusinessOpportunityMiniSolutions(opportunityId: string) {
  const response = await apiClient.get(
    `/api/augmis-business/opportunities/${encodeURIComponent(opportunityId)}/mini-solutions`
  );
  return response.data as {
    success: boolean;
    data: AugmisBusinessMiniSolutionSummary[];
  };
}

export async function getAugmisBusinessMiniSolution(solutionId: string) {
  const response = await apiClient.get(
    `/api/augmis-business/mini-solutions/${encodeURIComponent(solutionId)}`
  );
  return response.data as {
    success: boolean;
    data: AugmisBusinessMiniSolution;
  };
}

export async function updateAugmisBusinessMiniSolution(
  solutionId: string,
  payload: UpdateAugmisBusinessMiniSolutionPayload
) {
  const response = await apiClient.patch(
    `/api/augmis-business/mini-solutions/${encodeURIComponent(solutionId)}`,
    payload
  );
  return response.data as {
    success: boolean;
    data: AugmisBusinessMiniSolution;
  };
}

export async function approveAugmisBusinessMiniSolution(
  solutionId: string,
  payload: AugmisBusinessStatusActionPayload = {}
) {
  const response = await apiClient.post(
    `/api/augmis-business/mini-solutions/${encodeURIComponent(solutionId)}/approve`,
    payload
  );
  return response.data as {
    success: boolean;
    data: AugmisBusinessMiniSolution;
  };
}

export async function rejectAugmisBusinessMiniSolution(
  solutionId: string,
  payload: AugmisBusinessStatusActionPayload = {}
) {
  const response = await apiClient.post(
    `/api/augmis-business/mini-solutions/${encodeURIComponent(solutionId)}/reject`,
    payload
  );
  return response.data as {
    success: boolean;
    data: AugmisBusinessMiniSolution;
  };
}

export async function runAugmisBusinessOpportunityAIAssessment(opportunityId: string) {
  const response = await apiClient.post(
    `/api/augmis-business/opportunities/${encodeURIComponent(opportunityId)}/ai-assess`
  );
  return response.data as {
    success: boolean;
    data: AugmisBusinessOpportunityAIAssessment;
  };
}

export async function getAugmisBusinessOpportunityAIAssessment(opportunityId: string) {
  const response = await apiClient.get(
    `/api/augmis-business/opportunities/${encodeURIComponent(opportunityId)}/ai-assessment`
  );
  return response.data as {
    success: boolean;
    data: AugmisBusinessOpportunityAIAssessment;
  };
}

export async function listAugmisBusinessOpportunityAIAssessments(opportunityId: string) {
  const response = await apiClient.get(
    `/api/augmis-business/opportunities/${encodeURIComponent(opportunityId)}/ai-assessments`
  );
  return response.data as {
    success: boolean;
    data: AugmisBusinessOpportunityAIAssessmentSummary[];
  };
}

export async function listAugmisBusinessOpportunityExperienceMatches(
  opportunityId: string
) {
  const response = await apiClient.get(
    `/api/augmis-business/opportunities/${encodeURIComponent(opportunityId)}/experience-matches`
  );
  return response.data as {
    success: boolean;
    data: AugmisBusinessOpportunityExperienceMatch[];
  };
}

export async function listAugmisBusinessProspects(params: ProspectListParams = {}) {
  const response = await apiClient.get("/api/augmis-business/prospects", { params });
  return response.data as {
    success: boolean;
    data: AugmisBusinessProspect[];
    pagination: {
      page: number;
      page_size: number;
      total: number;
      total_pages: number;
    };
  };
}

export async function listAugmisBusinessLeads(params: LeadListParams = {}) {
  const response = await apiClient.get("/api/augmis-business/leads", { params });
  return response.data as {
    success: boolean;
    data: AugmisBusinessLead[];
    pagination: {
      page: number;
      page_size: number;
      total: number;
      total_pages: number;
    };
  };
}

export async function getAugmisBusinessLead(leadId: string) {
  const response = await apiClient.get(
    `/api/augmis-business/leads/${encodeURIComponent(leadId)}`
  );
  return response.data as {
    success: boolean;
    data: AugmisBusinessLead;
  };
}

export async function updateAugmisBusinessLead(
  leadId: string,
  payload: UpdateAugmisBusinessLeadPayload
) {
  const response = await apiClient.patch(
    `/api/augmis-business/leads/${encodeURIComponent(leadId)}`,
    payload
  );
  return response.data as {
    success: boolean;
    data: AugmisBusinessLead;
  };
}

export async function updateAugmisBusinessLeadStage(
  leadId: string,
  payload: UpdateAugmisBusinessLeadStagePayload
) {
  const response = await apiClient.patch(
    `/api/augmis-business/leads/${encodeURIComponent(leadId)}/stage`,
    payload
  );
  return response.data as {
    success: boolean;
    data: AugmisBusinessLead;
  };
}

export async function listAugmisBusinessLeadActivities(leadId: string) {
  const response = await apiClient.get(
    `/api/augmis-business/leads/${encodeURIComponent(leadId)}/activities`
  );
  return response.data as {
    success: boolean;
    data: AugmisBusinessActivity[];
  };
}

export async function createAugmisBusinessLeadActivity(
  leadId: string,
  payload: CreateAugmisBusinessLeadActivityPayload
) {
  const response = await apiClient.post(
    `/api/augmis-business/leads/${encodeURIComponent(leadId)}/activities`,
    payload
  );
  return response.data as {
    success: boolean;
    data: AugmisBusinessActivity;
  };
}

export async function listAugmisBusinessLeadTasks(leadId: string) {
  const response = await apiClient.get(
    `/api/augmis-business/leads/${encodeURIComponent(leadId)}/tasks`
  );
  return response.data as {
    success: boolean;
    data: AugmisBusinessTask[];
  };
}

export async function listAugmisBusinessTasks(params: TaskListParams = {}) {
  const response = await apiClient.get("/api/augmis-business/tasks", { params });
  return response.data as {
    success: boolean;
    data: AugmisBusinessTask[];
    pagination: {
      page: number;
      page_size: number;
      total: number;
      total_pages: number;
    };
  };
}

export async function listAugmisBusinessAssignableUsers(params?: {
  search?: string;
  user_ids?: string[];
  include_inactive?: boolean;
  limit?: number;
}) {
  const response = await apiClient.get("/api/augmis-business/users", { params });
  return response.data as {
    success: boolean;
    data: AugmisBusinessAssignableUser[];
  };
}

export async function createAugmisBusinessTask(payload: CreateAugmisBusinessTaskPayload) {
  const response = await apiClient.post("/api/augmis-business/tasks", payload);
  return response.data as {
    success: boolean;
    data: AugmisBusinessTask;
  };
}

export async function updateAugmisBusinessTask(
  taskId: string,
  payload: UpdateAugmisBusinessTaskPayload
) {
  const response = await apiClient.patch(
    `/api/augmis-business/tasks/${encodeURIComponent(taskId)}`,
    payload
  );
  return response.data as {
    success: boolean;
    data: AugmisBusinessTask;
  };
}

export async function completeAugmisBusinessTask(
  taskId: string,
  payload: CompleteAugmisBusinessTaskPayload = {}
) {
  const response = await apiClient.post(
    `/api/augmis-business/tasks/${encodeURIComponent(taskId)}/complete`,
    payload
  );
  return response.data as {
    success: boolean;
    data: AugmisBusinessTask;
  };
}

export async function getAugmisBusinessProspect(prospectId: string) {
  const response = await apiClient.get(
    `/api/augmis-business/prospects/${encodeURIComponent(prospectId)}`
  );
  return response.data as {
    success: boolean;
    data: AugmisBusinessProspect;
  };
}

export async function createAugmisBusinessProspect(
  payload: CreateAugmisBusinessProspectPayload
) {
  const response = await apiClient.post("/api/augmis-business/prospects", payload);
  return response.data as {
    success: boolean;
    data: AugmisBusinessProspect;
  };
}

export async function updateAugmisBusinessProspect(
  prospectId: string,
  payload: Partial<CreateAugmisBusinessProspectPayload>
) {
  const response = await apiClient.patch(
    `/api/augmis-business/prospects/${encodeURIComponent(prospectId)}`,
    payload
  );
  return response.data as {
    success: boolean;
    data: AugmisBusinessProspect;
  };
}

export async function getAugmisBusinessProspectContacts(prospectId: string) {
  const response = await apiClient.get(
    `/api/augmis-business/prospects/${encodeURIComponent(prospectId)}/contacts`
  );
  return response.data as {
    success: boolean;
    data: AugmisBusinessContact[];
  };
}

export async function createAugmisBusinessContact(
  prospectId: string,
  payload: CreateAugmisBusinessContactPayload
) {
  const response = await apiClient.post(
    `/api/augmis-business/prospects/${encodeURIComponent(prospectId)}/contacts`,
    payload
  );
  return response.data as {
    success: boolean;
    data: AugmisBusinessContact;
  };
}

export async function updateAugmisBusinessContact(
  contactId: string,
  payload: Partial<CreateAugmisBusinessContactPayload>
) {
  const response = await apiClient.patch(
    `/api/augmis-business/contacts/${encodeURIComponent(contactId)}`,
    payload
  );
  return response.data as {
    success: boolean;
    data: AugmisBusinessContact;
  };
}

export async function deleteAugmisBusinessContact(contactId: string) {
  const response = await apiClient.delete(
    `/api/augmis-business/contacts/${encodeURIComponent(contactId)}`
  );
  return response.data as {
    success: boolean;
    deleted: number;
    data?: {
      id: string;
      prospect_id: string;
      full_name: string | null;
      job_title: string | null;
    };
  };
}

export async function listAugmisBusinessProspectOpportunities(prospectId: string) {
  const response = await apiClient.get(
    `/api/augmis-business/prospects/${encodeURIComponent(prospectId)}/opportunities`
  );
  return response.data as {
    success: boolean;
    data: AugmisBusinessProspectOpportunity[];
  };
}

export async function listAugmisBusinessProspectLeads(prospectId: string) {
  const response = await apiClient.get(
    `/api/augmis-business/prospects/${encodeURIComponent(prospectId)}/leads`
  );
  return response.data as {
    success: boolean;
    data: AugmisBusinessProspectLead[];
  };
}

export async function listAugmisBusinessProspectActivities(prospectId: string) {
  const response = await apiClient.get(
    `/api/augmis-business/prospects/${encodeURIComponent(prospectId)}/activities`
  );
  return response.data as {
    success: boolean;
    data: AugmisBusinessProspectActivity[];
  };
}

export async function listAugmisBusinessReplies(params: ReplyListParams = {}) {
  const normalizedParams = {
    ...params,
    status: params.status === "all" ? undefined : params.status,
    intent: params.intent === "all" ? undefined : params.intent,
  };
  const response = await apiClient.get("/api/augmis-business/replies", {
    params: normalizedParams,
  });
  return response.data as {
    success: boolean;
    data: AugmisBusinessReply[];
    summary: {
      unreviewed_replies: number;
      action_required: number;
      positive_high_engagement: number;
      objections: number;
      meetings_or_proposals: number;
    };
    pagination: {
      page: number;
      page_size: number;
      total: number;
      total_pages: number;
    };
  };
}

export async function createAugmisBusinessReply(payload: CreateAugmisBusinessReplyPayload) {
  const response = await apiClient.post("/api/augmis-business/replies", payload);
  return response.data as {
    success: boolean;
    data: AugmisBusinessReply;
  };
}

export async function getAugmisBusinessReply(replyId: string) {
  const response = await apiClient.get(
    `/api/augmis-business/replies/${encodeURIComponent(replyId)}`
  );
  return response.data as {
    success: boolean;
    data: AugmisBusinessReply;
  };
}

export async function updateAugmisBusinessReply(
  replyId: string,
  payload: UpdateAugmisBusinessReplyPayload
) {
  const response = await apiClient.patch(
    `/api/augmis-business/replies/${encodeURIComponent(replyId)}`,
    payload
  );
  return response.data as {
    success: boolean;
    data: AugmisBusinessReply;
  };
}

export async function analyzeAugmisBusinessReply(replyId: string) {
  const response = await apiClient.post(
    `/api/augmis-business/replies/${encodeURIComponent(replyId)}/analyze`
  );
  return response.data as {
    success: boolean;
    data: AugmisBusinessReplyAnalysis;
  };
}

export async function getAugmisBusinessReplyAnalysis(replyId: string) {
  const response = await apiClient.get(
    `/api/augmis-business/replies/${encodeURIComponent(replyId)}/analysis`
  );
  return response.data as {
    success: boolean;
    data: AugmisBusinessReplyAnalysis;
  };
}

export async function listAugmisBusinessReplyAnalyses(replyId: string) {
  const response = await apiClient.get(
    `/api/augmis-business/replies/${encodeURIComponent(replyId)}/analyses`
  );
  return response.data as {
    success: boolean;
    data: AugmisBusinessReplyAnalysisSummary[];
  };
}

export async function generateAugmisBusinessReplyResponse(
  replyId: string,
  payload: GenerateAugmisBusinessReplyResponsePayload
) {
  const response = await apiClient.post(
    `/api/augmis-business/replies/${encodeURIComponent(replyId)}/response/generate`,
    payload
  );
  return response.data as {
    success: boolean;
    data: AugmisBusinessReplyResponseDraft;
  };
}

export async function listAugmisBusinessReplyResponses(replyId: string) {
  const response = await apiClient.get(
    `/api/augmis-business/replies/${encodeURIComponent(replyId)}/responses`
  );
  return response.data as {
    success: boolean;
    data: AugmisBusinessReplyResponseDraftSummary[];
  };
}

export async function getAugmisBusinessReplyResponse(responseId: string) {
  const response = await apiClient.get(
    `/api/augmis-business/reply-responses/${encodeURIComponent(responseId)}`
  );
  return response.data as {
    success: boolean;
    data: AugmisBusinessReplyResponseDraft;
  };
}

export async function updateAugmisBusinessReplyResponse(
  responseId: string,
  payload: UpdateAugmisBusinessReplyResponsePayload
) {
  const response = await apiClient.patch(
    `/api/augmis-business/reply-responses/${encodeURIComponent(responseId)}`,
    payload
  );
  return response.data as {
    success: boolean;
    data: AugmisBusinessReplyResponseDraft;
  };
}

export async function approveAugmisBusinessReplyResponse(
  responseId: string,
  payload: AugmisBusinessStatusActionPayload = {}
) {
  const response = await apiClient.post(
    `/api/augmis-business/reply-responses/${encodeURIComponent(responseId)}/approve`,
    payload
  );
  return response.data as {
    success: boolean;
    data: AugmisBusinessReplyResponseDraft;
  };
}

export async function rejectAugmisBusinessReplyResponse(
  responseId: string,
  payload: AugmisBusinessStatusActionPayload = {}
) {
  const response = await apiClient.post(
    `/api/augmis-business/reply-responses/${encodeURIComponent(responseId)}/reject`,
    payload
  );
  return response.data as {
    success: boolean;
    data: AugmisBusinessReplyResponseDraft;
  };
}

export async function buildAugmisBusinessLead(
  opportunityId: string,
  payload: BuildLeadPayload
) {
  const response = await apiClient.post(
    `/api/augmis-business/opportunities/${encodeURIComponent(opportunityId)}/build-lead`,
    payload
  );
  return response.data as {
    success: boolean;
    data: {
      lead: AugmisBusinessLead;
      first_task: AugmisBusinessTask;
      opportunity: AugmisBusinessOpportunity;
    };
  };
}
