"use client";

import Image from "next/image";
import { useState } from "react";
import type { CitizenGroupOption } from "../lib/types";
import { Icon } from "./Icon";
import { CitizenAssistant } from "./CitizenAssistant";

export function FloatingAssistant({ groups }: { groups: CitizenGroupOption[] }) {
  const [open, setOpen] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  function refreshChat() {
    setRefreshKey(prev => prev + 1);
  }

  return (
    <div className={`floating-assistant ${open ? "open" : ""}`}>
      <div className={`assistant-modal ${open ? "open" : ""}`} role="dialog" aria-modal={open} aria-hidden={!open} aria-label="Trợ lý GovEase AI">
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
                <button className="expand-chat" type="button" onClick={refreshChat} aria-label="Làm mới cuộc trò chuyện">
                  <Icon name="refresh" />
                  <span>Làm mới</span>
                </button>
                <button onClick={() => setOpen(false)} aria-label="Đóng">
                  <Icon name="close" />
                </button>
              </nav>
            </header>
            <div className="assistant-popup-body">
              <CitizenAssistant key={refreshKey} compact groups={groups} />
            </div>
          </div>
        </div>
      <button className={`floating-button ${open ? "open" : ""}`} onClick={() => setOpen(!open)} aria-label="Trợ lý GovEase AI">
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
