"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import Image from "next/image";

import { submitIntake } from "../lib/api";
import type { ChatMessage, CitizenGroupOption, IntakeResult, ValidationResult } from "../lib/types";
import { DynamicForm } from "./DynamicForm";
import { GuidanceView } from "./GuidanceView";
import { Icon } from "./Icon";
import { InlineSelectorBlock, SelectionSummaryChip } from "./InlineSelectorBlock";
import { NextStepsView } from "./NextStepsView";

const baseExamples = [
  "Tôi mới sinh con và cần làm giấy khai sinh",
  "Tôi đang thuê nhà và muốn đăng ký tạm trú",
  "Tôi cần cấp điện mới cho nhà ở",
];
const loadingMessage = "GovEase AI đang xem yêu cầu của bạn...";
const minLoadingMs = 2200;

type SelectorType = "group" | "subdomain" | "quick_reply" | "procedure_confirmation";

type ConversationMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  selectorPromptId?: string;
};

type SelectorPrompt = {
  id: string;
  type: SelectorType;
  status: "active" | "completed";
  title?: string;
  description?: string;
  selectedLabel?: string;
  helperText?: string;
  options?: Array<{ value: string; label: string; description?: string }>;
};

export function CitizenAssistant({
  compact = false,
  groups,
}: {
  compact?: boolean;
  groups: CitizenGroupOption[];
}) {
  const [phase, setPhase] = useState<"need" | "guide" | "validate" | "next">("need");
  const [showIntroModal, setShowIntroModal] = useState(false);
  
  useEffect(() => {
    if (compact) {
      if (typeof window !== "undefined" && !localStorage.getItem("botIntroSeen")) {
        setShowIntroModal(true);
      }
    }
  }, [compact]);
  const [input, setInput] = useState("");
  const [conversation, setConversation] = useState<ConversationMessage[]>([]);
  const [backendHistory, setBackendHistory] = useState<ChatMessage[]>([]);
  const [sessionId, setSessionId] = useState<string>();
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [result, setResult] = useState<IntakeResult | null>(null);
  const [validation, setValidation] = useState<ValidationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [pendingNeed, setPendingNeed] = useState<string | null>(null);
  const [selectedGroupKey, setSelectedGroupKey] = useState<string>();
  const [selectedSubdomainKey, setSelectedSubdomainKey] = useState<string>();
  const [selectorPrompts, setSelectorPrompts] = useState<Record<string, SelectorPrompt>>({});
  const [activeSelectorTurnId, setActiveSelectorTurnId] = useState<string>();
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const idRef = useRef(0);

  const groupMap = useMemo(
    () => new Map(groups.map((group) => [group.group_key, group])),
    [groups],
  );
  const selectedGroup = selectedGroupKey ? groupMap.get(selectedGroupKey) : undefined;
  const selectedSubdomain = selectedGroup?.subdomains.find((item) => item.subdomain_key === selectedSubdomainKey);
  const activeSelector = activeSelectorTurnId ? selectorPrompts[activeSelectorTurnId] : undefined;
  const blockingSelector = activeSelector?.type === "group" || activeSelector?.type === "subdomain";
  const examples = baseExamples.slice(0, compact ? 2 : 3);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: "smooth",
      });
    }
  }, [conversation, loading, result, activeSelectorTurnId]);

  function nextId(prefix: string) {
    idRef.current += 1;
    return `${prefix}-${idRef.current}`;
  }

  function queueSelector(type: SelectorType, group?: CitizenGroupOption) {
    const promptId = nextId("selector");
    const messageId = nextId("message");
    const prompt: SelectorPrompt =
      type === "group"
        ? {
            id: promptId,
            type,
            status: "active",
            title: "Chọn nhóm nhu cầu chính",
            description: "Chọn đúng 1 trong 11 nhóm Công dân để mình định tuyến workflow chính xác ngay từ đầu.",
          }
        : {
            id: promptId,
            type,
            status: "active",
            title: `Chọn nhánh cụ thể trong ${group?.label || "nhóm đã chọn"}`,
            description: "Chọn subdomain gần nhất với tình huống của bạn để assistant bám đúng workflow.",
          };

    setSelectorPrompts((prev) => ({ ...prev, [promptId]: prompt }));
    setActiveSelectorTurnId(promptId);
    setConversation((prev) => [
      ...prev,
      {
        id: messageId,
        role: "assistant",
        content:
          type === "group"
            ? "Mình đã ghi nhận nhu cầu của bạn. Trước khi đi tiếp, hãy chọn nhóm Công dân phù hợp nhất."
            : `Đã rõ nhóm ${group?.label?.toLowerCase() || "này"}. Chọn thêm nhánh cụ thể để mình route đúng workflow.`,
        selectorPromptId: promptId,
      },
    ]);
  }

  function completeSelector(promptId: string, selectedLabel: string, helperText: string) {
    setSelectorPrompts((prev) => ({
      ...prev,
      [promptId]: {
        ...prev[promptId],
        status: "completed",
        selectedLabel,
        helperText,
      },
    }));
    setActiveSelectorTurnId(undefined);
  }

  function queueProcedureConfirmation(procedureTitle?: string) {
    const promptId = nextId("selector");
    const messageId = nextId("message");

    setSelectorPrompts((prev) => ({
      ...prev,
      [promptId]: {
        id: promptId,
        type: "procedure_confirmation",
        status: "active",
        title: "Đúng thủ tục bạn cần?",
        description: "Xác nhận nhanh trước khi mình chuyển sang phần hướng dẫn chi tiết.",
        options: [
          { value: "confirm", label: "Đúng thủ tục này" },
          { value: "restart", label: "Làm thủ tục khác" },
        ],
      },
    }));
    setActiveSelectorTurnId(promptId);
    setConversation((prev) => [
      ...prev,
      {
        id: messageId,
        role: "assistant",
        content: `Mình đang đề xuất thủ tục: ${procedureTitle || "thủ tục này"}. Có đúng thứ bạn đang cần làm không?`,
        selectorPromptId: promptId,
      },
    ]);
  }

  function handleProcedureConfirmation(promptId: string, action: "confirm" | "restart", label: string) {
    if (action === "restart") {
      reset();
      return;
    }

    completeSelector(promptId, label, "Đã xác nhận đúng thủ tục và chuyển sang phần hướng dẫn.");
    setConversation((prev) => [
      ...prev,
      {
        id: nextId("message"),
        role: "user",
        content: label,
      },
    ]);
    setPhase("guide");
  }

  async function performIntake(
    message: string,
    options?: { appendUserMessage?: boolean; displayMessage?: string },
  ) {
    const appendUserMessage = options?.appendUserMessage ?? true;
    const trimmed = message.trim();
    if (!trimmed) return;
    const visibleMessage = (options?.displayMessage ?? trimmed).trim();

    const previousBackendHistory = backendHistory;
    const optimisticBackendHistory = appendUserMessage
      ? [...previousBackendHistory, { role: "user" as const, content: trimmed }]
      : [...previousBackendHistory, { role: "user" as const, content: trimmed }];

    if (appendUserMessage) {
      setConversation((prev) => [
        ...prev,
        {
          id: nextId("message"),
          role: "user",
          content: visibleMessage,
        },
      ]);
    }

    setLoading(true);
    setError("");
    const loadingStartedAt = Date.now();

    try {
      const nextAnswers = result?.clarifying_question_id
        ? { ...answers, [result.clarifying_question_id]: trimmed }
        : answers;

      const response = await submitIntake({
        message: trimmed,
        history: previousBackendHistory,
        answers: nextAnswers,
        session_id: sessionId,
        procedure_code: result?.procedure?.code,
        group_key: selectedGroupKey,
        subdomain_key: selectedSubdomainKey,
      });

      setSessionId(response.session_id);
      setResult(response);
      setAnswers(response.answers || nextAnswers);
      if (response.domain_key) {
        setSelectedGroupKey(response.domain_key);
      }
      const inferredSubdomainKey =
        response.answers?.subdomain_key || response.workflow_state?.slots?.subdomain_key;
      if (typeof inferredSubdomainKey === "string" && inferredSubdomainKey) {
        setSelectedSubdomainKey(inferredSubdomainKey);
      }
      setBackendHistory([
        ...optimisticBackendHistory,
        ...(response.clarifying_question
          ? [{ role: "assistant" as const, content: response.clarifying_question }]
          : []),
      ]);

      if (response.clarifying_question) {
        let promptId: string | undefined;

        if (response.quick_replies && response.quick_replies.length > 0) {
          promptId = nextId("selector");
          const options = response.quick_replies.map((r: any) => {
            const rawValue = typeof r === "string" ? r : (r.value || r.label);
            
            if (typeof rawValue === "string") {
              const matchedGroup = groupMap.get(rawValue);
              if (matchedGroup) return { label: matchedGroup.label, value: rawValue };
              
              for (const group of groupMap.values()) {
                const matchedSubdomain = group.subdomains.find((s) => s.subdomain_key === rawValue);
                if (matchedSubdomain) return { label: matchedSubdomain.label, value: rawValue };
              }
            }
            
            return typeof r === "string" ? { label: r, value: r } : r;
          });
          setSelectorPrompts((prev) => ({
            ...prev,
            [promptId!]: {
              id: promptId!,
              type: "quick_reply",
              status: "active",
              options
            }
          }));
          setActiveSelectorTurnId(promptId);
        }

        setConversation((prev) => [
          ...prev,
          {
            id: nextId("message"),
            role: "assistant",
            content: response.clarifying_question || "",
            selectorPromptId: promptId,
          },
        ]);
      }

      if (response.status === "completed") {
        if (response.procedure) {
          queueProcedureConfirmation(response.procedure.title);
        } else {
          setPhase("guide");
        }
      }
    } catch (reason) {
      setBackendHistory(previousBackendHistory);
      setError(reason instanceof Error ? reason.message : "Không thể xử lý yêu cầu.");
    } finally {
      const elapsed = Date.now() - loadingStartedAt;
      if (elapsed < minLoadingMs) {
        await new Promise((resolve) => setTimeout(resolve, minLoadingMs - elapsed));
      }
      setLoading(false);
    }
  }

  async function send(event?: FormEvent, payloadMessage?: string, displayMessage?: string) {
    event?.preventDefault();
    const rawMessage = payloadMessage ?? input;
    const message = rawMessage.trim();
    if (!message || loading || blockingSelector) return;

    const shownMessage = (displayMessage ?? rawMessage).trim();
    setError("");
    setInput("");
    if (inputRef.current) inputRef.current.style.height = "auto";

    await performIntake(message, { appendUserMessage: true });
  }
  async function handleGroupSelect(groupKey: string) {
    const group = groupMap.get(groupKey);
    if (!group || !activeSelectorTurnId) return;

    completeSelector(activeSelectorTurnId, group.label, "Nhóm này sẽ được giữ làm context cho luồng hiện tại.");
    setSelectedGroupKey(group.group_key);
    setSelectedSubdomainKey(undefined);
    setConversation((prev) => [
      ...prev,
      {
        id: nextId("message"),
        role: "user",
        content: `Nhóm tôi chọn: ${group.label}`,
      },
    ]);
    
    setLoading(true);
    setTimeout(() => {
      setLoading(false);
      queueSelector("subdomain", group);
    }, 500);
  }

  async function handleSubdomainSelect(subdomainKey: string) {
    if (!selectedGroup || !activeSelectorTurnId) return;
    const subdomain = selectedGroup.subdomains.find((item) => item.subdomain_key === subdomainKey);
    if (!subdomain) return;

    completeSelector(activeSelectorTurnId, subdomain.label, "Assistant sẽ bám trực tiếp vào nhánh workflow này.");
    setSelectedSubdomainKey(subdomain.subdomain_key);
    setConversation((prev) => [
      ...prev,
      {
        id: nextId("message"),
        role: "user",
        content: `Nhánh tôi chọn: ${subdomain.label}`,
      },
    ]);

    setLoading(true);
    setTimeout(() => {
      setLoading(false);
      if (pendingNeed) {
        const nextNeed = pendingNeed;
        setPendingNeed(null);
        void performIntake(nextNeed, { appendUserMessage: false });
      }
    }, 500);
  }

  function handleQuickReplySelect(promptId: string, value: string | string[], label: string) {
    completeSelector(promptId, label, "Đã chọn gợi ý từ hệ thống.");
    
    const valueStr = Array.isArray(value) ? value.join(", ") : value;
    
    if (typeof value === "string") {
      if (groupMap.has(value)) {
        setSelectedGroupKey(value);
        setSelectedSubdomainKey(undefined);
      } else if (selectedGroup?.subdomains.some((item) => item.subdomain_key === value)) {
        setSelectedSubdomainKey(value);
      }
    }
    
    void performIntake(valueStr, { appendUserMessage: true, displayMessage: label });
  }

  function reset() {
    setPhase("need");
    setResult(null);
    setValidation(null);
    setConversation([]);
    setBackendHistory([]);
    setSessionId(undefined);
    setAnswers({});
    setInput("");
    setError("");
    setPendingNeed(null);
    setSelectedGroupKey(undefined);
    setSelectedSubdomainKey(undefined);
    setSelectorPrompts({});
    setActiveSelectorTurnId(undefined);
  }

  if (phase === "guide" && result?.procedure) {
    return (
      <div className={`assistant-shell ${compact ? "compact" : ""}`}>
        <AssistantBar phase={phase} onReset={reset} />
        <GuidanceView result={result} onContinue={() => setPhase("validate")} />
      </div>
    );
  }

  if (phase === "validate" && result?.procedure) {
    return (
      <div className={`assistant-shell ${compact ? "compact" : ""}`}>
        <AssistantBar phase={phase} onReset={reset} />
        <DynamicForm
          procedureCode={result.procedure.code}
          onBack={() => setPhase("guide")}
          onContinue={(checked) => {
            setValidation(checked);
            setPhase("next");
          }}
        />
      </div>
    );
  }

  if (phase === "next" && result?.procedure) {
    return (
      <div className={`assistant-shell ${compact ? "compact" : ""}`}>
        <AssistantBar phase={phase} onReset={reset} />
        <NextStepsView
          result={result}
          validation={validation}
          onBack={() => setPhase("validate")}
          onRestart={reset}
        />
      </div>
    );
  }

  return (
    <div className={`assistant-shell ${compact ? "compact" : ""}`}>
      {(compact && showIntroModal) && (
        <div style={{ position: "absolute", inset: 0, zIndex: 50, backgroundColor: "var(--background, #f9fafb)", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "2rem", textAlign: "center", borderRadius: "var(--radius-lg, 12px)" }}>
          <span className="ai-orb" style={{ margin: "0 auto 1.5rem", transform: "scale(1.5)", background: "transparent", boxShadow: "none" }}>
            <Image src="/govlogo.png" alt="GovEase AI" width={32} height={32} />
          </span>
          <small style={{ color: "var(--primary, #D97A4A)", fontWeight: 600, letterSpacing: "1px", textTransform: "uppercase" }}>GovEase AI</small>
          <h1 style={{ fontSize: "1.75rem", color: "var(--text, #111827)", margin: "0.5rem 0 1rem" }}>Chào bạn, hôm nay mình có thể giúp gì cho bạn?</h1>
          <p style={{ color: "var(--text-light, #6b7280)", lineHeight: 1.6, marginBottom: "2rem", maxWidth: "400px" }}>
            Bạn cứ mô tả ngắn gọn việc mình đang cần làm. Mình sẽ giúp chọn đúng nhóm nhu cầu, đi đúng nhánh và dẫn bạn tới thủ tục phù hợp nhất.
          </p>
          <button style={{ backgroundColor: "var(--primary, #D97A4A)", color: "white", border: "none", padding: "0.75rem 2rem", borderRadius: "99px", fontSize: "1rem", fontWeight: 600, cursor: "pointer", boxShadow: "0 4px 6px rgba(217, 122, 74, 0.2)" }} onClick={() => {
            if (typeof window !== "undefined") {
              localStorage.setItem("botIntroSeen", "true");
            }
            setShowIntroModal(false);
          }}>
            Bắt đầu trò chuyện
          </button>
        </div>
      )}
      <AssistantBar phase={phase} onReset={reset} />
      <div className="intake-panel">
        <div className="chat-scroll-area" ref={scrollRef}>
          {!compact && (
            <div className="assistant-intro">
              <span className="ai-orb" style={{ background: "transparent", boxShadow: "none" }}>
                <Image src="/govlogo.png" alt="GovEase AI" width={28} height={28} />
              </span>
              <div>
                <small>GovEase AI</small>
                <h1>Chào bạn, hôm nay mình có thể giúp gì cho bạn?</h1>
                <p>
                  Bạn cứ mô tả ngắn gọn việc mình đang cần làm. Mình sẽ giúp chọn đúng nhóm
                  nhu cầu, đi đúng nhánh và dẫn bạn tới thủ tục phù hợp nhất.
                </p>
              </div>
            </div>
          )}



          {!conversation.length && (
            <div className="examples">
              <span>Gợi ý nhu cầu phổ biến:</span>
              {examples.map((example) => (
                <button onClick={() => send(undefined, example, example)} key={example}>
                  <Icon name="search" />
                  {example}
                </button>
              ))}
            </div>
          )}

          {!!conversation.length && (
            <div className="conversation">
              {conversation.map((message) => {
                const prompt = message.selectorPromptId ? selectorPrompts[message.selectorPromptId] : undefined;
                return (
                  <div className={`bubble ${message.role}`} key={message.id}>
                    <span>
                      {message.role === "assistant" ? <Icon name="bot" /> : <Icon name="user" />}
                    </span>
                    <div className="bubble-stack">
                      <p className="message-content">
                        {message.content.split('\n').map((para, idx, arr) => {
                          const isQuestion = para.includes('?');
                          const isProcedureConfirmation = prompt?.type === "procedure_confirmation" && para.includes(":");
                          const colonIndex = isProcedureConfirmation ? para.indexOf(":") : -1;
                          const prefix = isProcedureConfirmation ? para.slice(0, colonIndex + 1) : "";
                          const suffix = isProcedureConfirmation ? para.slice(colonIndex + 1).trimStart() : "";
                          return (
                            <span key={idx} style={isQuestion && message.role === "assistant" && !isProcedureConfirmation ? { fontWeight: 600, color: "#111827" } : {}}>
                              {isProcedureConfirmation ? (
                                <>
                                  {prefix} <strong style={{ color: "#111827" }}>{suffix}</strong>
                                </>
                              ) : (
                                para
                              )}
                              {idx < arr.length - 1 && <br />}
                            </span>
                          );
                        })}
                      </p>
                      {prompt?.status === "active" && prompt.type === "group" ? (
                        <InlineSelectorBlock
                          type="group"
                          title={prompt.title ?? "Chọn nhóm nhu cầu"}
                          description={prompt.description ?? ""}
                          options={groups}
                          disabled={loading}
                          onSelect={handleGroupSelect}
                        />
                      ) : null}
                      {prompt?.status === "active" && prompt.type === "subdomain" && selectedGroup ? (
                        <InlineSelectorBlock
                          type="subdomain"
                          title={prompt.title ?? "Chọn nhánh cụ thể"}
                          description={prompt.description ?? ""}
                          options={selectedGroup.subdomains}
                          disabled={loading}
                          onSelect={handleSubdomainSelect}
                        />
                      ) : null}
                      {prompt?.status === "active" && prompt.type === "quick_reply" && prompt.options ? (
                        prompt.options.length > 5 ? (
                          <InlineSelectorBlock
                            type="quick_reply"
                            title={prompt.title}
                            description={prompt.description}
                            options={prompt.options as {label: string, value: string}[]}
                            disabled={loading}
                            isMulti={prompt.title?.toLowerCase().includes("nhiều") || prompt.title?.toLowerCase().includes("các")}
                            onSelect={(val, label) => handleQuickReplySelect(prompt.id, val, label)}
                          />
                        ) : (
                          <div className={`quick-intake ${prompt.options.length === 2 && (prompt.options[0].label.toLowerCase() === 'có' || prompt.options[0].label.toLowerCase() === 'yes') ? 'yes-no-group' : ''}`} style={{ marginTop: "12px" }}>
                            {prompt.options.map((item) => (
                              <button
                                type="button"
                                key={`${item.value}-${item.label}`}
                                className="quick-intake-button"
                                onClick={() => handleQuickReplySelect(prompt.id, item.value, item.label)}
                                disabled={loading}
                              >
                                <strong>{item.label}</strong>
                                {item.description && <span>{item.description}</span>}
                              </button>
                            ))}
                          </div>
                        )
                      ) : null}
                      {prompt?.status === "active" && prompt.type === "procedure_confirmation" && prompt.options ? (
                        <div className="quick-intake yes-no-group" style={{ marginTop: "12px" }}>
                          {prompt.options.map((item) => (
                            <button
                              type="button"
                              key={`${item.value}-${item.label}`}
                              className="quick-intake-button"
                              onClick={() =>
                                handleProcedureConfirmation(
                                  prompt.id,
                                  item.value === "restart" ? "restart" : "confirm",
                                  item.label,
                                )
                              }
                              disabled={loading}
                            >
                              <strong>{item.label}</strong>
                            </button>
                          ))}
                        </div>
                      ) : null}
                      {prompt?.status === "completed" && prompt.selectedLabel ? (
                        <SelectionSummaryChip
                          selectedLabel={prompt.selectedLabel}
                          helperText={prompt.helperText || "Đã xác nhận trong luồng chat này."}
                        />
                      ) : null}
                    </div>
                  </div>
                );
              })}
              {loading && (
                <div className="bubble assistant bubble-loading">
                  <span>
                    <Image src="/govlogo.png" alt="GovEase AI" width={20} height={20} />
                  </span>
                  <p>
                    <span className="bubble-loading-dots" aria-hidden="true">
                      <i />
                      <i />
                      <i />
                    </span>
                    <strong>{loadingMessage}</strong>
                  </p>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="chat-input-area">
          <form className="need-composer" onSubmit={send}>
            <textarea
              ref={inputRef}
              value={input}
              onChange={(event) => {
                setInput(event.target.value);
                const target = event.target;
                target.style.height = "auto";
                target.style.height = `${target.scrollHeight}px`;
              }}
              placeholder={
                activeSelector?.type === "group"
                  ? "Chọn nhóm Công dân..."
                  : activeSelector?.type === "subdomain"
                    ? "Chọn nhánh cụ thể..."
                    : result?.needs_clarification
                      ? "Nhập câu trả lời..."
                      : "Ví dụ: Xin cấp giấy phép lái xe..."
              }
              rows={1}
              disabled={blockingSelector}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  void send();
                }
              }}
            />
            <button
              type="submit"
              disabled={loading || !input.trim() || blockingSelector}
              className={loading ? "is-loading" : ""}
            >
              {loading ? <span className="spinner" /> : <Icon name="send" />}
              <span>{loading ? "Đang xử lý" : "Gửi yêu cầu"}</span>
            </button>
          </form>

          {error && (
            <div className="inline-error">
              <Icon name="warning" />
              <div>
                <strong>Không thể kết nối</strong>
                <span>{error}</span>
              </div>
              <button onClick={() => inputRef.current?.focus()}>Thử lại</button>
            </div>
          )}

          <div className="trust-row">
            <span>
              <Icon name="shield" />
              Dữ liệu từ nguồn chính thống
            </span>
            <span>
              <Icon name="check" />
              Luồng chọn nhóm và nhánh ngay trong chat
            </span>
            <span>
              <Icon name="file" />
              Kiểm tra trước khi nộp
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

function AssistantBar({ phase, onReset }: { phase: string; onReset: () => void }) {
  const steps = [
    { key: "need", label: "Nêu nhu cầu" },
    { key: "guide", label: "Nhận hướng dẫn" },
    { key: "validate", label: "Kiểm tra thông tin" },
    { key: "next", label: "Bước tiếp theo" },
  ];
  const active = steps.findIndex((step) => step.key === phase);

  return (
    <div className="assistant-bar">
      <div className="mini-brand">
        <span>
          <Image src="/govlogo.png" alt="GovEase AI" width={20} height={20} />
        </span>
        <div>
          <strong>GovEase AI</strong>
          <small>Trợ lý dịch vụ công</small>
        </div>
      </div>
      <div className="progress-steps">
        {steps.map((step, index) => (
          <div
            className={`${index <= active ? "active" : ""} ${index < active ? "done" : ""}`}
            key={step.key}
          >
            <i>{index < active ? <Icon name="check" /> : index + 1}</i>
            <span>{step.label}</span>
          </div>
        ))}
      </div>
      <button className="restart" onClick={onReset}>
        <Icon name="refresh" />
      </button>
    </div>
  );
}
