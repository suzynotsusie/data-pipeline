"use client";

import { useState, useEffect } from "react";
import { Icon } from "./Icon";
import type { ChecklistItem, IntakeResult, StepItem } from "../lib/types";

const genericFallbackChecklist: {
  documents: ChecklistItem[];
  conditional: ChecklistItem[];
  steps: StepItem[];
} = {
  documents: [
    { name: "Tờ khai theo mẫu", quantity: "Bản chính x1", notes: "Điền đầy đủ thông tin theo biểu mẫu của thủ tục." },
    { name: "Giấy tờ tùy thân liên quan", quantity: "Bản sao x1", notes: "Chuẩn bị giấy tờ gốc để đối chiếu khi cần." },
  ],
  conditional: [],
  steps: [
    { order: 1, title: "Chuẩn bị hồ sơ", description: "Tập hợp đủ giấy tờ chính và giấy tờ bổ sung theo từng trường hợp." },
    { order: 2, title: "Nộp hồ sơ", description: "Nộp tại cơ quan có thẩm quyền hoặc qua cổng trực tuyến nếu thủ tục hỗ trợ." },
    { order: 3, title: "Theo dõi kết quả", description: "Kiểm tra phản hồi của cơ quan tiếp nhận để bổ sung hoặc nhận kết quả." },
  ],
};

const genericOverviewMeta = {
  processingTime: "Theo quy định pháp luật",
  processingHint: "Thời gian thực tế có thể thay đổi theo từng hồ sơ.",
  submissionPlace: "Cơ quan có thẩm quyền",
  submissionHint: "Kiểm tra lại cơ quan tiếp nhận trong hướng dẫn chính thức.",
};

export function GuidanceView({ result, onContinue }: { result: IntakeResult; onContinue: () => void }) {
  const documents = result.checklist?.documents?.length ? result.checklist.documents : genericFallbackChecklist.documents;
  const conditional = result.checklist?.conditional_documents?.length ? result.checklist.conditional_documents : genericFallbackChecklist.conditional;
  const steps = result.checklist?.steps?.length ? result.checklist.steps : genericFallbackChecklist.steps;
  const meta = genericOverviewMeta;
  
  const [checkedDocs, setCheckedDocs] = useState<Set<number>>(new Set());
  const [isPlaying, setIsPlaying] = useState(false);

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

  const progress = documents.length > 0 ? Math.round((checkedDocs.size / documents.length) * 100) : 100;

  const speak = () => {
    if (isPlaying) {
      window.speechSynthesis.cancel();
      setIsPlaying(false);
      return;
    }
    const textToSpeak = `Thủ tục: ${result.procedure?.title}. Bạn cần chuẩn bị ${documents.length} loại giấy tờ sau: ` + 
      documents.map((d, i) => `${i + 1}: ${d.name}.`).join(" ");
      
    const utterance = new SpeechSynthesisUtterance(textToSpeak);
    utterance.lang = 'vi-VN';
    utterance.rate = 0.9;
    utterance.onend = () => setIsPlaying(false);
    
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utterance);
    setIsPlaying(true);
  };

  return (
    <div className="guidance-view p-0">
      <div className="result-heading pb-4 mb-4 border-b border-outline-variant">
        <span className="success-seal bg-status-green-bg text-status-green w-10 h-10 rounded-full flex items-center justify-center shrink-0">
          <Icon name="check" />
        </span>
        <div>
          <small className="text-primary text-[9px] font-bold tracking-widest block">ĐÃ XÁC ĐỊNH THỦ TỤC PHÙ HỢP</small>
          <h2 className="text-lg font-bold font-sans my-1 leading-tight">{result.procedure?.title}</h2>
          <p className="text-[10px] text-muted m-0">Mã thủ tục: <strong>{result.procedure?.code}</strong></p>
        </div>
      </div>

      <div className="flex flex-col gap-4 mb-4">
        {/* Timeline & Location Overview */}
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-surface rounded-xl border border-outline-variant p-3 flex flex-col gap-2 shadow-sm min-h-[104px]">
            <div className="flex items-center gap-2 text-primary font-bold text-xs">
              <span className="w-7 h-7 rounded-full bg-surface-container-low flex items-center justify-center shrink-0">
                <Icon name="clock" className="w-4 h-4" />
              </span>
              <span>Thời gian xử lý</span>
            </div>
            <strong className="text-[12px] text-ink leading-snug">{meta.processingTime}</strong>
            <p className="text-[10px] text-muted m-0 leading-relaxed">{meta.processingHint}</p>
          </div>
          <div className="bg-surface rounded-xl border border-outline-variant p-3 flex flex-col gap-2 shadow-sm min-h-[104px]">
            <div className="flex items-center gap-2 text-primary font-bold text-xs">
              <span className="w-7 h-7 rounded-full bg-surface-container-low flex items-center justify-center shrink-0">
                <Icon name="home" className="w-4 h-4" />
              </span>
              <span>Nơi nộp hồ sơ</span>
            </div>
            <strong className="text-[12px] text-ink leading-snug">{meta.submissionPlace}</strong>
            <p className="text-[10px] text-muted m-0 leading-relaxed">{meta.submissionHint}</p>
          </div>
        </div>

        {/* Interactive Checklist Card */}
        <section className="info-card rounded-lg overflow-hidden border border-outline-variant shadow-soft bg-white">
          <div className="card-title p-4 border-b border-outline-variant bg-surface-container-low flex justify-between items-center">
            <div className="flex items-center gap-3">
              <span className="text-primary"><Icon name="file"/></span>
              <div>
                <h3 className="text-[13px] font-bold m-0 text-primary">Giấy tờ cần chuẩn bị</h3>
              </div>
            </div>
            <button 
              onClick={speak} 
              className={`p-2 rounded-full flex items-center justify-center transition-colors ${isPlaying ? 'bg-primary text-white animate-pulse' : 'bg-white border border-outline-variant text-primary hover:bg-surface'}`}
              title={isPlaying ? "Dừng đọc" : "Nghe hướng dẫn"}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M15.54 8.46a5 5 0 0 1 0 7.07"></path><path d="M19.07 4.93a10 10 0 0 1 0 14.14"></path></svg>
            </button>
          </div>
          
          <div className="px-4 pt-3 pb-1">
            <div className="flex justify-between text-[10px] font-bold mb-1">
              <span className="text-muted">Tiến độ chuẩn bị:</span>
              <span className="text-primary">{checkedDocs.size} / {documents.length}</span>
            </div>
            <div className="w-full bg-surface-dim rounded-full h-1.5 overflow-hidden">
              <div className="bg-primary h-1.5 rounded-full transition-all duration-500 ease-out" style={{ width: `${progress}%` }}></div>
            </div>
          </div>

          <ul className="p-0 m-0 list-none divide-y divide-outline-variant/50">
            {documents.map((item, index) => (
              <li key={`${item.name}-${index}`} className={`px-4 py-3 flex gap-3 transition-colors ${checkedDocs.has(index) ? 'bg-status-green-bg/30' : 'hover:bg-surface-container-low'}`}>
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
                    <strong className={`text-[11px] leading-snug block transition-all ${checkedDocs.has(index) ? 'line-through text-muted' : 'text-ink'}`}>
                      {item.name || "Giấy tờ theo hướng dẫn"}
                    </strong>
                    {item.notes && <p className="text-[10px] text-muted m-0 mt-1">{item.notes}</p>}
                    {item.quantity && <span className="inline-block mt-1.5 text-[9px] font-bold bg-surface-dim px-2 py-0.5 rounded text-on-surface-variant">{item.quantity}</span>}
                  </div>
                </label>
              </li>
            ))}
          </ul>
          {!!conditional.length && (
            <div className="bg-status-yellow-bg border-l-4 border-status-yellow p-3 m-3 rounded text-[10px]">
              <strong className="block text-status-yellow-dark mb-1">Hồ sơ theo trường hợp (nếu có):</strong>
              {conditional.map((item, index) => <p key={index} className="m-0 text-on-surface-variant">• {item.name}</p>)}
            </div>
          )}
        </section>

        {/* Timeline Steps Card */}
        <section className="info-card steps-card rounded-lg border border-outline-variant shadow-soft bg-white p-4">
          <div className="flex items-center gap-2 border-b border-outline-variant pb-3 mb-3">
            <span className="text-primary"><Icon name="arrow"/></span>
            <div>
              <h3 className="text-[13px] font-bold m-0 text-primary">Hướng dẫn từng bước</h3>
            </div>
          </div>
          <ol className="timeline p-0 m-0">
            {steps.map((step, index) => (
              <li key={index} className="grid grid-cols-[24px_1fr] gap-3 relative pb-4 last:pb-0">
                {index < steps.length - 1 && <div className="absolute left-[11px] top-[24px] bottom-0 w-[2px] bg-outline-variant/40" />}
                <span className="w-6 h-6 rounded-full bg-primary text-white text-[9px] flex items-center justify-center font-bold relative z-10 shadow-sm">{step.order || index + 1}</span>
                <div className="pt-1">
                  <strong className="text-[11px] text-ink">{step.title || `Bước ${index + 1}`}</strong>
                  {step.description && <p className="text-[10px] text-muted m-0 mt-1 leading-relaxed">{step.description}</p>}
                  {step.example && <aside className="bg-surface p-2 mt-2 text-[9px] rounded text-on-surface-variant border border-outline-variant/50"><b>Ví dụ:</b> {step.example}</aside>}
                </div>
              </li>
            ))}
          </ol>
        </section>
      </div>

      {!!result.common_errors.length && (
        <section className="warning-panel bg-status-yellow-bg border border-status-yellow rounded p-3 mb-4 flex gap-3 text-on-surface-variant">
          <span className="text-status-yellow-dark mt-0.5 shrink-0"><Icon name="warning"/></span>
          <div>
            <strong className="text-[11px] text-ink block mb-1">Lưu ý để tránh hồ sơ bị trả lại</strong>
            {result.common_errors.slice(0, 3).map((item, index) => <p key={index} className="text-[10px] m-0 mb-1 last:mb-0">• {item.problem}{item.fix ? ` — ${item.fix}` : ""}</p>)}
          </div>
        </section>
      )}

      <div className="next-action flex flex-col gap-3 mt-5 p-4 bg-surface-container rounded-lg border-l-4 border-primary">
        <div>
          <strong className="text-[12px] block text-ink">Bạn đã chuẩn bị xong hồ sơ?</strong>
          <span className="text-[10px] text-muted">Sử dụng GovEase AI để kiểm tra thông tin, tránh sai sót trước khi nộp chính thức.</span>
        </div>
        <button 
          className="primary-button h-10 w-full rounded-md flex items-center justify-center gap-2 font-bold text-[11px] bg-primary text-white shadow-soft transition-colors hover:bg-primary-container disabled:opacity-50"
          onClick={onContinue}
          disabled={progress < 100}
        >
          {progress < 100 ? "Vui lòng chuẩn bị đủ hồ sơ để tiếp tục" : "Kiểm tra thông tin"} <Icon name="arrow"/>
        </button>
      </div>
    </div>
  );
}
