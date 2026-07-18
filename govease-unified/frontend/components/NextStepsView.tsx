"use client";

import type { IntakeResult, ValidationResult } from "../lib/types";
import { Icon } from "./Icon";
import { WorkflowScrollDock } from "./WorkflowScrollDock";

function buildTimeline(result: IntakeResult, validation: ValidationResult | null) {
  const procedureTitle = result.procedure?.title || "thủ tục của bạn";
  const issues = validation?.issues || [];
  const blocking = issues.filter((issue) => issue.blocking);
  const warnings = issues.filter((issue) => !issue.blocking);
  const submissionHint =
    result.checklist.steps?.[0]?.description ||
    "Hoàn tất tờ khai trực tuyến theo đúng hồ sơ đã rà soát.";

  return [
    {
      title: "Hôm nay",
      body: blocking.length
        ? `Ưu tiên sửa ${blocking.length} nội dung quan trọng trước khi nộp ${procedureTitle.toLowerCase()}.`
        : submissionHint,
      tone: "done",
    },
    {
      title: "Trước khi nộp",
      body: warnings.length
        ? `Xem lại thêm ${warnings.length} lưu ý để giảm rủi ro hồ sơ bị yêu cầu bổ sung.`
        : "Đối chiếu bản gốc, bản sao và chữ ký trước khi gửi hồ sơ.",
      tone: "pending",
    },
    {
      title: "Nơi tiếp nhận",
      body: "Nộp tại cơ quan có thẩm quyền theo hướng dẫn và nguồn chính thống đính kèm trong hồ sơ thủ tục.",
      tone: "location",
    },
  ];
}

export function NextStepsView({
  result,
  validation,
  onBack,
  onRestart,
}: {
  result: IntakeResult;
  validation: ValidationResult | null;
  onBack: () => void;
  onRestart: () => void;
}) {
  const steps = buildTimeline(result, validation);
  const issueCount = validation?.issues.length || 0;
  const ready = validation?.ready_to_submit;

  return (
    <div className="next-steps-view" data-workflow-scroll>
      {ready ? (
        <div className="status-banner success">
          <div className="status-icon">
            <Icon name="check" />
          </div>
          <div className="status-text">
            <strong>Đã đạt kiểm tra sơ bộ</strong>
            <p>
              Dữ liệu đúng cấu trúc và chưa phát hiện mâu thuẫn. Kết quả này không thay thế bước
              kiểm tra của cơ quan nhà nước.
            </p>
          </div>
        </div>
      ) : (
        <div className="status-banner warning">
          <div className="status-icon">
            <Icon name="warning" />
          </div>
          <div className="status-text">
            <strong>Cần rà soát thêm hồ sơ</strong>
            <p>
              Hiện còn {issueCount} nội dung nên xử lý hoặc rà soát thêm. Tuy nhiên, bạn vẫn có
              thể xem lộ trình bên dưới để chuẩn bị.
            </p>
          </div>
        </div>
      )}

      <div className="modern-timeline">
        {steps.map((step, index) => (
          <div className={`timeline-step ${step.tone}`} key={step.title}>
            <div className="timeline-marker">
              <span>{index + 1}</span>
            </div>
            <div className="timeline-content">
              <strong>{step.title}</strong>
              <p>{step.body}</p>
            </div>
          </div>
        ))}
      </div>

      {!!result.sources.length && (
        <a
          href={result.sources[0].source_url || "https://dichvucong.gov.vn"}
          target="_blank"
          rel="noreferrer"
          className="reference-card"
        >
          <div className="ref-icon">
            <Icon name="shield" />
          </div>
          <div className="ref-content">
            <strong>Nguồn tham chiếu chính thống</strong>
            <p>Tra cứu lại biểu mẫu và quy định từ cổng Dịch vụ công.</p>
          </div>
          <div className="ref-external">
            <Icon name="external" />
          </div>
        </a>
      )}

      <div className="next-steps-actions">
        <button type="button" className="secondary-button" onClick={onBack}>
          ← Xem lại kết quả
        </button>
        <button type="button" className="primary-button" onClick={onRestart}>
          Bắt đầu hồ sơ mới
          <Icon name="home" />
        </button>
      </div>
      <WorkflowScrollDock />
    </div>
  );
}
