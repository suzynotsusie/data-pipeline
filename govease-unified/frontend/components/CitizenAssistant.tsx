"use client";

import { FormEvent, useRef, useState } from "react";
import { submitIntake } from "../lib/api";
import type { ChatMessage, IntakeResult, ValidationResult } from "../lib/types";
import { DynamicForm } from "./DynamicForm";
import { GuidanceView } from "./GuidanceView";
import { Icon } from "./Icon";
import { NextStepsView } from "./NextStepsView";

const examples = ["Tôi mới sinh con và cần làm giấy khai sinh", "Tôi đang thuê nhà và muốn đăng ký tạm trú"];

export function CitizenAssistant({ compact = false }: { compact?: boolean }) {
  const [phase, setPhase] = useState<"need" | "guide" | "validate" | "next">("need");
  const [input, setInput] = useState("");
  const [history, setHistory] = useState<ChatMessage[]>([]);
  const [sessionId, setSessionId] = useState<string>();
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [result, setResult] = useState<IntakeResult | null>(null);
  const [validation, setValidation] = useState<ValidationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const quickReplies = result?.quick_replies || [];

  async function send(event?: FormEvent, suggestion?: string) {
    event?.preventDefault();
    const message = (suggestion ?? input).trim();
    if (!message || loading) return;
    setLoading(true); setError(""); setInput("");
    try {
      const nextAnswers = result?.clarifying_question_id
        ? { ...answers, [result.clarifying_question_id]: message }
        : answers;
      const response = await submitIntake({ message, history, answers: nextAnswers, session_id: sessionId, procedure_code: result?.procedure?.code });
      setSessionId(response.session_id); setResult(response);
      setAnswers(response.answers || nextAnswers);
      setHistory((current) => [...current, { role: "user", content: message }, ...(response.clarifying_question ? [{ role: "assistant" as const, content: response.clarifying_question }] : [])]);
      if (response.status === "completed") setPhase("guide");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Không thể xử lý yêu cầu."); }
    finally { setLoading(false); }
  }

  function reset() { setPhase("need"); setResult(null); setValidation(null); setHistory([]); setSessionId(undefined); setAnswers({}); setInput(""); setError(""); setTimeout(() => inputRef.current?.focus(), 0); }

  if (phase === "guide" && result?.procedure) return <div className={`assistant-shell ${compact ? "compact" : ""}`}><AssistantBar phase={phase} onReset={reset}/><GuidanceView result={result} onContinue={() => setPhase("validate")}/></div>;
  if (phase === "validate" && result?.procedure) return <div className={`assistant-shell ${compact ? "compact" : ""}`}><AssistantBar phase={phase} onReset={reset}/><DynamicForm procedureCode={result.procedure.code} onBack={() => setPhase("guide")} onContinue={(checked) => { setValidation(checked); setPhase("next"); }}/></div>;
  if (phase === "next" && result?.procedure) return <div className={`assistant-shell ${compact ? "compact" : ""}`}><AssistantBar phase={phase} onReset={reset}/><NextStepsView result={result} validation={validation} onBack={() => setPhase("validate")} onRestart={reset}/></div>;

  return <div className={`assistant-shell ${compact ? "compact" : ""}`}>
    <AssistantBar phase={phase} onReset={reset}/>
    <div className="intake-panel">
      <div className="assistant-intro"><span className="ai-orb"><Icon name="bot"/></span><div><small>TRỢ LÝ THỦ TỤC HÀNH CHÍNH</small><h1>Chào bạn, tôi có thể hỗ trợ thủ tục gì?</h1><p>Mô tả nhu cầu bằng ngôn ngữ tự nhiên. GovEase AI sẽ xác định thủ tục, hướng dẫn hồ sơ và giúp kiểm tra trước khi nộp.</p></div></div>
      {!!history.length && <div className="conversation">{history.map((message, index) => <div className={`bubble ${message.role}`} key={index}><span>{message.role === "assistant" ? <Icon name="bot"/> : <Icon name="user"/>}</span><p>{message.content}</p></div>)}</div>}
      {result?.needs_clarification && <div className="clarification-label"><span>{result.domain_label ? `Đang làm rõ nhóm ${result.domain_label.toLowerCase()}. ` : ""}AI cần thêm một thông tin để hướng dẫn chính xác</span></div>}
      {!!quickReplies.length && <div className="quick-intake">{quickReplies.map((item) => <button type="button" key={`${item.value}-${item.label}`} className="quick-intake-button" onClick={() => send(undefined, item.value)} disabled={loading}><strong>{item.label}</strong>{item.description && <span>{item.description}</span>}</button>)}</div>}
      <form className="need-composer" onSubmit={send}>
        <textarea ref={inputRef} value={input} onChange={(event) => setInput(event.target.value)} placeholder={result?.needs_clarification ? "Nhập câu trả lời của bạn…" : "Ví dụ: Tôi mới sinh con và muốn làm giấy khai sinh…"} rows={compact ? 2 : 3} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); void send(); } }}/>
        <button type="submit" disabled={loading || !input.trim()}>{loading ? <span className="spinner"/> : <Icon name="send"/>}<span>{loading ? "Đang tra cứu" : "Gửi yêu cầu"}</span></button>
      </form>
      {error && <div className="inline-error"><Icon name="warning"/><div><strong>Không thể kết nối</strong><span>{error}</span></div><button onClick={() => inputRef.current?.focus()}>Thử lại</button></div>}
      {!history.length && !quickReplies.length && <div className="examples"><span>Gợi ý nhu cầu phổ biến:</span>{examples.map((example) => <button onClick={() => send(undefined, example)} key={example}><Icon name="search"/>{example}</button>)}</div>}
      <div className="trust-row"><span><Icon name="shield"/>Dữ liệu từ nguồn chính thống</span><span><Icon name="check"/>Có trích dẫn nguồn</span><span><Icon name="file"/>Kiểm tra trước khi nộp</span></div>
    </div>
  </div>;
}

function AssistantBar({ phase, onReset }: { phase: string; onReset: () => void }) {
  const steps = [{ key: "need", label: "Nêu nhu cầu" }, { key: "guide", label: "Nhận hướng dẫn" }, { key: "validate", label: "Kiểm tra thông tin" }, { key: "next", label: "Bước tiếp theo" }];
  const active = steps.findIndex((step) => step.key === phase);
  return <div className="assistant-bar"><div className="mini-brand"><span><Icon name="bot"/></span><div><strong>GovEase AI</strong><small>Trợ lý dịch vụ công</small></div></div><div className="progress-steps">{steps.map((step, index) => <div className={`${index <= active ? "active" : ""} ${index < active ? "done" : ""}`} key={step.key}><i>{index < active ? <Icon name="check"/> : index + 1}</i><span>{step.label}</span></div>)}</div><button className="restart" onClick={onReset}>Bắt đầu lại</button></div>;
}
