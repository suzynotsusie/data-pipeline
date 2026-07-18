import { CitizenAssistant } from "../components/CitizenAssistant";
import { FloatingAssistant } from "../components/FloatingAssistant";
import { Icon } from "../components/Icon";
import { PortalHeader } from "../components/PortalHeader";

const highlights = [
  "Dịch vụ công trực tuyến",
  "Dịch vụ công trực tuyến của Đảng",
  "Dịch vụ công liên thông: Khai sinh, Khai tử",
];

const notices = [
  {
    title: "Chuyển đổi, vận hành chính thức Cổng Dịch vụ công Quốc gia",
    date: "Ngày 29/05/2026",
  },
  {
    title: "Thông báo về việc dừng vận hành một số thủ tục để nâng cấp dịch vụ",
    date: "Ngày 21/04/2026",
  },
  {
    title: "Công bố dữ liệu quốc gia về bảo hiểm và hướng dẫn kết nối, khai thác sử dụng",
    date: "Ngày 11/02/2026",
  },
];

const citizenGroups = [
  "Có con nhỏ",
  "Học tập",
  "Việc làm",
  "Cư trú và giấy tờ tùy thân",
  "Hôn nhân và gia đình",
  "Điện lực, nhà ở, đất đai",
  "Sức khỏe và y tế",
  "Phương tiện và người lái",
  "Hưu trí",
  "Người thân qua đời",
  "Giải quyết khiếu kiện",
];

const businessGroups = [
  "Khởi sự kinh doanh",
  "Lao động và bảo hiểm xã hội",
  "Tài chính doanh nghiệp",
  "Điện lực, đất đai, xây dựng",
  "Thương mại, quảng cáo",
  "Sở hữu trí tuệ, đăng ký tài sản",
  "Thành lập chi nhánh, văn phòng đại diện",
  "Đấu thầu, mua sắm công",
  "Tái cấu trúc doanh nghiệp",
  "Giải quyết tranh chấp hợp đồng",
  "Tạm dừng, chấm dứt hoạt động",
];

export default function Home() {
  return (
    <main id="top" className="portal-page">
      <PortalHeader />

      <section className="portal-hero">
        <div className="hero-pattern" />
        <div className="page-width hero-content">
          <div className="portal-search">
            <input placeholder="Nhập từ khoá tìm kiếm" />
            <a href="#assistant">Tìm kiếm nâng cao</a>
            <button aria-label="Tìm kiếm">
              <Icon name="search" />
            </button>
          </div>

          <div className="quick-services">
            {highlights.map((item) => (
              <article key={item}>
                <strong>{item}</strong>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="notice-strip">
        <div className="page-width notice-layout">
          <button className="notice-arrow" aria-label="Xem tin trước">
            <Icon name="arrow" />
          </button>
          <div className="notice-list">
            {notices.map((item) => (
              <article key={item.title}>
                <strong>{item.title}</strong>
                <span>{item.date}</span>
              </article>
            ))}
          </div>
          <div className="notice-art" aria-hidden="true" />
        </div>
      </section>

      <section className="service-directory page-width">
        <div className="service-column">
          <div className="service-column-title">Công dân</div>
          <div className="service-list">
            {citizenGroups.map((item, index) => (
              <a className="service-row" href="#assistant" key={item}>
                <span className="service-icon tone-teal">{String(index + 1).padStart(2, "0")}</span>
                <strong>{item}</strong>
              </a>
            ))}
          </div>
        </div>

        <div className="service-column">
          <div className="service-column-title">Doanh nghiệp</div>
          <div className="service-list">
            {businessGroups.map((item, index) => (
              <a className="service-row" href="#assistant" key={item}>
                <span className="service-icon tone-red">{String(index + 1).padStart(2, "0")}</span>
                <strong>{item}</strong>
              </a>
            ))}
          </div>
        </div>
      </section>

      <section className="assistant-surface">
        <div className="page-width assistant-layout">
          <aside className="citizen-menu">
            <div className="menu-heading">
              <Icon name="user" />
              <div>
                <small>PHẠM VI DEMO</small>
                <strong>2 thủ tục</strong>
              </div>
            </div>
            {["Đăng ký khai sinh", "Đăng ký tạm trú"].map((item, index) => (
              <a className="featured" href="#assistant" key={item}>
                <span>{String(index + 1).padStart(2, "0")}</span>
                {item}
                <Icon name="arrow" />
              </a>
            ))}
            <div className="demo-scope-note">Các nhóm dịch vụ khác chưa được triển khai trong bản pilot.</div>
            <div className="source-mini">
              <Icon name="shield" />
              <p>Thông tin thủ tục trong demo được tổng hợp từ nguồn chính thống để mô phỏng trải nghiệm thực tế.</p>
              <a href="https://dichvucong.gov.vn" target="_blank" rel="noreferrer">
                dichvucong.gov.vn <Icon name="external" />
              </a>
            </div>
          </aside>

          <div className="assistant-section" id="assistant">
            <div className="section-kicker">
              <span>TRỢ LÝ DỊCH VỤ CÔNG</span>
              <i />
            </div>
            <h2>Hoàn thiện hồ sơ đúng ngay từ đầu</h2>
            <p className="section-lead">Một luồng hỗ trợ xuyên suốt ngay trong cổng dịch vụ công hiện có.</p>
            <CitizenAssistant />
          </div>
        </div>
      </section>

      <footer className="portal-footer">
        <div className="page-width footer-bar">
          <span>Cơ quan chủ quản: Văn phòng Chính phủ</span>
          <span>www.dichvucong.gov.vn</span>
          <span>Tổng đài hỗ trợ: 18001096</span>
          <span>Email: dichvucong@chinhphu.vn</span>
        </div>
      </footer>

      <FloatingAssistant />
    </main>
  );
}
