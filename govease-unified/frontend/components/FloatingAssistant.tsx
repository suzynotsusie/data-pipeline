"use client";

import Image from "next/image";
import { useState } from "react";
import { Icon } from "./Icon";
import { CitizenAssistant } from "./CitizenAssistant";

export function FloatingAssistant() {
  const [open, setOpen] = useState(false);

  function openExpandedChat() {
    const popup = window.open(new URL("/widget", window.location.origin).toString(), "govease-chat");
    if (!popup) window.location.assign("/widget");
    else popup.focus();
  }

  return (
    <div className={`floating-assistant ${open ? "open" : ""}`}>
      {open && (
        <div className="assistant-modal" role="dialog" aria-modal="false" aria-label="Trợ lý GovEase AI">
          <div className="assistant-modal-panel">
            <header className="assistant-popup-header">
              <div>
                <span className="assistant-popup-logo">
                  <Image src="/govlogo.png" alt="GovEase AI" width={28} height={28} className="assistant-popup-logo-image" />
                </span>
                <div>
                  <strong>GovEase AI</strong>
                  <small>
                    <i />
                    Đang hoạt động
                  </small>
                </div>
              </div>
              <nav>
                <button className="expand-chat" type="button" onClick={openExpandedChat} aria-label="Mở chatbot trong trang mới">
                  <Icon name="external" />
                  <span>Mở rộng</span>
                </button>
                <button onClick={() => setOpen(false)} aria-label="Đóng">
                  <Icon name="close" />
                </button>
              </nav>
            </header>
            <div className="assistant-popup-body">
              <CitizenAssistant compact />
            </div>
          </div>
        </div>
      )}
      <button className="floating-button floating-logo-button" onClick={() => setOpen(!open)} aria-label="Trợ lý GovEase AI">
        {open ? (
          <Icon name="close" />
        ) : (
          <span className="floating-logo-mark" aria-hidden="true">
            <Image src="/govlogo.png" alt="GovEase AI" width={48} height={48} className="floating-logo-image" priority />
          </span>
        )}
        <span>{open ? "Đóng" : "Trợ lý GovEase AI"}</span>
      </button>
    </div>
  );
}
