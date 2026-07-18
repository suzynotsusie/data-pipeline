import { CitizenAssistant } from "../components/CitizenAssistant";
import { FloatingAssistant } from "../components/FloatingAssistant";
import { Icon } from "../components/Icon";
import { PortalHeader } from "../components/PortalHeader";
import { getCitizenWorkflowCatalog } from "../lib/citizen-catalog";

const highlights = [
  {
    value: "11",
    label: "nhóm Công dân",
    note: "Bao phủ đủ các nhóm sự kiện đời sống đã được chuẩn hóa workflow.",
  },
  {
    value: "End-to-end",
    label: "đi trong chat",
    note: "Chọn nhóm, chọn nhánh, nhận hướng dẫn và kiểm tra hồ sơ trong cùng một luồng.",
  },
  {
    value: "24/7",
    label: "sẵn sàng demo",
    note: "Có thể thử trực tiếp trên portal hoặc widget nổi.",
  },
];

const notices = [
  {
    title: "Thông báo về việc dừng vận hành một số thủ tục để nâng cấp dịch vụ",
    date: "21/04/2026",
  },
  {
    title: "Chuyển đổi, vận hành chính thức Cổng Dịch vụ công Quốc gia",
    date: "29/05/2026",
  },
  {
    title: "Công bố dữ liệu quốc gia về bảo hiểm và hướng dẫn khai thác sử dụng",
    date: "11/02/2026",
  },
];

const businessGroups = [
  "Khởi sự kinh doanh",
  "Lao động và bảo hiểm xã hội",
  "Tài chính doanh nghiệp",
  "Điện lực, đất đai, xây dựng",
  "Thương mại, quảng cáo",
  "Đấu thầu, mua sắm công",
];

const trustSignals = [
  "Danh mục 11 nhóm Công dân đồng bộ trực tiếp từ catalog workflow",
  "Mỗi nhánh đều có selector ngay trong chat thay vì form tách rời",
  "Giữ lại trích dẫn và bước kiểm tra hồ sơ trước khi nộp",
];

const steps = [
  {
    index: "01",
    title: "Mô tả nhu cầu bằng ngôn ngữ tự nhiên",
    text: "Người dân chỉ cần nêu tình huống, chưa cần biết sẵn tên thủ tục.",
  },
  {
    index: "02",
    title: "Chọn nhóm và nhánh ngay trong chat",
    text: "Dropdown xuất hiện ngay dưới bubble assistant đang hỏi, giúp khóa đúng domain và subdomain.",
  },
  {
    index: "03",
    title: "Nhận checklist và kiểm tra trước khi nộp",
    text: "Sau khi route đúng workflow, hệ thống tiếp tục trả hướng dẫn và kiểm tra thông tin đầu vào.",
  },
];

export default async function Home() {
  const catalog = await getCitizenWorkflowCatalog();
  const citizenGroups = catalog.groups;
  const featuredGroups = citizenGroups.slice(0, 4);
  const totalSubdomains = citizenGroups.reduce((sum, item) => sum + item.subdomains.length, 0);

  return (
    <main id="top" className="portal-page">
      <PortalHeader />

      <section className="portal-hero">
        <div className="hero-pattern" />
        <div className="page-width hero-layout">
          <div className="hero-copy">
            <div className="hero-kicker">
              <span>GovEase AI workflow rollout</span>
              <i />
              <small>{citizenGroups.length} nhóm Công dân đã sẵn sàng trên frontend</small>
            </div>
            <h1>Chọn đúng nhóm, đúng nhánh ngay trong luồng chat.</h1>
            <p>
              Giao diện mới không ghim bộ chọn ở đầu trang. Thay vào đó, người dùng đi từ nhu cầu tự
              nhiên sang chọn nhóm Công dân và subdomain ngay trong cuộc hội thoại, rồi tiếp tục tới
              checklist và kiểm tra hồ sơ.
            </p>

            <div className="hero-actions">
              <a className="hero-primary" href="#assistant">
                Dùng trợ lý ngay
                <Icon name="arrow" />
              </a>
              <a className="hero-secondary" href="#explore">
                Xem 11 nhóm Công dân
              </a>
            </div>

            <div className="hero-metrics" aria-label="Tóm tắt rollout">
              {highlights.map((item) => (
                <article key={item.label}>
                  <strong>{item.value}</strong>
                  <span>{item.label}</span>
                  <p>{item.note}</p>
                </article>
              ))}
            </div>
          </div>

          <aside className="hero-rail" aria-label="Danh mục trọng tâm">
            <div className="hero-panel hero-panel-primary">
              <small>Đã đồng bộ từ workflow catalog</small>
              <div className="hero-procedure-list">
                {featuredGroups.map((item, index) => (
                  <article key={item.group_key}>
                    <span>{String(index + 1).padStart(2, "0")}</span>
                    <div>
                      <strong>{item.label}</strong>
                      <p>{item.description}</p>
                      <small>{item.subdomains.length} subdomain</small>
                    </div>
                  </article>
                ))}
              </div>
            </div>

            <div className="hero-panel hero-panel-soft">
              <div className="hero-panel-heading">
                <Icon name="shield" />
                <strong>Tại sao flow này đáng dùng</strong>
              </div>
              <ul>
                {trustSignals.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          </aside>
        </div>
      </section>

      <section className="notice-strip">
        <div className="page-width signal-strip">
          <div className="signal-intro">
            <small>Tin cập nhật</small>
            <strong>Thông tin mới nhất liên quan đến dịch vụ công trực tuyến</strong>
          </div>
          <div className="signal-list">
            {notices.map((item) => (
              <article key={item.title}>
                <span>{item.date}</span>
                <strong>{item.title}</strong>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="journey-band">
        <div className="page-width journey-layout">
          <article className="journey-card journey-card-accent">
            <small>Trải nghiệm mới cho 11 nhóm Công dân</small>
            <h2>Không cần nhớ cấu trúc thủ tục từ đầu</h2>
            <p>
              Người dùng chỉ cần nói nhu cầu, rồi chọn đúng nhóm và nhánh cụ thể khi assistant hỏi lại.
              Nhờ vậy việc route workflow diễn ra ngay trong chat thay vì bắt đầu bằng một form dài.
            </p>
          </article>

          <div className="journey-grid">
            {steps.map((item) => (
              <article className="journey-step" key={item.index}>
                <span>{item.index}</span>
                <strong>{item.title}</strong>
                <p>{item.text}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="service-directory page-width" id="explore">
        <div className="directory-heading">
          <div>
            <small>Khám phá nhu cầu</small>
            <h2>11 nhóm Công dân và {totalSubdomains} nhánh đã được nối vào frontend</h2>
          </div>
          <p>
            Danh mục bên dưới được lấy từ catalog workflow đã sinh. Người dùng có thể bắt đầu từ bất
            kỳ nhóm nào, sau đó dropdown trong chat sẽ tiếp tục làm rõ subdomain tương ứng.
          </p>
        </div>

        <div className="directory-grid">
          <section className="service-column citizen-column">
            <div className="service-column-title">Công dân</div>
            <div className="service-list">
              {citizenGroups.map((item, index) => (
                <a className="service-row" href="#assistant" key={item.group_key}>
                  <span className="service-icon tone-teal">{String(index + 1).padStart(2, "0")}</span>
                  <div className="service-row-copy">
                    <strong>{item.label}</strong>
                    <small>{item.subdomains.length} subdomain</small>
                  </div>
                </a>
              ))}
            </div>
          </section>

          <section className="service-column business-column">
            <div className="service-column-title">Doanh nghiệp</div>
            <div className="service-list">
              {businessGroups.map((item, index) => (
                <a className="service-row" href="#assistant" key={item}>
                  <span className="service-icon tone-red">{String(index + 1).padStart(2, "0")}</span>
                  <strong>{item}</strong>
                </a>
              ))}
            </div>
          </section>
        </div>
      </section>

      <section className="assistant-surface">
        <div className="page-width assistant-layout">
          <aside className="citizen-menu">
            <div className="menu-heading">
              <Icon name="user" />
              <div>
                <small>WORKFLOW CÔNG DÂN</small>
                <strong>{citizenGroups.length} nhóm</strong>
              </div>
            </div>
            {featuredGroups.map((item, index) => (
              <a className="featured" href="#assistant" key={item.group_key}>
                <span>{String(index + 1).padStart(2, "0")}</span>
                {item.label}
                <Icon name="arrow" />
              </a>
            ))}
            <div className="demo-scope-note">
              Bản frontend này đã chuyển từ chế độ pilot ít thủ tục sang chế độ chọn nhóm và nhánh
              trực tiếp trong chat, bám theo dữ liệu workflow đã sinh cho 11 nhóm Công dân.
            </div>
            <div className="source-mini">
              <Icon name="shield" />
              <p>
                Danh mục hiển thị và selector trong chat được đồng bộ từ catalog citizen workflow thay vì
                hardcode cục bộ trong giao diện.
              </p>
              <a href="https://dichvucong.gov.vn" target="_blank" rel="noreferrer">
                dichvucong.gov.vn <Icon name="external" />
              </a>
            </div>
          </aside>

          <div className="assistant-section" id="assistant">
            <div className="section-kicker">
              <span>Trợ lý dịch vụ công</span>
              <i />
            </div>
            <h2>Đi từ nhu cầu tự nhiên sang đúng workflow mà không rời khỏi cuộc chat</h2>
            <p className="section-lead">
              Khi cần, assistant sẽ hỏi lại bằng dropdown ngay dưới bubble chat mới nhất để người dùng
              chọn nhóm Công dân rồi chọn nhánh cụ thể. Sau khi khóa được context, hệ thống mới chuyển
              sang phần hướng dẫn chi tiết và kiểm tra hồ sơ.
            </p>
            <CitizenAssistant groups={citizenGroups} />
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

      <FloatingAssistant groups={citizenGroups} />
    </main>
  );
}
