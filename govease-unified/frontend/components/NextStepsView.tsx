"use client";

import type { IntakeResult, ValidationResult } from "../lib/types";
import { Icon } from "./Icon";

function buildTimeline(result: IntakeResult, validation: ValidationResult | null) {
  const procedureTitle = result.procedure?.title || "thủ tục của bạn";
  const issues = validation?.issues || [];
  const blocking = issues.filter((issue) => issue.blocking);
  const warnings = issues.filter((issue) => !issue.blocking);
  const submissionHint = result.checklist.steps?.[0]?.description || "Hoàn tất tờ khai trực tuyến theo đúng hồ sơ đã rà soát.";

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
  const procedureTitle = result.procedure?.title || "Thủ tục";
  const issueCount = validation?.issues.length || 0;
  const ready = validation?.ready_to_submit;

  return (
    <div className="next-steps-view">
      <div className="next-steps-hero">
        <span className="next-steps-avatar">
          <Icon name={ready ? "check" : "bot"} />
        </span>
        <div>
          <small>BƯỚC TIẾP THEO</small>
          <h2>{procedureTitle}</h2>
          <p>
            {ready
              ? "Hồ sơ đã qua kiểm tra sơ bộ. Dưới đây là lộ trình ngắn gọn để bạn hoàn tất việc nộp."
              : `Hiện còn ${issueCount} nội dung nên xử lý hoặc rà soát thêm. Bạn vẫn có thể xem trước kế hoạch tiếp theo để chuẩn bị.`}
          </p>
        </div>
      </div>

      <div className="next-steps-grid">
        {steps.map((step, index) => (
          <article className={`next-step-card tone-${step.tone}`} key={step.title}>
            <span>{index + 1}</span>
            <div>
              <strong>{step.title}</strong>
              <p>{step.body}</p>
            </div>
          </article>
        ))}
      </div>

      {!!result.sources.length && (
        <div className="source-panel">
          <Icon name="shield" />
          <div>
            <strong>Nguồn tham chiếu</strong>
            <p>Tra cứu lại thủ tục từ nguồn chính thống trước khi nộp hồ sơ chính thức.</p>
            <a href={result.sources[0].source_url || "https://dichvucong.gov.vn"} target="_blank" rel="noreferrer">
              {result.sources[0].source_url || "dichvucong.gov.vn"}
              <Icon name="external" />
            </a>
          </div>
        </div>
      )}

      <div className="next-steps-actions">
        <button type="button" className="secondary-button" onClick={onBack}>
          Quay lại kiểm tra
        </button>
        <button type="button" className="primary-button" onClick={onRestart}>
          Bắt đầu hồ sơ mới
        </button>
      </div>
    </div>
  );
}
