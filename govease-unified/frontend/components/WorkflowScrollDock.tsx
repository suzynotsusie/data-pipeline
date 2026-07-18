"use client";

import { useEffect, useRef, useState } from "react";
import { Icon } from "./Icon";

export function WorkflowScrollDock() {
  const anchorRef = useRef<HTMLDivElement>(null);
  const [canScrollUp, setCanScrollUp] = useState(false);
  const [canScrollDown, setCanScrollDown] = useState(false);

  useEffect(() => {
    const anchor = anchorRef.current;
    const container = anchor?.closest("[data-workflow-scroll]") as HTMLElement | null;
    if (!container) return;

    const update = () => {
      setCanScrollUp(container.scrollTop > 16);
      setCanScrollDown(container.scrollTop + container.clientHeight < container.scrollHeight - 16);
    };

    update();
    container.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
    return () => {
      container.removeEventListener("scroll", update);
      window.removeEventListener("resize", update);
    };
  }, []);

  function scrollByAmount(direction: "up" | "down") {
    const anchor = anchorRef.current;
    const container = anchor?.closest("[data-workflow-scroll]") as HTMLElement | null;
    if (!container) return;
    const amount = Math.max(180, Math.round(container.clientHeight * 0.52));
    container.scrollBy({ top: direction === "down" ? amount : -amount, behavior: "smooth" });
  }

  return (
    <div className="workflow-scroll-dock" ref={anchorRef}>
      <button
        type="button"
        className={`workflow-scroll-button ${canScrollUp ? "is-active" : "is-idle"}`}
        onClick={() => scrollByAmount("up")}
        aria-label="Cuộn lên"
        title="Cuộn lên"
        disabled={!canScrollUp}
      >
        <Icon name="arrow" />
      </button>
      <button
        type="button"
        className={`workflow-scroll-button ${canScrollDown ? "is-active" : "is-idle"}`}
        onClick={() => scrollByAmount("down")}
        aria-label="Cuộn xuống"
        title="Cuộn xuống"
        disabled={!canScrollDown}
      >
        <Icon name="arrow" />
      </button>
    </div>
  );
}
