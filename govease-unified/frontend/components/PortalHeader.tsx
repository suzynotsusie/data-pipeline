"use client";

import { useState } from "react";
import { Icon } from "./Icon";

const links = [
  "Thông tin và dịch vụ",
  "Thanh toán trực tuyến",
  "Phản ánh kiến nghị",
  "Đánh giá chất lượng phục vụ",
  "Hỗ trợ",
];

export function PortalHeader() {
  const [open, setOpen] = useState(false);

  return (
    <header className="portal-header">
      <div className="portal-brand page-width">
        <div className="emblem-placeholder" aria-hidden="true">
          <span>★</span>
          <small>VN</small>
        </div>
        <div className="portal-title">
          <strong>Cổng Dịch vụ công Quốc gia</strong>
          <span>Kết nối, cung cấp thông tin và dịch vụ công mọi lúc, mọi nơi</span>
        </div>
        <div className="account-actions">
          <button className="text-button">
            <Icon name="user" />
            Đăng ký
          </button>
          <button className="outline-button">Đăng nhập</button>
        </div>
        <button className="mobile-menu" onClick={() => setOpen(!open)} aria-label="Mở điều hướng">
          <Icon name={open ? "close" : "menu"} />
        </button>
      </div>
      <nav className={`portal-nav ${open ? "open" : ""}`} aria-label="Điều hướng chính">
        <div className="page-width nav-inner">
          <a className="home-link active" href="#top" aria-label="Trang chủ">
            <Icon name="home" />
          </a>
          {links.map((link) => (
            <a href={`/demo?feature=${encodeURIComponent(link)}`} key={link}>
              {link}
            </a>
          ))}
        </div>
      </nav>
    </header>
  );
}
