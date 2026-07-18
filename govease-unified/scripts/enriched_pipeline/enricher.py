from __future__ import annotations

from typing import Any

from raw_markdown_pipeline.utils import compact_whitespace, slugify


SUPPORTED_GROUPS = {
    "co_con_nho",
    "hon_nhan_gia_dinh",
    "cu_tru_giay_to",
    "suc_khoe_y_te",
    "hoc_tap",
    "dien_luc_nha_o_dat_dai",
    "giai_quyet_khieu_kien",
    "huu_tri",
    "nguoi_than_qua_doi",
    "phuong_tien_nguoi_lai",
    "viec_lam",
}


def enrich_normalized_structured(
    normalized: dict[str, Any],
    mapping_row: dict[str, Any],
) -> dict[str, Any]:
    group_key = mapping_row.get("group_key")
    title = normalized.get("source", {}).get("title") or ""
    workflow_family = mapping_row.get("workflow_family")
    subflow = _extract_subflow(mapping_row.get("notes"))

    highlight_documents = _pick_highlight_documents(normalized)
    special_cases = _derive_special_cases(normalized)
    common_errors = _derive_common_errors(normalized)
    candidate_input_fields = _build_candidate_fields(group_key, title, normalized, subflow)
    validation_hints = _build_validation_hints(group_key, title, normalized)

    return {
        "schema_version": "1.0",
        "enricher_version": "0.2.0",
        "source": {
            "procedure_code": normalized.get("source", {}).get("procedure_code"),
            "title": title,
            "group_key": group_key,
            "workflow_family": workflow_family,
            "subflow": subflow,
        },
        "experience": {
            "entry_label": _entry_label(group_key, subflow),
            "overview_summary": _build_overview_summary(group_key, title, normalized, subflow),
            "next_step_summary": _build_next_step_summary(group_key, normalized),
            "tone": "supportive_public_service",
        },
        "guidance": {
            "highlight_documents": highlight_documents,
            "special_cases": special_cases,
            "common_errors": common_errors,
            "validation_hints": validation_hints,
        },
        "intake": {
            "candidate_input_fields": candidate_input_fields,
            "suggested_clarifying_questions": _build_clarifying_questions(group_key, title, subflow),
        },
        "ui_hints": {
            "primary_channel": _primary_channel(normalized),
            "result_label": _primary_result_label(normalized),
            "time_badge": _primary_time_badge(normalized),
            "document_count_badge": normalized.get("documents", {}).get("document_count", 0),
        },
        "provenance": {
            "generator": "workflow_domain_enricher",
            "derivation_mode": "rule_based_semantic_enrichment",
            "supported_group": group_key in SUPPORTED_GROUPS,
        },
    }


def _extract_subflow(value: str | None) -> str | None:
    text = compact_whitespace(value or "")
    if "/" not in text:
        return None
    return text.split("/")[-1]


def _entry_label(group_key: str | None, subflow: str | None) -> str:
    if group_key == "co_con_nho":
        return "Hỗ trợ thủ tục cho trẻ em"
    if group_key == "hon_nhan_gia_dinh":
        return "Hỗ trợ hộ tịch và gia đình"
    if group_key == "cu_tru_giay_to":
        return "Hỗ trợ cư trú và giấy tờ"
    if group_key == "suc_khoe_y_te":
        return "Hỗ trợ y tế và bảo hiểm"
    if group_key == "hoc_tap":
        return "Hỗ trợ giáo dục và học tập"
    if group_key == "dien_luc_nha_o_dat_dai":
        return "Hỗ trợ nhà ở, đất đai và điện lực"
    if group_key == "giai_quyet_khieu_kien":
        return "Hỗ trợ khiếu nại và phản ánh"
    if group_key == "huu_tri":
        return "Hỗ trợ chế độ hưu trí"
    if group_key == "nguoi_than_qua_doi":
        return "Hỗ trợ chế độ cho thân nhân"
    if group_key == "phuong_tien_nguoi_lai":
        return "Hỗ trợ phương tiện và người lái"
    if group_key == "viec_lam":
        return "Hỗ trợ việc làm và lao động"
    return "Hỗ trợ thủ tục hành chính"


def _build_overview_summary(group_key: str | None, title: str, normalized: dict[str, Any], subflow: str | None) -> str:
    time_text = _primary_time_badge(normalized) or "theo thời hạn của cơ quan xử lý"
    result_label = _result_summary_label(normalized)

    if group_key == "co_con_nho":
        if subflow == "lien_thong_khai_sinh_bao_hiem_cu_tru":
            return f"Thủ tục này xử lý liên thông cho trẻ nhỏ, giúp gia đình hoàn tất khai sinh, cư trú và bảo hiểm trong cùng một quy trình. Kết quả thường nhận được là {result_label}. Thời gian xử lý tham khảo: {time_text}."
        if subflow == "bao_hiem_y_te":
            return f"Thủ tục này hỗ trợ hoàn tất khai sinh kèm cấp thẻ bảo hiểm y tế cho trẻ dưới 6 tuổi. Kết quả thường nhận được là {result_label}. Thời gian xử lý tham khảo: {time_text}."
        return f"Thủ tục này thuộc nhóm giấy tờ cho trẻ nhỏ, thường dùng để đăng ký hoặc cập nhật thông tin khai sinh. Kết quả thường nhận được là {result_label}. Thời gian xử lý tham khảo: {time_text}."

    if group_key == "hon_nhan_gia_dinh":
        return f"Thủ tục này thuộc nhóm hộ tịch gia đình, thường yêu cầu đối chiếu thông tin nhân thân và tình trạng hôn nhân của các bên. Kết quả thường nhận được là {result_label}. Thời gian xử lý tham khảo: {time_text}."

    if group_key == "cu_tru_giay_to":
        return f"Thủ tục này thuộc nhóm cư trú và giấy tờ, thường cần kiểm tra thông tin định danh hoặc hồ sơ giấy tờ chuyên ngành. Kết quả thường nhận được là {result_label}. Thời gian xử lý tham khảo: {time_text}."

    if group_key == "suc_khoe_y_te":
        if "bhyt" in title.lower() or "bảo hiểm y tế" in title.lower():
            return f"Thủ tục này thuộc nhóm y tế và bảo hiểm, thường dùng để đăng ký, điều chỉnh hoặc xác nhận quyền lợi bảo hiểm y tế. Kết quả thường nhận được là {result_label}. Thời gian xử lý tham khảo: {time_text}."
        return f"Thủ tục này thuộc nhóm y tế, thường cần đối chiếu thông tin người bệnh, đơn vị tiếp nhận hoặc quyền lợi chuyên ngành. Kết quả thường nhận được là {result_label}. Thời gian xử lý tham khảo: {time_text}."

    if group_key == "hoc_tap":
        return f"Thủ tục này thuộc nhóm giáo dục và học tập, thường liên quan đến hồ sơ đào tạo, văn bằng hoặc điều kiện học tập của người học. Kết quả thường nhận được là {result_label}. Thời gian xử lý tham khảo: {time_text}."

    if group_key == "dien_luc_nha_o_dat_dai":
        if "giấy chứng nhận" in title.lower() or "quyền sử dụng đất" in title.lower():
            return f"Thủ tục này thuộc nhóm đất đai và nhà ở, thường dùng để cấp, đổi hoặc cập nhật giấy chứng nhận và thông tin tài sản gắn liền với đất. Kết quả thường nhận được là {result_label}. Thời gian xử lý tham khảo: {time_text}."
        return f"Thủ tục này thuộc nhóm nhà ở, đất đai và điện lực, thường cần kiểm tra hiện trạng hồ sơ tài sản hoặc điều kiện hạ tầng liên quan. Kết quả thường nhận được là {result_label}. Thời gian xử lý tham khảo: {time_text}."

    if group_key == "giai_quyet_khieu_kien":
        return f"Thủ tục này thuộc nhóm khiếu nại và phản ánh, thường cần trình bày rõ nội dung vụ việc, quyết định hoặc hành vi bị khiếu nại và căn cứ kèm theo. Kết quả thường nhận được là {result_label}. Thời gian xử lý tham khảo: {time_text}."

    if group_key == "huu_tri":
        return f"Thủ tục này thuộc nhóm hưu trí, thường dùng để xác định điều kiện nghỉ hưu, trợ cấp hoặc chế độ hưởng theo hồ sơ bảo hiểm xã hội. Kết quả thường nhận được là {result_label}. Thời gian xử lý tham khảo: {time_text}."

    if group_key == "nguoi_than_qua_doi":
        return f"Thủ tục này thuộc nhóm hỗ trợ thân nhân người đã mất, thường liên quan đến mai táng phí, tử tuất hoặc chế độ phát sinh sau khi người hưởng qua đời. Kết quả thường nhận được là {result_label}. Thời gian xử lý tham khảo: {time_text}."

    if group_key == "phuong_tien_nguoi_lai":
        if "giấy phép lái xe" in title.lower() or "lái xe" in title.lower():
            return f"Thủ tục này thuộc nhóm phương tiện và người lái, thường dùng để cấp, đổi hoặc xác nhận hồ sơ liên quan đến giấy phép lái xe. Kết quả thường nhận được là {result_label}. Thời gian xử lý tham khảo: {time_text}."
        return f"Thủ tục này thuộc nhóm phương tiện và đăng kiểm, thường cần đối chiếu hồ sơ kỹ thuật, đăng ký hoặc chứng nhận an toàn của phương tiện. Kết quả thường nhận được là {result_label}. Thời gian xử lý tham khảo: {time_text}."

    if group_key == "viec_lam":
        if "giấy phép lao động" in title.lower() or "người nước ngoài" in title.lower():
            return f"Thủ tục này thuộc nhóm việc làm, thường liên quan đến lao động nước ngoài, nghĩa vụ báo cáo hoặc xác nhận điều kiện làm việc tại Việt Nam. Kết quả thường nhận được là {result_label}. Thời gian xử lý tham khảo: {time_text}."
        return f"Thủ tục này thuộc nhóm việc làm và lao động, thường cần kiểm tra hồ sơ nghề nghiệp, đơn vị sử dụng lao động hoặc điều kiện hưởng chế độ liên quan. Kết quả thường nhận được là {result_label}. Thời gian xử lý tham khảo: {time_text}."

    return f"{title} là một thủ tục hành chính. Kết quả thường nhận được là {result_label}. Thời gian xử lý tham khảo: {time_text}."


def _build_next_step_summary(group_key: str | None, normalized: dict[str, Any]) -> str:
    channels = normalized.get("submission", {}).get("channels", [])
    docs = normalized.get("documents", {})
    doc_count = docs.get("document_count", 0)
    channel_text = _channel_summary(channels)
    doc_text = _document_tracking_summary(doc_count)
    if group_key == "co_con_nho":
        return f"Chuẩn bị trước các giấy tờ cốt lõi của trẻ và người đi làm thủ tục, sau đó chọn kênh nộp phù hợp: {channel_text}. {doc_text}"
    if group_key == "hon_nhan_gia_dinh":
        return f"Nên rà trước giấy tờ nhân thân của hai bên và các điều kiện đặc biệt nếu có yếu tố nước ngoài hoặc ủy quyền. {doc_text}"
    if group_key == "cu_tru_giay_to":
        return f"Nên kiểm tra trước giấy tờ định danh, nơi nộp và mẫu biểu liên quan, rồi chọn kênh nộp phù hợp: {channel_text}. {doc_text}"
    if group_key == "suc_khoe_y_te":
        return f"Nên xác định rõ đối tượng tham gia, quyền lợi hoặc nhu cầu điều chỉnh hồ sơ y tế trước khi nộp. Có thể chọn kênh nộp phù hợp: {channel_text}. {doc_text}"
    if group_key == "hoc_tap":
        return f"Nên rà trước thông tin người học, cơ sở đào tạo và loại kết quả cần xin xác nhận hoặc cấp lại. Có thể chọn kênh nộp phù hợp: {channel_text}. {doc_text}"
    if group_key == "dien_luc_nha_o_dat_dai":
        return f"Nên chuẩn bị trước thông tin thửa đất, tài sản hoặc địa điểm tiếp nhận, rồi chọn kênh nộp phù hợp: {channel_text}. {doc_text}"
    if group_key == "giai_quyet_khieu_kien":
        return f"Nên tóm tắt rõ nội dung khiếu nại, quyết định hoặc hành vi liên quan và chuẩn bị tài liệu chứng minh trước khi nộp. Có thể chọn kênh nộp phù hợp: {channel_text}. {doc_text}"
    if group_key == "huu_tri":
        return f"Nên rà trước quá trình đóng bảo hiểm, mốc tuổi và loại chế độ muốn hưởng trước khi nộp. Có thể chọn kênh nộp phù hợp: {channel_text}. {doc_text}"
    if group_key == "nguoi_than_qua_doi":
        return f"Nên chuẩn bị giấy tờ của người đã mất, thân nhân và căn cứ hưởng chế độ trước khi nộp. Có thể chọn kênh nộp phù hợp: {channel_text}. {doc_text}"
    if group_key == "phuong_tien_nguoi_lai":
        return f"Nên kiểm tra trước loại phương tiện hoặc loại giấy phép cần xử lý, cùng hồ sơ kỹ thuật hoặc nhân thân liên quan. Có thể chọn kênh nộp phù hợp: {channel_text}. {doc_text}"
    if group_key == "viec_lam":
        return f"Nên xác định rõ nhu cầu lao động, hồ sơ nghề nghiệp hoặc chế độ cần giải quyết trước khi nộp. Có thể chọn kênh nộp phù hợp: {channel_text}. {doc_text}"
    return f"Chuẩn bị hồ sơ và chọn kênh nộp phù hợp: {channel_text}. {doc_text}"


def _pick_highlight_documents(normalized: dict[str, Any]) -> list[dict[str, Any]]:
    documents = normalized.get("documents", {})
    candidates = []
    for bucket in ("required", "conditional", "presented"):
        for item in documents.get(bucket, [])[:6]:
            candidates.append(
                {
                    "bucket": bucket,
                    "name": item.get("name"),
                    "conditions": item.get("conditions") or [],
                    "attachment_path": item.get("attachment_path"),
                }
            )
    return candidates[:6]


def _derive_special_cases(normalized: dict[str, Any]) -> list[str]:
    pool = _collect_text_pool(normalized)
    rules = {
        "Có yếu tố nước ngoài": ["yếu tố nước ngoài", "nước ngoài", "nước láng giềng"],
        "Có thể cần giấy tờ ủy quyền": ["ủy quyền"],
        "Có trường hợp hồ sơ điện tử thay thế bản giấy": ["bản điện tử", "trực tuyến", "ký số"],
        "Có tình huống trẻ bị bỏ rơi hoặc thiếu giấy chứng sinh": ["bị bỏ rơi", "không có Giấy chứng sinh", "cam đoan về việc sinh"],
        "Có thể cần chứng cứ quan hệ cha, mẹ, con": ["quan hệ cha", "quan hệ mẹ", "nhận cha, mẹ, con"],
        "Có kiểm tra dữ liệu cư trú/định danh": ["cơ sở dữ liệu quốc gia", "nơi cư trú", "định danh"],
        "Có thể cần đối chiếu quyền lợi bảo hiểm hoặc tuyến chuyên môn": ["bhyt", "bảo hiểm y tế", "khám chữa bệnh", "chuyển tuyến"],
        "Có thể cần đối chiếu thông tin thửa đất hoặc giấy chứng nhận": ["thửa đất", "giấy chứng nhận", "quyền sử dụng đất"],
        "Có thể cần xác minh hồ sơ học tập hoặc văn bằng": ["văn bằng", "bảng điểm", "người học", "nghiên cứu sinh"],
        "Có thể cần tài liệu chứng minh nội dung khiếu nại": ["khiếu nại", "quyết định hành chính", "hành vi hành chính"],
        "Có thể cần đối chiếu quá trình đóng bảo hiểm để giải quyết chế độ": ["lương hưu", "hưu trí", "bảo hiểm xã hội", "trợ cấp hằng tháng"],
        "Có thể cần hồ sơ tử tuất hoặc mai táng phí": ["mai táng phí", "tử tuất", "người chết", "thân nhân"],
        "Có thể cần hồ sơ kỹ thuật phương tiện hoặc giấy phép lái xe": ["đăng kiểm", "xe cơ giới", "giấy phép lái xe", "phương tiện"],
        "Có thể cần xác minh quan hệ lao động hoặc giấy phép làm việc": ["việc làm", "lao động", "giấy phép lao động", "người sử dụng lao động"],
    }
    results = []
    lowered_pool = " ".join(pool).lower()
    for label, keywords in rules.items():
        if any(keyword.lower() in lowered_pool for keyword in keywords):
            results.append(label)
    return results


def _derive_common_errors(normalized: dict[str, Any]) -> list[str]:
    pool = _collect_text_pool(normalized)
    lowered_pool = " ".join(pool).lower()
    errors = []
    if "không khai thác được thông tin" in lowered_pool:
        errors.append("Thông tin định danh hoặc cư trú không khớp với dữ liệu dân cư.")
    if "ủy quyền" in lowered_pool:
        errors.append("Thiếu giấy tờ hoặc nội dung ủy quyền phù hợp.")
    if "giấy chứng sinh" in lowered_pool:
        errors.append("Thiếu giấy chứng sinh hoặc giấy thay thế hợp lệ.")
    if "người nước ngoài" in lowered_pool or "nước ngoài" in lowered_pool:
        errors.append("Thiếu giấy tờ hợp pháp hóa hoặc giấy tờ nhân thân của phía nước ngoài.")
    if "phiếu" in lowered_pool or "mẫu" in lowered_pool:
        errors.append("Điền sai mẫu tờ khai hoặc chọn sai biểu mẫu đi kèm.")
    if "bhyt" in lowered_pool or "bảo hiểm y tế" in lowered_pool:
        errors.append("Sai nhóm đối tượng tham gia hoặc thông tin quyền lợi bảo hiểm y tế.")
    if "giấy chứng nhận" in lowered_pool or "thửa đất" in lowered_pool:
        errors.append("Thông tin thửa đất, tài sản hoặc giấy chứng nhận chưa khớp với hồ sơ hiện có.")
    if "văn bằng" in lowered_pool or "bảng điểm" in lowered_pool or "nghiên cứu sinh" in lowered_pool:
        errors.append("Thiếu minh chứng học tập, văn bằng hoặc xác nhận từ cơ sở đào tạo.")
    if "khiếu nại" in lowered_pool:
        errors.append("Nội dung khiếu nại chưa nêu rõ quyết định, hành vi hoặc tài liệu chứng minh liên quan.")
    if "lương hưu" in lowered_pool or "hưu trí" in lowered_pool:
        errors.append("Thiếu thông tin về thời gian tham gia bảo hiểm hoặc chưa xác định đúng chế độ hưu trí.")
    if "mai táng phí" in lowered_pool or "tử tuất" in lowered_pool:
        errors.append("Thiếu giấy tờ về người đã mất hoặc căn cứ xác định thân nhân hưởng chế độ.")
    if "đăng kiểm" in lowered_pool or "giấy phép lái xe" in lowered_pool:
        errors.append("Thiếu hồ sơ kỹ thuật phương tiện hoặc thông tin giấy phép lái xe cần đối chiếu.")
    if "lao động" in lowered_pool or "giấy phép lao động" in lowered_pool:
        errors.append("Thiếu hồ sơ về vị trí việc làm, đơn vị sử dụng lao động hoặc điều kiện làm việc áp dụng.")
    return errors[:5]


def _build_candidate_fields(group_key: str | None, title: str, normalized: dict[str, Any], subflow: str | None) -> list[dict[str, Any]]:
    base_fields: list[dict[str, Any]] = []
    if group_key == "co_con_nho":
        base_fields.extend(
            [
                _field("child_full_name", "Tên trẻ", "text", required=False),
                _field("child_birth_date", "Ngày sinh của trẻ", "date", required=False),
                _field("child_birth_place", "Nơi sinh", "text", required=False),
                _field("requester_relationship", "Quan hệ với trẻ", "enum", required=True),
                _field("has_foreign_element", "Có yếu tố nước ngoài", "boolean", required=True),
            ]
        )
        if "nhận cha, mẹ, con" in title.lower():
            base_fields.append(_field("relationship_proof_available", "Có giấy tờ chứng minh quan hệ cha mẹ con", "boolean", required=True))
        if subflow in {"bao_hiem_y_te", "lien_thong_khai_sinh_bao_hiem_cu_tru"}:
            base_fields.append(_field("needs_health_insurance", "Cần liên thông bảo hiểm y tế", "boolean", required=True))
        if subflow == "lien_thong_khai_sinh_bao_hiem_cu_tru":
            base_fields.append(_field("needs_residence_registration", "Cần liên thông đăng ký thường trú", "boolean", required=True))

    elif group_key == "hon_nhan_gia_dinh":
        base_fields.extend(
            [
                _field("party_one_full_name", "Người thứ nhất", "text", required=True),
                _field("party_two_full_name", "Người thứ hai", "text", required=True),
                _field("has_foreign_element", "Có yếu tố nước ngoài", "boolean", required=True),
                _field("current_marital_status_docs", "Có giấy tờ chứng minh tình trạng hôn nhân", "boolean", required=True),
                _field("submission_at_border_area", "Nộp tại khu vực biên giới", "boolean", required=False),
            ]
        )

    elif group_key == "cu_tru_giay_to":
        base_fields.extend(
            [
                _field("document_request_type", "Loại giấy tờ cần xử lý", "text", required=True),
                _field("submission_channel_preference", "Kênh nộp dự kiến", "enum", required=False),
                _field("identity_document_available", "Có giấy tờ định danh", "boolean", required=True),
                _field("residency_or_status_known", "Biết rõ nơi cư trú hoặc tình trạng hiện tại", "boolean", required=False),
            ]
        )
        if "căn cước" in title.lower():
            base_fields.append(_field("age_over_14", "Người làm thủ tục từ đủ 14 tuổi", "boolean", required=True))
        if "hộ chiếu" in title.lower():
            base_fields.append(_field("passport_status", "Tình trạng hộ chiếu hiện tại", "enum", required=False))

    elif group_key == "suc_khoe_y_te":
        base_fields.extend(
            [
                _field("request_subject", "Đối tượng làm thủ tục", "text", required=True),
                _field("insurance_or_medical_need", "Nhu cầu bảo hiểm hoặc y tế", "text", required=True),
                _field("submission_channel_preference", "Kênh nộp dự kiến", "enum", required=False),
                _field("has_insurance_number", "Đã có mã BHXH/BHYT", "boolean", required=False),
            ]
        )
        if "bhyt" in title.lower() or "bảo hiểm y tế" in title.lower():
            base_fields.append(_field("insurance_participation_group", "Nhóm tham gia BHYT", "enum", required=True))
        if "cấp thẻ" in title.lower():
            base_fields.append(_field("needs_card_issue", "Cần cấp mới hoặc cấp lại thẻ", "boolean", required=True))

    elif group_key == "hoc_tap":
        base_fields.extend(
            [
                _field("learner_full_name", "Tên người học", "text", required=True),
                _field("education_record_type", "Loại hồ sơ học tập cần xử lý", "text", required=True),
                _field("education_institution", "Cơ sở đào tạo liên quan", "text", required=False),
                _field("submission_channel_preference", "Kênh nộp dự kiến", "enum", required=False),
            ]
        )
        if "tiến sĩ" in title.lower():
            base_fields.append(_field("doctoral_stage", "Giai đoạn đào tạo tiến sĩ", "enum", required=False))
        if "văn bằng" in title.lower() or "bằng" in title.lower():
            base_fields.append(_field("certificate_or_degree_type", "Loại văn bằng/chứng chỉ", "text", required=False))

    elif group_key == "dien_luc_nha_o_dat_dai":
        base_fields.extend(
            [
                _field("property_or_service_need", "Nhu cầu về đất đai, nhà ở hoặc điện lực", "text", required=True),
                _field("property_location", "Địa điểm tài sản hoặc nơi sử dụng dịch vụ", "text", required=True),
                _field("submission_channel_preference", "Kênh nộp dự kiến", "enum", required=False),
                _field("has_current_certificate", "Đã có giấy tờ/tài liệu hiện trạng", "boolean", required=False),
            ]
        )
        if "giấy chứng nhận" in title.lower():
            base_fields.append(_field("certificate_status", "Tình trạng giấy chứng nhận hiện tại", "enum", required=False))
        if "thửa đất" in title.lower() or "quyền sử dụng đất" in title.lower():
            base_fields.append(_field("land_plot_identifier", "Thông tin thửa đất", "text", required=False))

    elif group_key == "giai_quyet_khieu_kien":
        base_fields.extend(
            [
                _field("complaint_subject", "Nội dung khiếu nại chính", "text", required=True),
                _field("decision_or_behavior_target", "Quyết định hoặc hành vi bị khiếu nại", "text", required=True),
                _field("has_supporting_evidence", "Có tài liệu chứng minh kèm theo", "boolean", required=True),
                _field("submission_channel_preference", "Kênh nộp dự kiến", "enum", required=False),
            ]
        )

    elif group_key == "huu_tri":
        base_fields.extend(
            [
                _field("insured_person_name", "Người hưởng chế độ", "text", required=True),
                _field("retirement_or_allowance_need", "Nhu cầu hưởng chế độ hưu trí/trợ cấp", "text", required=True),
                _field("social_insurance_participation_known", "Đã rõ quá trình tham gia BHXH", "boolean", required=True),
                _field("submission_channel_preference", "Kênh nộp dự kiến", "enum", required=False),
            ]
        )
        if "lương hưu" in title.lower():
            base_fields.append(_field("retirement_age_status", "Đã đến mốc tuổi hưởng chế độ", "boolean", required=False))

    elif group_key == "nguoi_than_qua_doi":
        base_fields.extend(
            [
                _field("deceased_person_name", "Người đã mất", "text", required=True),
                _field("claimant_relationship", "Quan hệ của người nộp với người đã mất", "enum", required=True),
                _field("support_benefit_type", "Loại chế độ cần giải quyết", "text", required=True),
                _field("submission_channel_preference", "Kênh nộp dự kiến", "enum", required=False),
            ]
        )

    elif group_key == "phuong_tien_nguoi_lai":
        base_fields.extend(
            [
                _field("vehicle_or_license_need", "Nhu cầu về phương tiện hoặc giấy phép", "text", required=True),
                _field("vehicle_or_person_identifier", "Thông tin phương tiện hoặc người lái", "text", required=True),
                _field("submission_channel_preference", "Kênh nộp dự kiến", "enum", required=False),
                _field("has_technical_or_identity_documents", "Đã có hồ sơ kỹ thuật hoặc giấy tờ nhân thân", "boolean", required=False),
            ]
        )
        if "giấy phép lái xe" in title.lower():
            base_fields.append(_field("driver_license_status", "Tình trạng giấy phép lái xe hiện tại", "enum", required=False))

    elif group_key == "viec_lam":
        base_fields.extend(
            [
                _field("employment_need", "Nhu cầu việc làm hoặc lao động", "text", required=True),
                _field("worker_or_employer_info", "Thông tin người lao động hoặc đơn vị sử dụng lao động", "text", required=True),
                _field("submission_channel_preference", "Kênh nộp dự kiến", "enum", required=False),
                _field("has_supporting_employment_documents", "Đã có hồ sơ lao động liên quan", "boolean", required=False),
            ]
        )
        if "giấy phép lao động" in title.lower():
            base_fields.append(_field("foreign_worker_case", "Hồ sơ có liên quan lao động nước ngoài", "boolean", required=True))

    return base_fields


def _build_validation_hints(group_key: str | None, title: str, normalized: dict[str, Any]) -> list[str]:
    hints = []
    if normalized.get("submission", {}).get("channels"):
        hints.append("Nên xác định trước kênh nộp hồ sơ để biết có cần bản giấy, bản điện tử hay xuất trình trực tiếp.")
    if normalized.get("documents", {}).get("forms"):
        hints.append("Có mẫu biểu đính kèm, nên kiểm tra đúng biểu mẫu trước khi nộp.")
    if group_key in {"co_con_nho", "hon_nhan_gia_dinh"}:
        hints.append("Thông tin hộ tịch giữa các giấy tờ phải thống nhất về họ tên, ngày sinh và quan hệ liên quan.")
    if group_key == "cu_tru_giay_to":
        hints.append("Nên đối chiếu trước dữ liệu định danh và nơi cư trú để tránh bị yêu cầu bổ sung.")
    if group_key == "suc_khoe_y_te":
        hints.append("Nên xác định đúng nhóm đối tượng, mã số bảo hiểm và quyền lợi áp dụng trước khi nộp.")
    if group_key == "hoc_tap":
        hints.append("Nên rà lại thông tin người học, cơ sở đào tạo và loại xác nhận hoặc văn bằng cần xin.")
    if group_key == "dien_luc_nha_o_dat_dai":
        hints.append("Nên đối chiếu trước thông tin thửa đất, tài sản hoặc hiện trạng hồ sơ để tránh bị yêu cầu chỉnh sửa.")
    if group_key == "giai_quyet_khieu_kien":
        hints.append("Nên nêu rõ diễn biến vụ việc, quyết định hoặc hành vi bị khiếu nại và chuẩn bị tài liệu chứng minh.")
    if group_key == "huu_tri":
        hints.append("Nên rà lại quá trình tham gia bảo hiểm, độ tuổi và loại chế độ muốn hưởng trước khi nộp.")
    if group_key == "nguoi_than_qua_doi":
        hints.append("Nên kiểm tra kỹ giấy tờ của người đã mất, thân nhân và căn cứ phát sinh chế độ.")
    if group_key == "phuong_tien_nguoi_lai":
        hints.append("Nên đối chiếu trước thông tin phương tiện, hồ sơ kỹ thuật hoặc giấy phép lái xe liên quan.")
    if group_key == "viec_lam":
        hints.append("Nên xác định đúng nhóm thủ tục lao động, đơn vị liên quan và hồ sơ nghề nghiệp cần xuất trình.")
    if "yếu tố nước ngoài" in title.lower():
        hints.append("Nếu có giấy tờ nước ngoài, cần kiểm tra yêu cầu hợp pháp hóa hoặc xác nhận tương đương.")
    return hints


def _build_clarifying_questions(group_key: str | None, title: str, subflow: str | None) -> list[str]:
    if group_key == "co_con_nho":
        questions = [
            "Bé đã có giấy chứng sinh hoặc giấy tờ thay thế chưa?",
            "Thủ tục này có liên quan đến yếu tố nước ngoài, mang thai hộ hoặc trẻ bị bỏ rơi không?",
        ]
        if subflow in {"bao_hiem_y_te", "lien_thong_khai_sinh_bao_hiem_cu_tru"}:
            questions.append("Bạn muốn xử lý liên thông luôn bảo hiểm hoặc thường trú cho trẻ không?")
        return questions
    if group_key == "hon_nhan_gia_dinh":
        return [
            "Hai bên đã có đủ giấy tờ nhân thân và tình trạng hôn nhân chưa?",
            "Hồ sơ có yếu tố nước ngoài, khu vực biên giới hoặc ủy quyền không?",
        ]
    if group_key == "cu_tru_giay_to":
        return [
            "Bạn đang xử lý giấy tờ gì và muốn nộp trực tiếp hay trực tuyến?",
            "Thông tin định danh và nơi cư trú hiện tại đã sẵn sàng để đối chiếu chưa?",
        ]
    if group_key == "suc_khoe_y_te":
        return [
            "Bạn đang muốn đăng ký, điều chỉnh hay xác nhận quyền lợi y tế hoặc bảo hiểm nào?",
            "Bạn đã có mã BHXH/BHYT hoặc thông tin đơn vị tiếp nhận liên quan chưa?",
        ]
    if group_key == "hoc_tap":
        return [
            "Bạn đang cần xử lý hồ sơ học tập, văn bằng hay xác nhận nào?",
            "Người học và cơ sở đào tạo liên quan đã xác định rõ chưa?",
        ]
    if group_key == "dien_luc_nha_o_dat_dai":
        return [
            "Bạn đang xử lý nhu cầu nào về đất đai, nhà ở hoặc điện lực?",
            "Bạn đã có thông tin thửa đất, địa chỉ tài sản hoặc giấy tờ hiện trạng chưa?",
        ]
    if group_key == "giai_quyet_khieu_kien":
        return [
            "Bạn đang khiếu nại về quyết định hay hành vi nào, và thuộc cơ quan nào?",
            "Bạn đã có đơn khiếu nại hoặc tài liệu chứng minh nội dung vụ việc chưa?",
        ]
    if group_key == "huu_tri":
        return [
            "Bạn đang muốn chuẩn bị nghỉ hưu hay giải quyết chế độ hưu trí cụ thể nào?",
            "Quá trình tham gia bảo hiểm và độ tuổi hưởng chế độ đã xác định rõ chưa?",
        ]
    if group_key == "nguoi_than_qua_doi":
        return [
            "Bạn đang cần giải quyết mai táng phí, tử tuất hay chế độ nào cho thân nhân?",
            "Giấy tờ của người đã mất và mối quan hệ của người nộp hồ sơ đã sẵn sàng chưa?",
        ]
    if group_key == "phuong_tien_nguoi_lai":
        return [
            "Bạn đang xử lý hồ sơ cho phương tiện hay cho giấy phép lái xe?",
            "Bạn đã có thông tin nhận diện phương tiện hoặc giấy tờ của người lái chưa?",
        ]
    if group_key == "viec_lam":
        return [
            "Bạn đang cần giải quyết thủ tục lao động nào cho người lao động hoặc doanh nghiệp?",
            "Hồ sơ nghề nghiệp, đơn vị sử dụng lao động hoặc yếu tố lao động nước ngoài đã rõ chưa?",
        ]
    return []


def _primary_channel(normalized: dict[str, Any]) -> str | None:
    methods = normalized.get("submission", {}).get("methods", [])
    if not methods:
        return None
    return methods[0].get("channel")


def _primary_result_label(normalized: dict[str, Any]) -> str | None:
    primary = normalized.get("results", {}).get("primary_result") or {}
    return primary.get("name")


def _primary_time_badge(normalized: dict[str, Any]) -> str | None:
    timings = normalized.get("submission", {}).get("timing_summary", {}).get("unique_processing_times", [])
    return timings[0] if timings else None


def _result_summary_label(normalized: dict[str, Any]) -> str:
    label = compact_whitespace(_primary_result_label(normalized) or "")
    return label or "kết quả giải quyết theo thủ tục này"


def _channel_label(channel: str | None) -> str:
    return {
        "in_person": "Trực tiếp",
        "online": "Trực tuyến",
        "postal": "Dịch vụ bưu chính",
    }.get(channel or "", compact_whitespace(channel or ""))


def _channel_summary(channels: list[str]) -> str:
    labels = [_channel_label(channel) for channel in channels if compact_whitespace(channel)]
    if not labels:
        return "theo kênh tiếp nhận được cơ quan công bố"
    return ", ".join(labels)


def _document_tracking_summary(doc_count: int) -> str:
    if doc_count <= 0:
        return "Hiện hệ thống chưa trích xuất được checklist giấy tờ rõ ràng, nên bạn cần đối chiếu thêm ở nguồn chính thức."
    if doc_count == 1:
        return "Hiện có 1 mục giấy tờ cần theo dõi trong checklist."
    return f"Hiện có khoảng {doc_count} mục giấy tờ cần theo dõi trong checklist."


def _collect_text_pool(normalized: dict[str, Any]) -> list[str]:
    pool: list[str] = []
    for bucket in ("required", "conditional", "presented"):
        for item in normalized.get("documents", {}).get(bucket, []):
            if item.get("name"):
                pool.append(item["name"])
            pool.extend(item.get("conditions") or [])
    pool.extend(normalized.get("documents", {}).get("notes", []))
    pool.extend(normalized.get("process", {}).get("notes", []))
    return [compact_whitespace(item) for item in pool if compact_whitespace(item)]


def _field(field_id: str, label: str, field_type: str, *, required: bool) -> dict[str, Any]:
    return {
        "field_id": field_id,
        "label": label,
        "field_type": field_type,
        "required": required,
    }
