export type TokenUser = {
  id: string;
  username: string;
  first_name: string;
  last_name: string;
  organization_id: string;
  organization_slug: string;
  organization_name: string;
  roles: string[];
  permissions: string[];
  is_super_admin: boolean;
};

export type AuthSession = {
  user: TokenUser;
  csrf_token: string;
};

export type LearnerProfile = {
  id: string;
  user_id: string;
  organization_id: string;
  onboarding_status: string;
  target_fde_role: string | null;
  career_interests: string[];
  domain_preferences: string[];
  technical_experience: Record<string, unknown>;
  project_experience: unknown[];
  domain_experience: Record<string, unknown>;
  existing_certifications: unknown[];
  years_of_experience: number | null;
  available_weekly_hours: number | null;
  consent_privacy: boolean;
  consent_ai_processing: boolean;
  profile_completed_at: string | null;
  skills_confirmed_at: string | null;
  summary: string | null;
};

export type ExtractedSkill = {
  name: string;
  category?: string | null;
  proficiency_level: string;
  years_experience?: number | null;
  evidence?: string | null;
  confidence: number;
};

export type ResumeExtractionPayload = {
  summary?: string | null;
  years_of_experience?: number | null;
  skills: ExtractedSkill[];
  technical_experience: unknown[];
  project_experience: unknown[];
  domain_experience: string[];
  certifications: Array<{ name: string; issuer?: string | null; year?: string | null }>;
  suggested_target_roles: string[];
  suggested_domains: string[];
};

export type AIExtraction = {
  id: string;
  resume_document_id: string;
  provider: string;
  model: string;
  prompt_version: string;
  status: string;
  validated_payload: ResumeExtractionPayload | null;
  edited_payload: ResumeExtractionPayload | null;
  confirmed_payload: ResumeExtractionPayload | null;
  input_tokens?: number | null;
  output_tokens?: number | null;
  estimated_cost_usd?: number | null;
  error_message?: string | null;
  hallucination_risk_score?: number | null;
  confirmed_at?: string | null;
};

export type LearnerSkill = {
  id: string;
  skill_id: string;
  skill_name: string;
  skill_code: string;
  pillar_name?: string | null;
  proficiency_level: string;
  score?: number | null;
  confidence?: number | null;
  source: string;
  confirmed: boolean;
  notes?: string | null;
};

export type AuditLog = {
  id: string;
  action: string;
  entity_type: string;
  entity_id: string | null;
  actor_id: string | null;
  before_state: Record<string, unknown> | null;
  after_state: Record<string, unknown> | null;
  ip_address: string | null;
  correlation_id: string | null;
  created_at: string;
  metadata: Record<string, unknown>;
};

export type UserOut = {
  id: string;
  username: string;
  first_name: string;
  last_name: string;
  status: string;
  organization_id: string;
  roles: string[];
  is_super_admin: boolean;
  has_recoverable_password?: boolean;
};

export type AssessmentQuestion = {
  id: string;
  skill_id: string;
  skill_code?: string | null;
  skill_name?: string | null;
  stem: string;
  choices: string[];
  sort_order: number;
  correct_index?: number | null;
  explanation?: string | null;
  selected_index?: number | null;
  is_correct?: boolean | null;
};

export type Assessment = {
  id: string;
  user_id: string;
  organization_id: string;
  kind: string;
  status: string;
  provider?: string | null;
  model?: string | null;
  prompt_version?: string | null;
  score_percent?: number | null;
  correct_count?: number | null;
  total_count?: number | null;
  started_at?: string | null;
  submitted_at?: string | null;
  error_message?: string | null;
  created_at: string;
  questions: AssessmentQuestion[];
  draft_answers?: Array<{ question_id: string; selected_index: number }>;
};

export type LearningPlanItem = {
  id: string;
  skill_id: string;
  skill_code?: string | null;
  skill_name?: string | null;
  priority: number;
  status: string;
  rationale?: string | null;
  estimated_hours?: number | null;
};

export type LearningPlan = {
  id: string;
  user_id: string;
  organization_id: string;
  source_assessment_id?: string | null;
  status: string;
  summary?: string | null;
  provider?: string | null;
  model?: string | null;
  created_at: string;
  items: LearningPlanItem[];
  completed_count: number;
  total_count: number;
};

export type OrgOverview = {
  organization_id: string;
  organization_name: string;
  candidates_count: number;
  profiles_completed: number;
  skills_confirmed: number;
  assessments_scored: number;
  plans_active: number;
  avg_assessment_score?: number | null;
};

export type CandidateInterviewReadiness = {
  user_id: string;
  username?: string | null;
  first_name: string;
  last_name: string;
  email: string;
  account_status: string;
  skills_confirmed: boolean;
  mcq_status?: string | null;
  mcq_score_percent?: number | null;
  coding_status?: string | null;
  coding_score_percent?: number | null;
  ready_for_manual_interview: boolean;
  readiness_reason: string;
};

export type InterviewReadiness = {
  organization_id: string;
  organization_name: string;
  mcq_pass_threshold: number;
  coding_pass_threshold: number;
  ready_count: number;
  candidates: CandidateInterviewReadiness[];
};

export type AiProviderInfo = {
  id: string;
  name: string;
  enabled: boolean;
  auth_type: string;
  default_model?: string;
};

export type AiProvidersResponse = {
  providers: AiProviderInfo[];
  default_provider: string;
};

export type CourseSlide = {
  id: string;
  module_id: string;
  title: string;
  body_markdown: string;
  visual_type: string;
  visual_payload: Record<string, unknown>;
  key_takeaway?: string | null;
  self_check?: { question?: string; answer?: string } | null;
  sort_order: number;
  completed: boolean;
};

export type CourseModule = {
  id: string;
  title: string;
  objectives: string[];
  sort_order: number;
  status: string;
  slides: CourseSlide[];
};

export type CourseProgress = {
  percent_complete: number;
  completed_slide_ids: string[];
  current_module_id?: string | null;
  current_slide_id?: string | null;
  completed_at?: string | null;
};

export type CourseTopic = {
  id: string;
  label: string;
  blurb: string;
  group: string;
};

export type Course = {
  id: string;
  domain: string;
  title: string;
  summary?: string | null;
  status: string;
  learning_goals: string[];
  selected_topics?: string[];
  provider?: string | null;
  model?: string | null;
  prompt_version?: string | null;
  error_message?: string | null;
  created_at: string;
  completed_at?: string | null;
  modules: CourseModule[];
  progress?: CourseProgress | null;
  total_slides: number;
  completed_slides: number;
};

export type CourseCatalogItem = {
  domain: string;
  required: boolean;
  course: Course | null;
  title_hint: string;
  description: string;
  topics: CourseTopic[];
  selected_topic_ids: string[];
};

export type CourseCatalog = {
  domains: string[];
  items: CourseCatalogItem[];
  assessment_unlocked: boolean;
};

export type CodingQuestion = {
  id: string;
  title: string;
  prompt_markdown: string;
  language: string;
  starter_code: string;
  topic_tags: string[];
  domain_focus?: string | null;
  difficulty: string;
  sort_order: number;
  submitted_code?: string | null;
  score?: number | null;
  passed?: boolean | null;
  feedback?: string | null;
};

export type CodingAssessment = {
  id: string;
  status: string;
  domains: string[];
  provider?: string | null;
  model?: string | null;
  prompt_version?: string | null;
  score_percent?: number | null;
  passed_count?: number | null;
  total_count?: number | null;
  started_at?: string | null;
  submitted_at?: string | null;
  error_message?: string | null;
  created_at: string;
  questions: CodingQuestion[];
  draft_answers?: Array<{ question_id: string; code: string }>;
};
