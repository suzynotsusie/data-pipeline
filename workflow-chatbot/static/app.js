const chatForm = document.getElementById("chatForm");
const chatLog = document.getElementById("chatLog");
const messageInput = document.getElementById("messageInput");
const quickRepliesEl = document.getElementById("quickReplies");
const modeButtons = document.querySelectorAll(".mode-chip");

// New Phase 7 elements
const groupSelect = document.getElementById("groupSelect");
const subdomainSelect = document.getElementById("subdomainSelect");
const refreshChatBtn = document.getElementById("refreshChatBtn");
const closeOverlayBtn = document.getElementById("closeOverlayBtn");
const introOverlay = document.getElementById("introOverlay");
const introContinueBtn = document.getElementById("introContinueBtn");

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
  quickRepliesEl.className = "quick-replies";

  if (!items || items.length === 0) {
    quickRepliesEl.innerHTML = `<span class="quick-empty">Chưa có gợi ý nhanh ở bước này.</span>`;
    return;
  }

  // Phase 7: Check Yes/No layout
  const isYesNo = items.length === 2 && items.some(i => i.value === "yes" || i.label === "Có") && items.some(i => i.value === "no" || i.label === "Không");
  if (isYesNo) {
    quickRepliesEl.classList.add("yes-no-group");
  }

  // Phase 7: Multi-select detection (assume payload item structure or just heuristics)
  const isMultiSelect = items.some(i => i.is_multi_select || i.multi_select);
  if (isMultiSelect) {
    const select = document.createElement("select");
    select.multiple = true;
    select.className = "multi-select-dropdown";
    items.forEach(item => {
      const option = document.createElement("option");
      option.value = item.value || item.label;
      option.textContent = item.label;
      select.appendChild(option);
    });
    const btn = document.createElement("button");
    btn.textContent = "Xác nhận lựa chọn";
    btn.className = "btn-confirm-multi";
    btn.onclick = () => {
      const selected = Array.from(select.selectedOptions).map(opt => opt.value);
      if (selected.length > 0) {
        sendMessage(JSON.stringify(selected)); // Or handle formatting as needed
      }
    };
    quickRepliesEl.appendChild(select);
    quickRepliesEl.appendChild(btn);
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
      group_key: groupSelect ? groupSelect.value : null,
      subdomain_key: subdomainSelect ? subdomainSelect.value : null,
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

// Phase 7 UI Handlers
document.addEventListener("DOMContentLoaded", () => {
  // Intro Overlay
  if (!localStorage.getItem("botIntroSeen")) {
    introOverlay.style.display = "flex";
  }
  introContinueBtn.addEventListener("click", () => {
    localStorage.setItem("botIntroSeen", "true");
    introOverlay.style.display = "none";
  });

  // Auto-resize textarea
  messageInput.addEventListener("input", function() {
    this.style.height = "auto";
    this.style.height = (this.scrollHeight) + "px";
  });

  // Load Catalog
  let globalCatalog = {};
  fetch("/api/catalog").then(res => res.json()).then(data => {
    globalCatalog = data;
    groupSelect.innerHTML = '<option value="">-- Chọn nhóm --</option>';
    if(data && Object.keys(data).length > 0) {
      for (const groupKey in data) {
        const group = data[groupKey];
        const opt = document.createElement("option");
        opt.value = groupKey;
        opt.textContent = group.label;
        groupSelect.appendChild(opt);
      }
    }
  }).catch(err => console.error("Error loading catalog:", err));

  groupSelect.addEventListener("change", (e) => {
    const groupKey = e.target.value;
    subdomainSelect.innerHTML = '<option value="">-- Chọn subdomain --</option>';
    if(groupKey && globalCatalog[groupKey] && globalCatalog[groupKey].subdomains) {
      const subdomains = globalCatalog[groupKey].subdomains;
      for (const subKey in subdomains) {
        const sub = subdomains[subKey];
        const opt = document.createElement("option");
        opt.value = subKey;
        opt.textContent = sub.label;
        subdomainSelect.appendChild(opt);
      }
    }
  });

  // Header Refresh/Close
  refreshChatBtn.addEventListener("click", () => {
    chatLog.innerHTML = "";
    sessionId = null;
    addBubble("assistant", "Chào bạn, mình đã làm mới luồng. Bạn cần hỗ trợ gì?");
    renderQuickReplies([
      { value: "birth_registration", label: "Khai sinh" },
      { value: "residence_management", label: "Cư trú" },
    ]);
  });

  closeOverlayBtn.addEventListener("click", () => {
    // Basic close logic
    alert("Chat overlay closed");
  });
});
