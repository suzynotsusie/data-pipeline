export type ChatMessage = { role: "user" | "assistant"; content: string };

export type CitizenSubdomainOption = {
  event_id: number;
  subdomain_key: string;
  label: string;
  summary?: string | null;
};

export type CitizenGroupOption = {
  group_key: string;
  group_id: number;
  label: string;
  description: string;
  entry_prompts: string[];
  subdomains: CitizenSubdomainOption[];
};

export type CitizenWorkflowCatalog = {
  persona: "citizen";
  updated_at: string;
  groups: CitizenGroupOption[];
};

export type Source = {
  title: string;
  source_url: string;
  chunk_id?: string;
};

export type Procedure = {
  id: string;
  code: string;
  title: string;
  source_url: string;
  detail_level?: string;
  agency?: unknown;
};

export type ChecklistItem = {
  name?: string;
  condition?: string | null;
  quantity?: string | number | null;
  notes?: string | null;
  alternatives?: unknown;
};

export type StepItem = {
  order?: number;
  title?: string;
  description?: string;
  example?: string | null;
};

export type IntakeResult = {
  session_id: string;
  status: "needs_clarification" | "completed";
  needs_clarification: boolean;
  clarifying_question_id?: string | null;
  clarifying_question?: string | null;
  answers: Record<string, string>;
  confidence: number;
  procedure?: Procedure | null;
  checklist: {
    documents?: ChecklistItem[];
    conditional_documents?: ChecklistItem[];
    steps?: StepItem[];
    user_steps?: StepItem[];
    next_step_summary?: string | null;
    overview_summary?: string | null;
    processing_time_summary?: string | null;
    submission_place_summary?: string | null;
    submission_method_labels?: string[];
  };
  examples: string[];
  common_errors: Array<{ field?: string; problem?: string; fix?: string }>;
  sources: Source[];
  quick_replies: Array<{ value: string; label: string; description?: string }>;
  current_node_id?: string | null;
  domain_key?: string | null;
  domain_label?: string | null;
  workflow_state?: {
    slots?: Record<string, string>;
    asked_node_ids?: string[];
    completed_route_id?: string;
    procedure_code?: string;
    why_this_route?: string;
  };
};

export type CitizenGroup = {
  key: string;
  label: string;
  official_group_id: number;
  official_url: string;
  description: string;
  preferred_workflow_family?: string | null;
  procedure_count: number;
  raw_data_count: number;
  workflow_ready_count: number;
  catalog_ready_count: number;
  raw_only_count: number;
};

export type CatalogProcedure = {
  code: string;
  title: string;
  source_url: string;
  field?: string | null;
  raw_data_available: boolean;
  normalized_available: boolean;
  detail_level?: string | null;
  workflow_family?: string | null;
  support_level: string;
  notes?: string;
};

export type FormField = {
  path: string;
  label: string;
  type: string;
  required: boolean;
  example?: string | null;
  options: Array<string | { label: string; value: string }>;
  validation: { format?: string; pattern?: string };
  source_url: string;
  options_source_url?: string;
  options_endpoint?: string | null;
  prefill_source?: "vneid" | string | null;
  read_only_when_verified?: boolean;
  help_text?: string | null;
};

export type FormSchema = {
  procedure: Procedure;
  fields: FormField[];
  source_url: string;
  schema_version: string;
};

export type ValidationIssue = {
  field: string;
  rule_id: string;
  severity: "error" | "warning" | string;
  layer: string;
  message: string;
  suggestion: string;
  source_url: string;
  evidence?: string;
  blocking: boolean;
};

export type ValidationResult = {
  ready_to_submit: boolean;
  issues: ValidationIssue[];
  procedure: Procedure;
  validation_layers: Record<string, unknown>;
};

export type ApiErrorBody = { error?: { code?: string; message?: string; request_id?: string } };

export type Province = { code: string; name: string };
export type AdministrativeUnit = Province;
