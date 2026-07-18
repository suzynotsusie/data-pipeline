# GovEase AI Personas And Assist Modes

Tài liệu này mô tả cách phân loại người dùng thật trong bối cảnh dịch vụ công và cách hệ thống nên phản ứng với từng nhóm.

## 1. Tư duy cốt lõi

Một chatbot dịch vụ công không nên giả định:

- mọi người dùng đều giống nhau
- ai cũng biết thuật ngữ hành chính
- ai cũng muốn đi từng bước như nhau
- ai cũng muốn tốc độ như nhau

GovEase AI nên hoạt động như một assistant có nhiều lối vào:

- người đã biết khá rõ thủ tục thì đi nhanh
- người biết lơ mơ thì được thu hẹp thông minh
- người không biết gì thì được dẫn dắt an toàn
- người lớn tuổi hoặc ít rành công nghệ thì được hỏi ngắn, dễ hiểu, ít lựa chọn cùng lúc

## 2. Persona chính

## 2.1. `knows_procedure`

Mô tả:

- đã tra cứu trước
- biết khá rõ thủ tục
- muốn tiết kiệm thời gian

Ví dụ câu đầu:

- `Tôi muốn đăng ký tạm trú`
- `Tôi muốn đăng ký lại khai sinh`
- `Cho tôi checklist hồ sơ đăng ký thường trú`

Nhu cầu:

- không bị hỏi lại điều đã biết
- chốt route nhanh
- đi thẳng vào checklist hoặc câu hỏi còn thiếu duy nhất

Rủi ro nếu thiết kế kém:

- họ thấy chatbot chậm, phiền, kém thông minh

Chế độ phù hợp:

- `fast_track`

## 2.2. `semi_clear`

Mô tả:

- biết đại khái tình huống của mình
- chưa chắc tên thủ tục
- có thể trả lời được nếu hỏi đúng cách

Ví dụ:

- `Tôi mới thuê nhà nên chắc cần đăng ký gì đó`
- `Tôi mới sinh con và muốn làm giấy tờ cho bé`
- `Tôi cần giấy xác nhận nơi ở nhưng không rõ tên`

Nhu cầu:

- bot hiểu ngữ cảnh đời thường
- không dùng quá nhiều thuật ngữ pháp lý quá sớm
- vẫn đi khá nhanh

Rủi ro:

- nếu bot hỏi cứng, họ sẽ thấy bị “hành chính hóa”
- nếu bot quá mở, họ sẽ không biết chọn gì

Chế độ phù hợp:

- `guided`

## 2.3. `first_time_unclear`

Mô tả:

- lần đầu làm thủ tục
- không biết tên thủ tục
- không biết bắt đầu từ đâu

Ví dụ:

- `Tôi cần làm gì bây giờ`
- `Tôi mới chuyển chỗ ở`
- `Tôi không biết mình phải chuẩn bị giấy tờ gì`

Nhu cầu:

- từng bước rõ ràng
- mỗi lần chỉ một câu hỏi
- nhiều ví dụ thực tế

Rủi ro:

- quá nhiều lựa chọn cùng lúc sẽ làm họ bỏ cuộc

Chế độ phù hợp:

- `guided`

## 2.4. `elderly_confused`

Mô tả:

- người lớn tuổi
- đọc chậm
- ít rành công nghệ hoặc không hiểu thuật ngữ pháp lý

Ví dụ:

- `Tôi lớn tuổi, bạn hướng dẫn chậm thôi`
- `Tôi không rành mấy từ này`
- `Giải thích dễ hiểu giúp tôi`

Nhu cầu:

- câu ngắn
- chữ dễ đọc
- ít lựa chọn
- ưu tiên câu hỏi `Có / Không`
- giải thích rất đời thường

Rủi ro:

- list dài
- button quá nhiều chữ
- bắt họ tự suy ra khác biệt giữa các thủ tục

Chế độ phù hợp:

- `guided`

## 2.5. `compliance_careful`

Mô tả:

- người dùng cẩn thận
- không cần nhanh nhất
- muốn đi chắc để tránh nộp sai

Ví dụ:

- `Bạn hỏi kỹ giúp tôi để tôi khỏi chọn nhầm`
- `Tôi muốn chắc chắn thủ tục đúng trước khi chuẩn bị hồ sơ`

Nhu cầu:

- bot giải thích vì sao đang hỏi
- xác nhận lại kết luận
- tóm tắt lý do chọn route

Chế độ phù hợp:

- `guided`

## 3. Assist mode

Hiện tại hệ thống dùng 2 mode chính:

## 3.1. `guided`

Khi dùng:

- user chưa chắc thủ tục
- user mô tả hoàn cảnh đời thường
- user muốn đi an toàn từng bước

Đặc điểm:

- có thể dùng binary flow `Có / Không`
- mỗi lần hỏi một ý ngắn
- ưu tiên câu hỏi đời thường
- tránh ném ra list dài ở bước đầu

## 3.2. `fast_track`

Khi dùng:

- user đã biết khá rõ thủ tục
- hoặc đã cung cấp nhiều slot có giá trị cao ngay từ đầu

Đặc điểm:

- bỏ qua lớp gỡ rối ban đầu
- nhảy thẳng tới node còn thiếu quan trọng nhất
- nếu đủ thông tin thì chốt route ngay

## 4. Cách phân loại trong lượt đầu

LLM hoặc heuristic đầu tiên cần suy ra:

- `domain_key`
- `user_mode`
- `persona_key`
- `assist_mode`
- `slot_updates`

Ví dụ:

```json
{
  "domain_key": "residence_management",
  "user_mode": "knows_procedure",
  "persona_key": "knows_procedure",
  "assist_mode": "fast_track",
  "slot_updates": {
    "residence_goal": "register_temporary"
  },
  "confidence": 0.93
}
```

## 5. Nguyên tắc chọn mode

### Chọn `fast_track` nếu

- user gọi đúng hoặc gần đúng tên thủ tục
- user yêu cầu đi nhanh
- user nói rõ hành động cần làm

Ví dụ:

- `Tôi muốn đăng ký tạm trú`
- `Tôi đã tra cứu rồi, cho tôi checklist`
- `Tôi cần đăng ký lại khai sinh`

### Chọn `guided` nếu

- user kể hoàn cảnh
- user tỏ ra không chắc
- user cần giải thích

Ví dụ:

- `Tôi mới sinh con`
- `Tôi đang ở thuê`
- `Tôi không rõ phải làm thủ tục nào`

## 6. Nâng cấp kỹ thuật đã bắt đầu trong project

Trong chatbot hiện tại, hệ thống đã bắt đầu lưu:

- `assist_mode`
- `user_mode`
- `persona_key`

UI cũng đã có:

- nút chọn `Dẫn từng bước`
- nút chọn `Đi nhanh`

Ý nghĩa:

- người dùng có quyền ép mode ngay từ đầu
- nếu không chọn, hệ thống sẽ tự suy đoán

## 7. Hướng nâng cấp tiếp theo

### 7.1. Cho người dùng chuyển mode giữa chừng

Ví dụ:

- đang guided nhưng muốn chuyển sang fast-track
- hoặc đang đi nhanh nhưng muốn bot giải thích kỹ hơn

### 7.2. Thêm chế độ `review`

Dành cho trường hợp:

- người dùng đã biết thủ tục
- đã điền gần xong
- muốn check hồ sơ trước khi nộp

### 7.3. Thêm nút `Tôi không chắc`

Khi đó bot sẽ:

- giải thích câu hỏi hiện tại
- cho ví dụ đời thường
- hoặc hỏi theo cách đơn giản hơn

## 8. Kết luận

Muốn chatbot dịch vụ công thật sự hữu ích, không thể chỉ có một flow cho tất cả mọi người.

Cách đúng là:

- phân loại người dùng
- chọn mode hỗ trợ phù hợp
- dùng LLM để hiểu mức độ rõ ràng của user
- dùng decision tree để giữ hệ thống chắc và đúng
