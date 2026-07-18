from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from typing import Any

from .procedure_data import ProcedureDataStore, ProcedureRecord, load_procedure_store


Issue = dict[str, Any]


class SubmissionValidator:
    def __init__(self, store: ProcedureDataStore | None = None):
        self.store = store or load_procedure_store()

    def validate(
        self,
        procedure_identifier: str,
        submission: dict[str, Any],
        *,
        today: date | None = None,
    ) -> list[Issue]:
        record = self.store.require(procedure_identifier)
        today = today or date.today()
        issues: list[Issue] = []

        self._required_field_checks(record, submission, issues)
        self._full_name_checks(record, submission, issues)
        self._identity_number_checks(record, submission, issues)
        self._date_checks(record, submission, issues, today)
        self._signature_check(record, submission, issues)

        code = record.code
        title_key = _norm(record.title)
        if code == "1.001193" or "khai sinh" in title_key:
            self._birth_registration_checks(record, submission, issues, today)
        if code == "1.004194" or "tam tru" in title_key:
            self._temporary_residence_checks(record, submission, issues, today)

        return _dedupe_issues(issues)

    def _required_field_checks(
        self, record: ProcedureRecord, submission: dict[str, Any], issues: list[Issue]
    ) -> None:
        fields = record.data.get("input_fields") or _fallback_required_fields(record)
        for field in fields:
            if not isinstance(field, dict) or not field.get("required"):
                continue
            path = str(field.get("field") or "")
            if not path or "*" in path:
                continue
            if _is_blank(_get(submission, path)):
                issues.append(
                    _issue(
                        record,
                        field=path,
                        rule_id="required-field",
                        message=f"Thiếu trường thông tin bắt buộc: {field.get('label') or path}.",
                        suggestion="Vui lòng điền trường này chính xác theo giấy tờ gốc.",
                    )
                )

    def _full_name_checks(
        self, record: ProcedureRecord, submission: dict[str, Any], issues: list[Issue]
    ) -> None:
        for path, value in _flatten(submission).items():
            if not path.endswith("full_name") or _is_blank(value):
                continue
            name = str(value).strip()
            if len(name.split()) < 2 or re.search(r"[^A-Za-zÀ-ỹĐđ' -]", name):
                issues.append(
                    _issue(
                        record,
                        field=path,
                        rule_id="full-name-format",
                        message="Họ và tên chưa đúng định dạng.",
                        suggestion="Nhập ít nhất họ và tên, chỉ dùng chữ cái, dấu cách, dấu nháy hoặc dấu gạch nối.",
                    )
                )
                continue
            ascii_name = normalize_ascii(name)
            words = ascii_name.lower().split()
            looks_like_telex = any(
                re.search(r"(?:aa|aw|ee|oo|ow|uw|dd)", word)
                or (len(word) >= 5 and word[-1:] in {"s", "f", "r", "x", "j"})
                for word in words
            )
            if looks_like_telex:
                issues.append(
                    _issue(
                        record,
                        field=path,
                        rule_id="possible-telex-typo",
                        severity="warning",
                        message="Họ tên có dấu hiệu chứa phím gõ Telex chưa được chuyển thành tiếng Việt.",
                        suggestion="Đối chiếu giấy tờ gốc; ví dụ sửa 'Nguyeenx' thành 'Nguyễn'.",
                    )
                )

    def _identity_number_checks(
        self, record: ProcedureRecord, submission: dict[str, Any], issues: list[Issue]
    ) -> None:
        for path, value in _flatten(submission).items():
            if not path.endswith("identity_number") and "identity_number" not in path:
                continue
            if _is_blank(value):
                continue
            digits = re.sub(r"\D", "", str(value))
            if str(value).strip() != digits or len(digits) != 12:
                issues.append(
                    _issue(
                        record,
                        field=path,
                        rule_id="identity-number-format",
                        message="Số định danh không đúng định dạng.",
                        suggestion="Sử dụng đúng 12 chữ số của số định danh cá nhân/CCCD, không có khoảng trắng hoặc ký tự phân cách.",
                    )
                )
            elif len(set(digits)) <= 2 or digits in {"012345678901", "123456789012"}:
                issues.append(
                    _issue(
                        record,
                        field=path,
                        rule_id="identity-number-looks-synthetic",
                        message="Số định danh có dấu hiệu là dữ liệu mẫu hoặc dữ liệu giả.",
                        suggestion="Nhập đúng số trên căn cước/VNeID. GovEase chỉ kiểm tra dấu hiệu bất thường và chưa thể xác minh chủ sở hữu số này.",
                    )
                )

    def _date_checks(
        self,
        record: ProcedureRecord,
        submission: dict[str, Any],
        issues: list[Issue],
        today: date,
    ) -> None:
        for path, value in _flatten(submission).items():
            if not path.endswith("_date") and "date" not in path:
                continue
            if _is_blank(value):
                continue
            parsed = _parse_date(value)
            if parsed is None:
                issues.append(
                    _issue(
                        record,
                        field=path,
                        rule_id="date-format",
                        message="Ngày tháng không hợp lệ.",
                        suggestion="Vui lòng nhập định dạng DD/MM/YYYY hoặc YYYY-MM-DD.",
                    )
                )
            elif "birth_date" in path and parsed > today:
                issues.append(
                    _issue(
                        record,
                        field=path,
                        rule_id="birth-date-future",
                        message="Ngày sinh không thể nằm trong tương lai.",
                        suggestion="Sử dụng ngày sinh trên giấy tờ chính thức.",
                    )
                )

    def _signature_check(
        self, record: ProcedureRecord, submission: dict[str, Any], issues: list[Issue]
    ) -> None:
        signature_present = submission.get("signature_present")
        if signature_present is False:
            issues.append(
                _issue(
                    record,
                    field="signature_present",
                    rule_id="missing-signature",
                    message="Tờ khai đang thiếu chữ ký của người nộp.",
                    suggestion="Vui lòng ký tờ khai trước khi nộp, hoặc xác nhận ký điện tử.",
                )
            )

    def _birth_registration_checks(
        self,
        record: ProcedureRecord,
        submission: dict[str, Any],
        issues: list[Issue],
        today: date,
    ) -> None:
        child_birth_date = _parse_date(_get(submission, "child.birth_date"))
        certificate_birth_date = _parse_date(_get(submission, "birth_certificate.birth_date"))
        if child_birth_date and certificate_birth_date and child_birth_date != certificate_birth_date:
            issues.append(
                _issue(
                    record,
                    field="child.birth_date",
                    rule_id="birth-date-certificate-mismatch",
                    layer="semantic",
                    message="Ngày sinh của trẻ không khớp với Giấy chứng sinh.",
                    suggestion="Nhập chính xác ngày sinh trên Giấy chứng sinh.",
                )
            )

        for role in ("father", "mother"):
            declared = _get(submission, f"{role}.full_name")
            certified = _get(submission, f"birth_certificate.{role}_full_name")
            if declared and certified and _norm(str(declared)) != _norm(str(certified)):
                issues.append(
                    _issue(
                        record,
                        field=f"{role}.full_name",
                        rule_id=f"{role}-name-certificate-mismatch",
                        layer="semantic",
                        message="Họ tên không khớp với Giấy chứng sinh.",
                        suggestion="Sử dụng chính xác họ tên trên Giấy chứng sinh.",
                    )
                )

        certificate_available = _get(submission, "birth_certificate.available")
        if certificate_available is False:
            has_replacement = bool(
                _get(submission, "birth_witness_statement") or _get(submission, "birth_commitment")
            )
            if not has_replacement:
                issues.append(
                    _issue(
                        record,
                        field="birth_certificate",
                        rule_id="missing-birth-certificate-replacement",
                        message="Không có Giấy chứng sinh và chưa cung cấp giấy tờ thay thế.",
                        suggestion="Vui lòng cung cấp Văn bản xác nhận của người làm chứng hoặc Giấy cam đoan về việc sinh.",
                    )
                )

        if child_birth_date and (today - child_birth_date).days > 60:
            issues.append(
                _issue(
                    record,
                    field="child.birth_date",
                    rule_id="late-birth-registration",
                    severity="warning",
                    message="Hồ sơ đăng ký khai sinh có vẻ đã quá hạn 60 ngày.",
                    suggestion="Cơ quan tiếp nhận có thể sẽ yêu cầu bổ sung văn bản giải trình đăng ký muộn.",
                )
            )

    def _temporary_residence_checks(
        self,
        record: ProcedureRecord,
        submission: dict[str, Any],
        issues: list[Issue],
        today: date,
    ) -> None:
        temporary_address = _get(submission, "temporary_address")
        permanent_address = _get(submission, "permanent_address")

        for path, address in (("temporary_address", temporary_address), ("permanent_address", permanent_address)):
            if not isinstance(address, dict):
                continue
            missing = [
                key
                for key in ("province_code", "district_code", "ward_code", "detail")
                if _is_blank(address.get(key))
            ]
            if missing:
                issues.append(
                    _issue(
                        record,
                        field=path,
                        rule_id="incomplete-administrative-address",
                        message="Địa chỉ chưa đầy đủ đơn vị hành chính hoặc địa chỉ chi tiết.",
                        suggestion="Chọn đủ tỉnh/thành phố, quận/huyện, xã/phường và nhập số nhà, đường/ngõ/ngách hoặc thôn/tổ.",
                    )
                )
            elif len(str(address.get("detail", "")).strip()) < 5:
                issues.append(
                    _issue(
                        record,
                        field=path,
                        rule_id="address-detail-too-short",
                        message="Phần địa chỉ chi tiết quá ngắn để xác định nơi cư trú.",
                        suggestion="Nhập rõ số nhà và tên đường/ngõ/ngách, hoặc thôn/tổ dân phố.",
                    )
                )

        if temporary_address and permanent_address and _norm(str(temporary_address)) == _norm(str(permanent_address)):
            issues.append(
                _issue(
                    record,
                    field="temporary_address",
                    rule_id="temporary-address-equals-permanent",
                    layer="semantic",
                    message="Địa chỉ tạm trú đang trùng với địa chỉ thường trú.",
                    suggestion="Chỉ đăng ký tạm trú khi sinh sống ở nơi khác với thường trú.",
                )
            )

        start_date = _parse_date(_get(submission, "stay_start_date"))
        end_date = _parse_date(_get(submission, "stay_end_date"))
        if start_date and end_date and end_date <= start_date:
            issues.append(
                _issue(
                    record,
                    field="stay_end_date",
                    rule_id="stay-end-before-start",
                    message="Ngày kết thúc tạm trú phải sau ngày bắt đầu.",
                    suggestion="Vui lòng sửa lại thời hạn tạm trú.",
                )
            )

        if _is_blank(_get(submission, "accommodation_proof")):
            issues.append(
                _issue(
                    record,
                    field="accommodation_proof",
                    rule_id="missing-accommodation-proof",
                    message="Thiếu giấy tờ chứng minh chỗ ở hợp pháp.",
                    suggestion="Vui lòng đính kèm Hợp đồng thuê nhà hoặc giấy tờ chứng minh chỗ ở khác.",
                )
            )

        if _get(submission, "applicant.is_minor") is True and _is_blank(_get(submission, "guardian_consent")):
            issues.append(
                _issue(
                    record,
                    field="guardian_consent",
                    rule_id="minor-missing-guardian-consent",
                    message="Người chưa thành niên cần có sự đồng ý của cha mẹ/người giám hộ.",
                    suggestion="Vui lòng đính kèm văn bản đồng ý của cha mẹ/người giám hộ.",
                )
            )


def _fallback_required_fields(record: ProcedureRecord) -> list[dict[str, Any]]:
    title_key = _norm(record.title)
    if record.code == "1.004194" or "tam tru" in title_key:
        return [
            {"field": "applicant.full_name", "label": "Applicant full name", "required": True},
            {"field": "applicant.identity_number", "label": "Applicant identity number", "required": True},
            {"field": "temporary_address", "label": "Temporary address", "required": True},
            {"field": "permanent_address", "label": "Permanent address", "required": True},
            {"field": "stay_start_date", "label": "Stay start date", "required": True},
            {"field": "stay_end_date", "label": "Stay end date", "required": True},
            {"field": "accommodation_proof", "label": "Accommodation proof", "required": True},
        ]
    return []


def _issue(
    record: ProcedureRecord,
    *,
    field: str,
    rule_id: str,
    message: str,
    suggestion: str,
    severity: str = "error",
    layer: str = "rules",
    evidence: str | None = None,
) -> Issue:
    return {
        "field": field,
        "rule_id": rule_id,
        "severity": severity,
        "layer": layer,
        "message": message,
        "suggestion": suggestion,
        "source_url": record.source_url,
        "evidence": evidence or f"Validation rule {rule_id} for procedure {record.code or record.id}.",
        "blocking": severity == "error",
    }


def _get(data: dict[str, Any], path: str) -> Any:
    current: Any = data
    for part in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def _flatten(data: Any, prefix: str = "") -> dict[str, Any]:
    if not isinstance(data, dict):
        return {prefix: data} if prefix else {}
    flattened: dict[str, Any] = {}
    for key, value in data.items():
        path = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, dict):
            flattened.update(_flatten(value, path))
        else:
            flattened[path] = value
    return flattened


def normalize_ascii(value: str) -> str:
    value = value.replace("Đ", "D").replace("đ", "d")
    return "".join(
        character for character in unicodedata.normalize("NFKD", value)
        if not unicodedata.combining(character)
    )


def _is_blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _parse_date(value: Any) -> date | None:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not value.strip():
        return None
    value = value.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _norm(value: str) -> str:
    value = value.lower().replace("đ", "d")
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return " ".join(value.split())


def _dedupe_issues(issues: list[Issue]) -> list[Issue]:
    seen: set[tuple[str, str]] = set()
    deduped: list[Issue] = []
    for issue in issues:
        key = (str(issue["field"]), str(issue["rule_id"]))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(issue)
    return deduped
