const chatForm = document.getElementById("chatForm");
const chatLog = document.getElementById("chatLog");
const messageInput = document.getElementById("messageInput");
const quickRepliesEl = document.getElementById("quickReplies");
const modeButtons = document.querySelectorAll(".mode-chip");

const sessionIdEl = document.getElementById("sessionId");
const domainLabelEl = document.getElementById("domainLabel");
const assistModeEl = document.getElementById("assistMode");
const personaLabelEl = document.getElementById("personaLabel");
const nodeIdEl = document.getElementById("nodeId");
const completedEl = document.getElementById("completed");
const slotStateEl = document.getElementById("slotState");
const resultCardEl = document.getElementById("resultCard");

let sessionId = null;
let sending = false;
let preferredMode = "guided";

function addBubble(role, text) {
  const wrapper = document.createElement("div");
  wrapper.className = `bubble ${role}`;
  wrapper.textContent = text;
  chatLog.appendChild(wrapper);
  chatLog.scrollTop = chatLog.scrollHeight;
}

function renderResult(result) {
  if (!result) {
    resultCardEl.className = "result-empty";
    resultCardEl.innerHTML = "Chưa chốt được thủ tục.";
    return;
  }

  resultCardEl.className = "result-card";
  resultCardEl.innerHTML = `
    <p class="result-code">Mã ${result.procedure_code}</p>
    <h3>${result.procedure_name}</h3>
    <p><strong>Cơ quan:</strong> ${result.agency}</p>
    <p><strong>Nơi nộp / nhóm:</strong> ${result.submit_to}</p>
    <p><strong>Lý do chọn route:</strong> ${result.why_this_route}</p>
    <p><strong>Pre-check:</strong> ${result.summary}</p>
    <p><a href="${result.source_url}" target="_blank" rel="noreferrer">Mở nguồn Dịch vụ công</a></p>
  `;
}

function renderQuickReplies(items) {
  quickRepliesEl.innerHTML = "";

  if (!items || items.length === 0) {
    quickRepliesEl.innerHTML = `<span class="quick-empty">Chưa có gợi ý nhanh ở bước này.</span>`;
    return;
  }

  items.forEach((item) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "quick-reply";
    button.innerHTML = `<span class="quick-reply-label">${item.label}</span>`;
    button.addEventListener("click", () => sendMessage(item.value || item.label));
    quickRepliesEl.appendChild(button);
  });
}

function updateState(payload) {
  sessionId = payload.session_id;
  sessionIdEl.textContent = payload.session_id || "Chưa tạo";
  domainLabelEl.textContent = payload.domain_label || "Chưa chọn";
  assistModeEl.textContent = payload.assist_mode_label || "Chưa xác định";
  personaLabelEl.textContent = payload.persona_label || "Chưa xác định";
  nodeIdEl.textContent = payload.current_node_id || "Đã chốt route";
  completedEl.textContent = payload.completed ? "Đã chốt thủ tục" : "Đang hỏi đáp";
  slotStateEl.textContent = JSON.stringify(payload.slots || {}, null, 2);
  renderResult(payload.result);
  renderQuickReplies(payload.quick_replies || []);
}

async function sendMessage(message) {
  if (sending) return;
  sending = true;

  addBubble("user", message);
  messageInput.value = "";

  const response = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: sessionId,
      message,
      preferred_mode: preferredMode,
    }),
  });

  if (!response.ok) {
    addBubble("assistant", "Có lỗi xảy ra khi gọi backend.");
    sending = false;
    return;
  }

  const payload = await response.json();
  addBubble("assistant", payload.message);
  updateState(payload);
  sending = false;
}

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = messageInput.value.trim();
  if (!message) return;
  await sendMessage(message);
});

modeButtons.forEach((button) => {
  button.addEventListener("click", () => {
    preferredMode = button.dataset.mode || "guided";
    modeButtons.forEach((item) => item.classList.toggle("active", item === button));
  });
});

modeButtons.forEach((item) => item.classList.toggle("active", item.dataset.mode === preferredMode));

addBubble(
  "assistant",
  "Chào bạn, mình là GovEase AI. Bạn đang cần hỗ trợ về khai sinh hay cư trú?"
);

renderQuickReplies([
  { value: "birth_registration", label: "Khai sinh" },
  { value: "residence_management", label: "Cư trú" },
]);
