"use client";

import { FormEvent, useMemo, useState } from "react";
import Image from "next/image";
import useSWR from "swr";
import { getFormSchema, validateSubmission } from "../lib/api";
import { useDistricts, useProvinces, useWards } from "../hooks/useAdministrativeUnits";
import type { FormField, FormSchema, ValidationIssue, ValidationResult } from "../lib/types";
import { Icon } from "./Icon";
import { WorkflowScrollDock } from "./WorkflowScrollDock";

type AdministrativeAddressValue = {
  province_code: string;
  province: string;
  district_code: string;
  district: string;
  ward_code: string;
  ward: string;
  detail: string;
};

type FieldValue = string | boolean | AdministrativeAddressValue;

const emptyAddress: AdministrativeAddressValue = {
  province_code: "",
  province: "",
  district_code: "",
  district: "",
  ward_code: "",
  ward: "",
  detail: "",
};

function formatVietnameseDateInput(raw: string) {
  const digits = raw.replace(/\D/g, "").slice(0, 8);
  if (digits.length <= 2) return digits;
  if (digits.length <= 4) return `${digits.slice(0, 2)}/${digits.slice(2)}`;
  return `${digits.slice(0, 2)}/${digits.slice(2, 4)}/${digits.slice(4)}`;
}

function normalizeDateDisplay(value: string) {
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    const [year, month, day] = value.split("-");
    return `${day}/${month}/${year}`;
  }
  return formatVietnameseDateInput(value);
}

function setNested(target: Record<string, unknown>, path: string, value: unknown) {
  const parts = path.split(".");
  let current = target;
  parts.forEach((part, index) => {
    if (part === "__proto__" || part === "constructor" || part === "prototype") return;
    if (index === parts.length - 1) current[part] = value;
    else current = (current[part] ??= {}) as Record<string, unknown>;
  });
}

function AdministrativeAddressControl({
  value,
  onChange,
  issue,
}: {
  value: AdministrativeAddressValue;
  onChange: (value: AdministrativeAddressValue) => void;
  issue?: ValidationIssue;
}) {
  const { provinces } = useProvinces();
  const { districts } = useDistricts(value.province_code);
  const { wards } = useWards(value.province_code, value.district_code);

  return (
    <div className={`administrative-address ${issue ? "has-error" : ""}`}>
      <select
        value={value.province_code}
        onChange={(event) => {
          const unit = provinces.find((item) => item.code === event.target.value);
          onChange({
            ...emptyAddress,
            province_code: unit?.code || "",
            province: unit?.name || "",
          });
        }}
      >
        <option value="">-- Tỉnh/thành phố --</option>
        {provinces.map((item) => (
          <option key={item.code} value={item.code}>
            {item.name}
          </option>
        ))}
      </select>
      <select
        value={value.district_code}
        disabled={!value.province_code}
        onChange={(event) => {
          const unit = districts.find((item) => item.code === event.target.value);
          onChange({
            ...value,
            district_code: unit?.code || "",
            district: unit?.name || "",
            ward_code: "",
            ward: "",
          });
        }}
      >
        <option value="">-- Quận/huyện --</option>
        {districts.map((item) => (
          <option key={item.code} value={item.code}>
            {item.name}
          </option>
        ))}
      </select>
      <select
        value={value.ward_code}
        disabled={!value.district_code}
        onChange={(event) => {
          const unit = wards.find((item) => item.code === event.target.value);
          onChange({
            ...value,
            ward_code: unit?.code || "",
            ward: unit?.name || "",
          });
        }}
      >
        <option value="">-- Xã/phường --</option>
        {wards.map((item) => (
          <option key={item.code} value={item.code}>
            {item.name}
          </option>
        ))}
      </select>
      <input
        type="text"
        value={value.detail}
        onChange={(event) => onChange({ ...value, detail: event.target.value })}
        placeholder="Số nhà, đường/ngõ/ngách, thôn/tổ..."
      />
    </div>
  );
}

function FieldControl({
  field,
  value,
  onChange,
  issue,
}: {
  field: FormField;
  value: FieldValue;
  onChange: (value: FieldValue) => void;
  issue?: ValidationIssue;
}) {
  const describedBy = issue ? `error-${field.path}` : undefined;
  if (field.type === "administrative_address") {
    return (
      <AdministrativeAddressControl
        value={typeof value === "object" && value !== null ? (value as AdministrativeAddressValue) : emptyAddress}
        onChange={onChange}
        issue={issue}
      />
    );
  }
  if (field.type === "boolean" || field.type === "confirmation") {
    return (
      <select
        value={value === true ? "true" : value === false ? "false" : ""}
        onChange={(event) => onChange(event.target.value === "true")}
        aria-invalid={!!issue}
        aria-describedby={describedBy}
        className={`compact-select ${issue ? "has-error" : ""}`}
      >
        <option value="">-- Chọn --</option>
        <option value="true">Có</option>
        <option value="false">Không</option>
      </select>
    );
  }
  if (field.type === "enum" && field.options.length) {
    return (
      <select
        value={String(value)}
        onChange={(event) => onChange(event.target.value)}
        aria-invalid={!!issue}
        aria-describedby={describedBy}
      >
        <option value="">-- Chọn thông tin --</option>
        {field.options.map((option) => {
          const entry = typeof option === "string" ? { label: option, value: option } : option;
          return (
            <option value={entry.value} key={entry.value}>
              {entry.label}
            </option>
          );
        })}
      </select>
    );
  }
  return (
    <input
      type="text"
      value={field.type === "date" ? normalizeDateDisplay(String(value)) : String(value)}
      onChange={(event) => onChange(field.type === "date" ? formatVietnameseDateInput(event.target.value) : event.target.value)}
      placeholder={
        field.type === "date"
          ? "dd/mm/yyyy"
          : field.example || (field.type === "identity_number" ? "Tự động điền sau khi đăng nhập VNeID" : "Nhập thông tin")
      }
      inputMode={field.type === "identity_number" || field.type === "date" ? "numeric" : undefined}
      maxLength={field.type === "identity_number" ? 12 : field.type === "date" ? 10 : undefined}
      aria-invalid={!!issue}
      aria-describedby={describedBy}
    />
  );
}

export function DynamicForm({
  procedureCode,
  onBack,
  onContinue,
}: {
  procedureCode: string;
  onBack: () => void;
  onContinue?: (result: ValidationResult) => void;
}) {
  const { data: schema, isLoading: loading, error: schemaError } = useSWR<FormSchema>(
    procedureCode ? `/api/v1/procedures/${encodeURIComponent(procedureCode)}/form-schema` : null,
    () => getFormSchema(procedureCode)
  );

  const [values, setValues] = useState<Record<string, FieldValue>>({});
  const [openHelp, setOpenHelp] = useState<string | null>(null);
  const [result, setResult] = useState<ValidationResult | null>(null);
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState("");

  const needsProvinces = schema?.fields.some((field) => field.options_endpoint === "/api/v1/administrative-units/provinces");
  const { provinces, error: provError } = useProvinces();
  const provinceOptions =
    needsProvinces && provinces.length > 0 ? provinces.map((item) => ({ label: item.name, value: item.name })) : null;
  const provinceError = provError ? "Không tải được danh mục mới nhất; đang dùng danh mục dự phòng." : "";

  const issues = useMemo(() => new Map((result?.issues || []).map((issue) => [issue.field, issue])), [result]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setChecking(true);
    setError("");
    const submission: Record<string, unknown> = {};
    Object.entries(values).forEach(([path, value]) => setNested(submission, path, value));
    try {
      setResult(await validateSubmission(procedureCode, submission));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không thể kiểm tra hồ sơ.");
    } finally {
      setChecking(false);
    }
  }

  if (loading) {
    return (
      <div className="form-loading">
        <span />
        <strong>Đang tải biểu mẫu từ hệ thống...</strong>
      </div>
    );
  }

  if (!schema) {
    return (
      <div className="error-state">
        <Icon name="warning" />
        <h3>Chưa thể tải biểu mẫu</h3>
        <p>{schemaError?.message || error}</p>
        <button onClick={onBack}>Quay lại hướng dẫn</button>
      </div>
    );
  }

  return (
    <div className="form-workspace" data-workflow-scroll>
      <div className="form-heading">
        <div>
          <small>KIỂM TRA TRƯỚC KHI NỘP</small>
          <h2>{schema.procedure.title}</h2>
          <p>
            Nhập thông tin theo giấy tờ gốc. Trường có dấu <b>*</b> là bắt buộc.
          </p>
        </div>
        <span>Mã: {procedureCode}</span>
      </div>

      {result && (
        <div className={`validation-summary ${result.ready_to_submit ? "ready" : "issues"}`}>
          <Icon name={result.ready_to_submit ? "shield" : "warning"} />
          <div>
            <strong>
              {result.ready_to_submit
                ? "Đã đạt kiểm tra sơ bộ"
                : `Phát hiện ${result.issues.length} nội dung cần kiểm tra`}
            </strong>
            <p>
              {result.ready_to_submit
                ? "Dữ liệu đúng cấu trúc và chưa phát hiện mâu thuẫn. Kết quả này không thay thế bước kiểm tra của cơ quan nhà nước."
                : "Sửa các trường được đánh dấu để giảm rủi ro thiếu, sai hoặc nhập dữ liệu mẫu."}
            </p>
          </div>
        </div>
      )}

      <form onSubmit={submit}>
        <div className="field-grid">
          {schema.fields.map((field) => {
            const issue = issues.get(field.path);
            const displayedField =
              field.options_endpoint === "/api/v1/administrative-units/provinces" && provinceOptions
                ? { ...field, options: provinceOptions }
                : field;
            const defaultValue =
              field.type === "boolean" || field.type === "confirmation"
                ? false
                : field.type === "administrative_address"
                  ? emptyAddress
                  : "";
            return (
              <div
                className={`form-field flex flex-col gap-1 ${
                  field.type === "boolean" || field.type === "confirmation" || field.type === "administrative_address"
                    ? "wide"
                    : ""
                }`}
                key={field.path}
              >
                {(
                  <label htmlFor={field.path}>
                    {field.label}
                    {field.required && <b>*</b>}
                    {field.prefill_source === "vneid" && <span className="verified-source">VNeID</span>}
                    {field.help_text && (
                      <button
                        type="button"
                        className="field-help-button"
                        onClick={() => setOpenHelp(openHelp === field.path ? null : field.path)}
                      >
                        Giải nghĩa
                      </button>
                    )}
                  </label>
                )}
                {openHelp === field.path && field.help_text && (
                  <div className="field-help">
                    <Image src="/govlogo.png" alt="GovEase AI" width={20} height={20} />
                    <span>{field.help_text}</span>
                  </div>
                )}
                <FieldControl
                  field={displayedField}
                  value={values[field.path] ?? defaultValue}
                  onChange={(value) => {
                    setValues((current) => ({ ...current, [field.path]: value }));
                    if (result) setResult(null);
                  }}
                  issue={issue}
                />
                {issue && (
                  <div className="field-error" id={`error-${field.path}`}>
                    <strong>{issue.message}</strong>
                    <span>{issue.suggestion}</span>
                  </div>
                )}
                {!issue && field.validation.format && <small>Định dạng: {field.validation.format}</small>}
                {field.prefill_source === "vneid" && (
                  <small>
                    Chưa kết nối VNeID trong bản demo; số nhập tay chỉ được kiểm tra cấu trúc, không được xác nhận là
                    số thật.
                  </small>
                )}
                {field.options_endpoint && !provinceOptions && !provinceError && <small>Đang tải danh mục tỉnh/thành phố...</small>}
                {field.options_source_url && field.options_source_url !== field.source_url && (
                  <small>
                    <a href={field.options_source_url} target="_blank" rel="noreferrer">
                      Nguồn danh mục lựa chọn
                    </a>
                  </small>
                )}
              </div>
            );
          })}
        </div>

        {provinceError && (
          <div className="inline-error">
            <Icon name="warning" />
            {provinceError}
          </div>
        )}
        {error && (
          <div className="inline-error">
            <Icon name="warning" />
            {error}
          </div>
        )}

        <div className="form-actions">
          <button type="button" className="secondary-button" onClick={onBack}>
            ← Xem lại hướng dẫn
          </button>
          <div className="form-actions-group">
            {result && onContinue && (
              <button type="button" className="secondary-button" onClick={() => onContinue(result)}>
                Xem bước tiếp theo
                <Icon name="arrow" />
              </button>
            )}
            <button className="primary-button" type="submit" disabled={checking}>
              {checking ? "Đang đối chiếu..." : "Kiểm tra thông tin"}
              <Icon name="shield" />
            </button>
          </div>
        </div>
      </form>

      <div className="privacy-note">
        <Icon name="shield" />
        <span>Thông tin chỉ được gửi đến API để kiểm tra và không được frontend lưu trữ. Kết quả mang tính hướng dẫn.</span>
      </div>
      <WorkflowScrollDock />
    </div>
  );
}
