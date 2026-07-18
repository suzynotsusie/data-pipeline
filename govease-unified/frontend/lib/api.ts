import type {
  AdministrativeUnit,
  ApiErrorBody,
  CatalogProcedure,
  ChatMessage,
  CitizenGroup,
  FormSchema,
  IntakeResult,
  Province,
  ValidationResult,
} from "./types";

const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(message: string, public code = "REQUEST_FAILED", public requestId?: string) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
    });
  } catch {
    throw new ApiError("Không thể kết nối đến dịch vụ GovEase AI. Vui lòng thử lại.", "NETWORK_ERROR");
  }
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as ApiErrorBody;
    throw new ApiError(
      body.error?.message || "Dịch vụ đang tạm thời gián đoạn.",
      body.error?.code,
      body.error?.request_id,
    );
  }
  return response.json() as Promise<T>;
}

export function submitIntake(payload: {
  message: string;
  session_id?: string;
  procedure_code?: string;
  persona?: string;
  group_key?: string;
  candidate_procedure_codes?: string[];
  history: ChatMessage[];
  answers: Record<string, string>;
}): Promise<IntakeResult> {
  return request("/api/v1/intake", { method: "POST", body: JSON.stringify(payload) });
}

export function getCitizenGroups(): Promise<{ persona: string; items: CitizenGroup[]; total: number }> {
  return request("/api/v1/catalog/citizen-groups");
}

export function getCitizenGroup(groupKey: string): Promise<CitizenGroup & { procedures: CatalogProcedure[] }> {
  return request(`/api/v1/catalog/citizen-groups/${encodeURIComponent(groupKey)}`);
}

export function getFormSchema(procedureCode: string): Promise<FormSchema> {
  return request(`/api/v1/procedures/${encodeURIComponent(procedureCode)}/form-schema`);
}

export function validateSubmission(procedureCode: string, submission: Record<string, unknown>): Promise<ValidationResult> {
  return request(`/api/v1/procedures/${encodeURIComponent(procedureCode)}/validate`, {
    method: "POST",
    body: JSON.stringify({ submission }),
  });
}

export function getProvinces(): Promise<{ items: Province[]; total: number; source_url: string }> {
  return request("/api/v1/administrative-units/provinces");
}

export function getDistricts(provinceCode: string): Promise<{ items: AdministrativeUnit[]; total: number; source_url: string }> {
  return request(`/api/v1/administrative-units/districts?province_code=${encodeURIComponent(provinceCode)}`);
}

export function getWards(provinceCode: string, districtCode: string): Promise<{ items: AdministrativeUnit[]; total: number; source_url: string }> {
  return request(`/api/v1/administrative-units/wards?province_code=${encodeURIComponent(provinceCode)}&district_code=${encodeURIComponent(districtCode)}`);
}

export const apiBaseUrl = API_URL;
