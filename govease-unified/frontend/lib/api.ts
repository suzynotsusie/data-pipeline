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

const API_URL =
  typeof window === "undefined"
    ? (process.env.NEXT_PUBLIC_API_URL || "").replace(/\/$/, "")
    : "";
const ENABLE_OFFLINE_INTAKE_MOCK = process.env.NEXT_PUBLIC_ENABLE_OFFLINE_INTAKE_MOCK === "true";

export class ApiError extends Error {
  constructor(message: string, public code = "REQUEST_FAILED", public requestId?: string) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response | undefined;
  const target = `${API_URL || ""}${path}`;
  const startedAt = typeof performance !== "undefined" ? performance.now() : Date.now();
  try {
    response = await fetch(target, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
    });
  } catch (err) {
    // catch Network Errors
  }
  const finishedAt = typeof performance !== "undefined" ? performance.now() : Date.now();
  const clientMs = Number((finishedAt - startedAt).toFixed(2));
  const routeMs = response?.headers.get("X-GovEase-Route-MS");
  const totalMs = response?.headers.get("X-Response-Time-MS");
  const requestId = response?.headers.get("X-Request-ID");
  console.info("[GovEase API]", {
    path,
    ok: Boolean(response?.ok),
    status: response?.status ?? "NETWORK_ERROR",
    clientMs,
    routeMs,
    totalMs,
    requestId,
  });

  // --- FALLBACK MOCK DATA CHO FRONTEND KHI BACKEND DOWN HOẶC 502/504 ---
  if (!response || !response.ok) {
    console.warn("Backend is unreachable or returned error. Using mock fallback for:", path);
    if (path.includes("/catalog/citizen-groups")) {
      return {
        persona: "citizen",
        items: [
          {
            group_key: "phuong_tien_nguoi_lai",
            label: "Phương tiện và người lái",
            subdomains: [
              { subdomain_key: "giay_phep_lai_xe", subdomain_label: "Giấy phép lái xe" },
              { subdomain_key: "dang_ky_phuong_tien", subdomain_label: "Đăng ký phương tiện" },
              { subdomain_key: "dang_kiem_phuong_tien", subdomain_label: "Đăng kiểm phương tiện" }
            ]
          },
          {
            group_key: "hoc_tap",
            label: "Học tập",
            subdomains: [
              { subdomain_key: "giao_duc_mam_non", subdomain_label: "Giáo dục mầm non" },
              { subdomain_key: "giao_duc_pho_thong", subdomain_label: "Giáo dục phổ thông" }
            ]
          }
        ],
        total: 2
      } as unknown as T;
    }
    if (path.includes("/intake") && ENABLE_OFFLINE_INTAKE_MOCK) {
      let payload: any = {};
      try {
        if (init?.body) payload = JSON.parse(init.body as string);
      } catch (e) {}
      
      const msg = (payload.message || "").toLowerCase();
      const isFirstTurn = !payload.answers || Object.keys(payload.answers).length === 0;

      if (msg.includes("không") || payload.answers?.mock_q_2 || (!isFirstTurn && msg.includes("chốt"))) {
        return {
          status: "completed",
          session_id: "mock_session_123",
          answers: { ...payload.answers, mock_q_2: msg },
          procedure: {
            code: "1.000010",
            title: "Cấp đổi Giấy phép lái xe do ngành Giao thông vận tải cấp",
            url: "https://dichvucong.gov.vn/p/home/dvc-chi-tiet-thu-tuc-hanh-chinh.html?ma_thu_tuc=1.000010"
          }
        } as unknown as T;
      }

      if (msg.includes("đúng") || msg.includes("có") || msg.includes("cấp đổi") || msg.includes("yes")) {
        return {
          status: "needs_clarification",
          session_id: "mock_session_123",
          answers: { ...payload.answers, mock_q_1: msg },
          clarifying_question: "Giả lập (Offline): Xác nhận lại, bạn muốn nhận kết quả qua đường bưu điện đúng không?",
          clarifying_question_id: "mock_q_2",
          quick_replies: [{ label: "Có", value: "Có" }, { label: "Không", value: "Không" }]
        } as unknown as T;
      }

      return {
        status: "needs_clarification",
        session_id: "mock_session_123",
        answers: {},
        clarifying_question: "Giả lập (Offline): Bạn đang muốn làm thủ tục cấp đổi giấy phép lái xe hay đăng ký xe?",
        clarifying_question_id: "mock_q_1",
        quick_replies: [{ label: "Cấp đổi GPLX", value: "Cấp đổi GPLX" }, { label: "Đăng ký xe", value: "Đăng ký xe" }]
      } as unknown as T;
    }

    // Nếu không có mock thì throw error cũ
    if (response) {
      const body = (await response.json().catch(() => ({}))) as ApiErrorBody;
      throw new ApiError(
        body.error?.message || "Dịch vụ đang tạm thời gián đoạn.",
        body.error?.code,
        body.error?.request_id,
      );
    }
    throw new ApiError("Không thể kết nối đến dịch vụ GovEase AI (Mock fallback failed). Vui lòng thử lại.", "NETWORK_ERROR");
  }

  return response.json() as Promise<T>;
}

export function submitIntake(payload: {
  message: string;
  session_id?: string;
  procedure_code?: string;
  persona?: string;
  group_key?: string;
  subdomain_key?: string;
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
