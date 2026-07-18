import Link from "next/link";

export default function DemoNotice() {
  return <main className="demo-notice-page"><section><span>GOV EASE AI · BẢN DEMO</span><h1>Tính năng cổng dịch vụ công đang được mô phỏng</h1><p>Hackathon pilot hiện chỉ triển khai trọn vẹn hai thủ tục: đăng ký khai sinh và đăng ký tạm trú. Các mục điều hướng khác được giữ để mô phỏng bối cảnh tích hợp và không phải dịch vụ công thật.</p><Link href="/#assistant">Quay lại trải nghiệm trợ lý</Link></section></main>;
}
