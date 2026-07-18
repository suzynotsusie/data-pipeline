"use client";

import { useEffect, useState } from "react";

import type { IntakeResult, StepItem } from "../lib/types";
import { Icon } from "./Icon";
import { WorkflowScrollDock } from "./WorkflowScrollDock";

const missingSubmissionMeta = {
  submissionPlace: "Chưa có thông tin nơi nộp đủ rõ",
  submissionHint: "Hiện chưa có thông tin đáng tin cậy về nơi tiếp nhận hoặc cách nộp cho thủ tục này.",
};

const genericOverviewMeta = {
  processingTime: "Theo quy định của cơ quan tiếp nhận",
  processingHint: "Thời gian thực tế có thể thay đổi theo từng hồ sơ.",
  submissionPlace: "Cơ quan có thẩm quyền",
  submissionHint: "Kiểm tra lại cơ quan tiếp nhận trong hướng dẫn chính thức.",
};

const repeatedCommonErrorFix =
  "Nên xác định trước kênh nộp hồ sơ để biết có cần bản giấy, bản điện tử hay xuất trình trực tiếp.";

function compressCommonError(problem?: string | null, fix?: string | null) {
  const cleanProblem = (problem || "").trim().replace(/^[\-\u2022]\s*/, "").replace(/[.;:\s]+$/g, "");
  const cleanFix = (fix || "").trim().replace(/^[\-\u2022]\s*/, "").replace(/[.;:\s]+$/g, "");
  if (!cleanProblem) return "";
  if (!cleanFix || cleanFix === repeatedCommonErrorFix.replace(/[.;:\s]+$/g, "")) return cleanProblem;
  return `${cleanProblem}: ${cleanFix}`;
}

function normalizeSubmissionMethodLabel(label: string) {
  const compact = label.trim().replace(/\s+/g, " ");
  const lowered = compact.toLocaleLowerCase("vi-VN");

  if (lowered.includes("trực tuyến")) return "Trực tuyến";
  if (lowered.includes("trực tiếp")) return "Trực tiếp";
  if (lowered.includes("bưu chính")) return "Bưu chính";

  return compact.charAt(0).toLocaleUpperCase("vi-VN") + compact.slice(1);
}

function dedupeSubmissionMethodLabels(labels?: string[] | null) {
  if (!labels?.length) return [];

  const seen = new Set<string>();
  const normalized: string[] = [];

  for (const label of labels) {
    if (!label?.trim()) continue;
    const next = normalizeSubmissionMethodLabel(label);
    const key = next.toLocaleLowerCase("vi-VN");
    if (seen.has(key)) continue;
    seen.add(key);
    normalized.push(next);
  }

  return normalized;
}

function formatSubmissionMethodLabels(labels: string[]) {
  return labels.join(" / ");
}

function buildSubmissionPlaceMeta({
  submissionPlace,
  submissionMethodLabels,
}: {
  submissionPlace?: string | null;
  submissionMethodLabels?: string[] | null;
}) {
  const place = submissionPlace?.trim();
  const methods = dedupeSubmissionMethodLabels(submissionMethodLabels);

  if (place && methods.length > 1) {
    return {
      submissionPlace: place,
      submissionHint: `Có thể nộp qua: ${formatSubmissionMethodLabels(methods)}.`,
    };
  }

  if (place && methods.length === 1) {
    return {
      submissionPlace: place,
      submissionHint: `Có thể nộp qua ${methods[0].toLocaleLowerCase("vi-VN")}.`,
    };
  }

  if (!place && methods.length > 1) {
    return {
      submissionPlace: "Có nhiều cách nộp hồ sơ",
      submissionHint: `Hiện đã xác định được các kênh nộp sau: ${formatSubmissionMethodLabels(methods)}.`,
    };
  }

  if (!place && methods.length === 1) {
    return {
      submissionPlace: `Nộp qua ${methods[0].toLocaleLowerCase("vi-VN")}`,
      submissionHint: "Hiện chưa có thông tin cụ thể về nơi tiếp nhận, nhưng đã xác định được kênh nộp hồ sơ phù hợp.",
    };
  }

  return missingSubmissionMeta;
}

export function GuidanceView({ result, onContinue }: { result: IntakeResult; onContinue: () => void }) {
  const documents = (result.checklist?.documents || []).filter((item) => Boolean(item?.name));
  const conditional = (result.checklist?.conditional_documents || []).filter((item) => Boolean(item?.name));
  const summarizedSteps = result.checklist?.user_steps?.length
    ? result.checklist.user_steps
    : summarizeSteps(result.checklist?.steps || []);
  const steps = summarizedSteps.length ? summarizedSteps : [];
  const hasVerifiedChecklist = documents.length > 0;
  const hasVerifiedSteps = steps.length > 0;
  const submissionMeta = buildSubmissionPlaceMeta({
    submissionPlace: result.checklist?.submission_place_summary,
    submissionMethodLabels: result.checklist?.submission_method_labels,
  });
  const meta = {
    processingTime: result.checklist?.processing_time_summary || genericOverviewMeta.processingTime,
    processingHint: genericOverviewMeta.processingHint,
    submissionPlace: submissionMeta.submissionPlace,
    submissionHint: submissionMeta.submissionHint,
  };
  const commonErrorItems = Array.from(
    new Set((result.common_errors || []).map((item) => compressCommonError(item.problem, item.fix)).filter(Boolean)),
  ).slice(0, 3);

  const [checkedDocs, setCheckedDocs] = useState<Set<number>>(new Set());
  const [isPlaying, setIsPlaying] = useState(false);
  const [showConditionalDocs, setShowConditionalDocs] = useState(false);

  useEffect(() => {
    return () => {
      window.speechSynthesis.cancel();
    };
  }, []);

  const toggleDoc = (index: number) => {
    const next = new Set(checkedDocs);
    if (next.has(index)) next.delete(index);
    else next.add(index);
    setCheckedDocs(next);
  };

  const progress = hasVerifiedChecklist ? Math.round((checkedDocs.size / documents.length) * 100) : 100;

  const speak = () => {
    if (isPlaying) {
      window.speechSynthesis.cancel();
      setIsPlaying(false);
      return;
    }

    const textToSpeak = hasVerifiedChecklist
      ? `Thủ tục: ${result.procedure?.title}. ${result.checklist?.next_step_summary || ""} Bạn cần chuẩn bị ${documents.length} loại giấy tờ sau: ${documents.map((d, i) => `${i + 1}: ${d.name}.`).join(" ")}`
      : `Thủ tục: ${result.procedure?.title}. Hiện chưa có dữ liệu checklist giấy tờ đã xác thực cho thủ tục này. Vui lòng đối chiếu nguồn chính thức trước khi chuẩn bị hồ sơ.`;

    const utterance = new SpeechSynthesisUtterance(textToSpeak);
    utterance.lang = "vi-VN";
    utterance.rate = 0.9;
    utterance.onend = () => setIsPlaying(false);

    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utterance);
    setIsPlaying(true);
  };

  return (
    <div className="guidance-view p-0" data-workflow-scroll>
      <div className="result-heading pb-4 mb-4 border-b border-outline-variant">
        <span className="success-seal bg-status-green-bg text-status-green w-10 h-10 rounded-full flex items-center justify-center shrink-0">
          <Icon name="check" />
        </span>
        <div>
          <small className="text-primary text-[9px] font-bold tracking-widest block">ĐÃ XÁC ĐỊNH THỦ TỤC PHÙ HỢP</small>
          <h2 className="text-lg font-bold font-sans my-1 leading-tight">{result.procedure?.title}</h2>
          <p className="text-[10px] text-muted m-0">
            Mã thủ tục: <strong>{result.procedure?.code}</strong>
          </p>
        </div>
      </div>

      <div className="flex flex-col gap-5 mb-5">
        <div className="rounded-xl border border-outline-variant bg-surface-container-low p-4 text-[12px] leading-relaxed text-on-surface-variant shadow-sm flex flex-col gap-3">
          <div className="flex items-center flex-wrap gap-2">
            <span className="text-[11px] text-muted">Xác thực và lấy dữ liệu từ:</span>
            <a 
              href={`https://dichvucong.gov.vn/p/home/dvc-chi-tiet-thu-tuc-hanh-chinh.html?ma_thu_tuc=${result.procedure?.code}`}
              target="_blank"
              rel="noopener noreferrer"
              className="verified-source inline-flex items-center gap-1"
              style={{ textDecoration: 'none', marginLeft: 0 }}
              title="Trích xuất từ Cổng Dịch vụ công Quốc gia"
            >
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
                <polyline points="9 12 11 14 15 10"></polyline>
              </svg>
              Cổng DVC Quốc gia
            </a>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-surface rounded-xl border border-outline-variant p-3 flex flex-col gap-2 shadow-sm min-h-[104px]">
            <div className="flex items-center gap-2 text-primary font-bold text-xs">
              <span className="w-7 h-7 rounded-full bg-surface-container-low flex items-center justify-center shrink-0">
                <Icon name="clock" className="w-4 h-4" />
              </span>
              <span>Thời gian xử lý</span>
            </div>
            <strong className="text-[12px] text-ink leading-snug">{meta.processingTime}</strong>
            <p className="text-[11px] text-muted m-0 leading-relaxed">{meta.processingHint}</p>
          </div>
          <div className="bg-surface rounded-xl border border-outline-variant p-3 flex flex-col gap-2 shadow-sm min-h-[104px]">
            <div className="flex items-center gap-2 text-primary font-bold text-xs">
              <span className="w-7 h-7 rounded-full bg-surface-container-low flex items-center justify-center shrink-0">
                <Icon name="home" className="w-4 h-4" />
              </span>
              <span>Nơi nộp hồ sơ</span>
            </div>
            <strong className="text-[12px] text-ink leading-snug">{meta.submissionPlace}</strong>
            <p className="text-[11px] text-muted m-0 leading-relaxed">{meta.submissionHint}</p>
          </div>
        </div>

        <section className="info-card rounded-lg overflow-hidden border border-outline-variant shadow-soft bg-white">
          <div className="card-title p-4 border-b border-outline-variant bg-surface-container-low flex justify-between items-center">
            <div className="flex items-center gap-3">
              <span className="text-primary">
                <Icon name="file" />
              </span>
              <div>
                <h3 className="text-[13px] font-bold m-0 text-primary">Giấy tờ cần chuẩn bị</h3>
              </div>
            </div>
            <button
              onClick={speak}
              className={`p-2 rounded-full flex items-center justify-center transition-colors ${isPlaying ? "bg-primary text-white animate-pulse" : "bg-white border border-outline-variant text-primary hover:bg-surface"}`}
              title={isPlaying ? "Dừng đọc" : "Nghe hướng dẫn"}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
                <path d="M15.54 8.46a5 5 0 0 1 0 7.07"></path>
                <path d="M19.07 4.93a10 10 0 0 1 0 14.14"></path>
              </svg>
            </button>
          </div>

          <div className="px-4 pt-3 pb-2">
            <div className="flex justify-between text-[11px] font-bold mb-2">
              <span className="text-muted">{hasVerifiedChecklist ? "Tiến độ chuẩn bị:" : "Trạng thái dữ liệu:"}</span>
              <span className="text-primary">{hasVerifiedChecklist ? `${checkedDocs.size} / ${documents.length}` : "Chưa xác thực"}</span>
            </div>
            <div className="w-full bg-surface-dim rounded-full h-1.5 overflow-hidden">
              <div className="bg-primary h-1.5 rounded-full transition-all duration-500 ease-out" style={{ width: `${progress}%` }}></div>
            </div>
          </div>

          {hasVerifiedChecklist ? (
            <ul className="p-0 m-0 list-none divide-y divide-outline-variant/50">
              {documents.map((item, index) => (
                <li key={`${item.name}-${index}`} className={`px-4 py-3 flex gap-3 transition-colors ${checkedDocs.has(index) ? "bg-status-green-bg/30" : "hover:bg-surface-container-low"}`}>
                  <label className="flex items-start gap-3 cursor-pointer w-full">
                    <div className="pt-0.5 shrink-0">
                      <input
                        type="checkbox"
                        className="w-4 h-4 rounded border-outline text-primary focus:ring-primary accent-primary"
                        checked={checkedDocs.has(index)}
                        onChange={() => toggleDoc(index)}
                      />
                    </div>
                    <div className="flex-1">
                      <strong className={`text-[11px] leading-snug block transition-all ${checkedDocs.has(index) ? "line-through text-muted" : "text-ink"}`}>
                        {item.name || "Giấy tờ theo hướng dẫn"}
                      </strong>
                      {item.notes && <p className="text-[11px] text-muted m-0 mt-1 leading-relaxed">{item.notes}</p>}
                      {item.quantity && (
                        <span className="inline-block mt-1.5 text-[10px] font-bold bg-surface-dim px-2 py-0.5 rounded text-on-surface-variant">
                          {item.quantity}
                        </span>
                      )}
                    </div>
                  </label>
                </li>
              ))}
            </ul>
          ) : (
            <div className="mx-4 mb-4 rounded-lg border border-status-yellow bg-status-yellow-bg p-3 text-[11px] text-on-surface-variant">
              <strong className="block mb-1 text-ink">Chưa có checklist giấy tờ đủ rõ cho thủ tục này</strong>
              <p className="m-0">
                Hiện hệ thống chưa trích xuất được danh sách giấy tờ đáng tin cậy cho thủ tục này, nên mình không hiện checklist mẫu để tránh gây hiểu nhầm.
                Bạn nên đối chiếu thêm từ nguồn chính thức hoặc bổ sung checklist ở backend nếu muốn hiển thị đầy đủ hơn.
              </p>
            </div>
          )}

          {!!conditional.length && (
            <div className="mx-3 mb-3 rounded-lg border border-outline-variant bg-surface-container-low overflow-hidden">
              <button
                type="button"
                onClick={() => setShowConditionalDocs((value) => !value)}
                className="w-full px-4 py-3 flex items-center justify-between gap-3 text-left"
              >
                <div>
                  <strong className="block text-[11px] text-ink">Hồ sơ theo trường hợp</strong>
                  <span className="text-[11px] text-muted">{conditional.length} mục chỉ cần xem thêm nếu bạn thuộc trường hợp đặc biệt.</span>
                </div>
                <span className="shrink-0 text-[11px] font-bold text-primary">{showConditionalDocs ? "Thu gọn" : "Xem thêm"}</span>
              </button>
              {showConditionalDocs && (
                <div className="px-4 pb-3 space-y-2">
                  {conditional.map((item, index) => (
                    <p key={index} className="m-0 text-[11px] leading-relaxed text-on-surface-variant">
                      - {item.name}
                    </p>
                  ))}
                </div>
              )}
            </div>
          )}
        </section>

        <section className="info-card steps-card rounded-lg border border-outline-variant shadow-soft bg-white p-4">
          <div className="flex items-center gap-2 border-b border-outline-variant pb-3 mb-3">
            <span className="text-primary">
              <Icon name="arrow" />
            </span>
            <div>
              <h3 className="text-[13px] font-bold m-0 text-primary">Hướng dẫn từng bước</h3>
              {result.checklist?.next_step_summary && (
                <p className="text-[11px] text-muted m-0 mt-1 leading-relaxed">{result.checklist.next_step_summary}</p>
              )}
            </div>
          </div>
          <ol className="timeline p-0 m-0">
            {hasVerifiedSteps ? (
              steps.map((step, index) => (
                <li key={index} className="grid grid-cols-[24px_1fr] gap-3 relative pb-4 last:pb-0">
                  {index < steps.length - 1 && <div className="absolute left-[11px] top-[24px] bottom-0 w-[2px] bg-outline-variant/40" />}
                  <span className="w-6 h-6 rounded-full bg-primary text-white text-[9px] flex items-center justify-center font-bold relative z-10 shadow-sm">
                    {step.order || index + 1}
                  </span>
                  <div className="pt-1">
                    <strong className="text-[11px] text-ink">{step.title || `Bước ${index + 1}`}</strong>
                    {step.description && <p className="text-[11px] text-muted m-0 mt-1 leading-relaxed">{step.description}</p>}
                    {step.example && (
                      <aside className="bg-surface p-2 mt-2 text-[10px] rounded text-on-surface-variant border border-outline-variant/50">
                        <b>Ví dụ:</b> {step.example}
                      </aside>
                    )}
                  </div>
                </li>
              ))
            ) : (
              <li className="text-[11px] text-muted leading-relaxed list-none">
                Hiện chưa có hướng dẫn từng bước đủ rõ cho thủ tục này. Hệ thống giữ nội dung theo đúng dữ liệu đang có, thay vì tự sinh thêm các bước có thể gây hiểu nhầm.
              </li>
            )}
          </ol>
        </section>
      </div>

      {!!commonErrorItems.length && (
        <section className="warning-panel bg-status-yellow-bg border border-status-yellow rounded p-3 mb-4 flex gap-3 text-on-surface-variant">
          <span className="text-status-yellow-dark mt-0.5 shrink-0">
            <Icon name="warning" />
          </span>
          <div>
            <strong className="text-[11px] text-ink block mb-1">Lưu ý để tránh hồ sơ bị trả lại</strong>
            <ul className="m-0 pl-4 space-y-1">
              {commonErrorItems.map((item, index) => (
                <li key={index} className="text-[11px] leading-relaxed">
                  {item}
                </li>
              ))}
            </ul>
          </div>
        </section>
      )}

      <div className="next-action flex flex-col gap-3 mt-5 p-4 bg-surface-container rounded-lg border-l-4 border-primary">
        <div>
          <strong className="text-[12px] block text-ink">Bạn đã chuẩn bị xong hồ sơ?</strong>
          <span className="text-[11px] text-muted">Khi sẵn sàng, mình sẽ giúp bạn kiểm tra thông tin trước khi nộp chính thức.</span>
        </div>
        <button
          className="primary-button h-10 w-full rounded-md flex items-center justify-center gap-2 font-bold text-[11px] bg-primary text-white shadow-soft transition-colors hover:bg-primary-container disabled:opacity-50"
          onClick={onContinue}
          disabled={hasVerifiedChecklist ? progress < 100 : false}
        >
          {hasVerifiedChecklist ? "Tôi đã chuẩn bị xong" : "Kiểm tra thông tin"} <Icon name="arrow" />
        </button>
        {hasVerifiedChecklist && progress < 100 && <p className="m-0 text-[11px] text-muted">Hãy tick đủ các giấy tờ bắt buộc để tiếp tục.</p>}
      </div>
      <WorkflowScrollDock />
    </div>
  );
}

function summarizeSteps(steps: IntakeResult["checklist"]["steps"] = []): StepItem[] {
  const detected = {
    chooseChannel: false,
    prepareDocuments: false,
    submit: false,
    supplement: false,
    verify: false,
    confirm: false,
    receive: false,
  };

  for (const step of steps || []) {
    const haystack = `${step?.title || ""} ${step?.description || ""} ${step?.example || ""}`.toLowerCase();
    if (/(trực tiếp|trực tuyến|bưu chính|hình thức nộp|cổng dịch vụ công)/.test(haystack)) detected.chooseChannel = true;
    if (/(tờ khai|giấy tờ|đính kèm|hồ sơ)/.test(haystack)) detected.prepareDocuments = true;
    if (/(nộp hồ sơ|hoàn tất việc nộp|tiếp nhận hồ sơ)/.test(haystack)) detected.submit = true;
    if (/(bổ sung|hoàn thiện hồ sơ|từ chối)/.test(haystack)) detected.supplement = true;
    if (/(thẩm tra|xác minh|tra cứu|kiểm tra)/.test(haystack)) detected.verify = true;
    if (/(xác nhận|biểu mẫu|một ngày)/.test(haystack)) detected.confirm = true;
    if (/(trả kết quả|nhận kết quả|in giấy|ký)/.test(haystack)) detected.receive = true;
  }

  const summarized: StepItem[] = [];
  const add = (title: string, description: string) => {
    summarized.push({ order: summarized.length + 1, title, description, example: null });
  };

  if (detected.chooseChannel) add("Chọn cách nộp", "Chọn kênh nộp phù hợp với hồ sơ của bạn: trực tiếp, trực tuyến hoặc bưu chính.");
  if (detected.prepareDocuments) add("Chuẩn bị giấy tờ", "Rà soát giấy tờ chính, mẫu tờ khai và tài liệu đính kèm theo checklist của thủ tục.");
  if (detected.submit) add("Nộp hồ sơ", "Nộp hồ sơ theo kênh đã chọn và hoàn tất lệ phí nếu thủ tục có yêu cầu.");
  if (detected.supplement) add("Bổ sung khi được yêu cầu", "Nếu hồ sơ thiếu hoặc chưa hợp lệ, bổ sung đúng giấy tờ theo thông báo của cơ quan tiếp nhận.");
  if (detected.verify) add("Cơ quan thẩm tra", "Cơ quan tiếp nhận sẽ kiểm tra, tra cứu hoặc xác minh thêm trước khi chốt kết quả.");
  if (detected.confirm) add("Xác nhận thông tin", "Nếu nộp trực tuyến, kiểm tra lại biểu mẫu điện tử và xác nhận thông tin khi hệ thống gửi lại.");
  if (detected.receive) add("Nhận kết quả", "Theo dõi phiếu hẹn hoặc thông báo và nhận kết quả khi hồ sơ đã được giải quyết.");

  return summarized.slice(0, 7);
}
