# GovEase AI Decision Tree

Tài liệu này mô tả cách GovEase AI dùng `workflow engine + decision tree` để dẫn người dùng đi từ nhu cầu đời thường đến đúng thủ tục hành chính.

Phạm vi hiện tại:

- Khai sinh
- Cư trú

## 1. Mục tiêu của decision tree

Decision tree không phải để thay AI trả lời thay tất cả.

Decision tree dùng để:

- giữ luồng hội thoại có kiểm soát
- tránh chọn sai thủ tục vì người dùng không hiểu thuật ngữ hành chính
- chia nhỏ vấn đề thành từng câu hỏi ngắn, dễ trả lời
- map kết quả cuối cùng về đúng `procedure_code`
- giúp backend debug được vì mỗi bước đều có state rõ ràng

LLM chỉ làm 2 việc:

- hiểu câu trả lời tự nhiên của người dùng
- diễn đạt lại câu hỏi sao cho dễ hiểu hơn

Backend mới là phần quyết định:

- đang ở node nào
- hỏi tiếp gì
- khi nào đủ dữ kiện để chốt route
- route nào map sang mã thủ tục nào

## 2. Nguyên tắc thiết kế

### 2.1. Không bắt người dân hiểu thuật ngữ pháp lý ngay từ đầu

Người dân thường không bắt đầu bằng:

- `Tôi muốn đăng ký thường trú`
- `Tôi muốn xác nhận điều kiện`
- `Tôi muốn khai báo thông tin cư trú khi chưa đủ điều kiện`

Họ thường nói theo nhu cầu thực tế:

- `Tôi mới sinh con`
- `Tôi muốn làm giấy khai sinh`
- `Tôi đang ở nhà thuê`
- `Tôi chuyển chỗ ở`
- `Tôi cần giấy xác nhận`

Vì vậy decision tree phải đi theo ngôn ngữ đời thường trước.

### 2.2. Nếu một bước có quá nhiều lựa chọn, phải chia nhỏ bằng câu hỏi `Có / Không`

Ví dụ:

- thay vì đưa ngay 6 lựa chọn về khai sinh ở bước đầu
- hệ thống hỏi:
  - `Bạn đang làm giấy khai sinh lần đầu cho trẻ phải không?`
  - nếu không, hỏi tiếp:
  - `Bạn đang xin bản sao hoặc trích lục giấy khai sinh phải không?`

Cách này:

- giảm overload nhận thức
- giúp người dân đỡ sợ
- phù hợp hơn với người lớn tuổi hoặc người không quen thuật ngữ

### 2.3. Chỉ đưa lựa chọn nhiều nhánh khi đã thu hẹp đủ

Khi user đã vào đúng cụm nhỏ, hệ thống mới nên hiện các option chi tiết hơn.

## 3. Kiến trúc logic

Luồng chuẩn:

1. Xác định domain
2. Dùng binary flow nếu bước đầu có quá nhiều lựa chọn
3. Chuyển sang decision tree chính
4. Thu thập slot
5. So khớp route
6. Chốt `procedure_code`

### 3.1. Các khái niệm chính

- `domain`: nhóm thủ tục lớn, ví dụ `birth_registration`, `residence_management`
- `node`: một câu hỏi đang hỏi user
- `slot`: một biến trạng thái cần thu thập, ví dụ `birth_location`
- `route`: tập điều kiện cuối cùng để map sang mã thủ tục
- `procedure_code`: mã thủ tục hành chính thật trong dữ liệu

## 4. Flow khai sinh

## 4.1. Mục tiêu

Phân biệt các nhóm:

- khai sinh mới
- đăng ký lại khai sinh
- xin bản sao hoặc trích lục
- ghi nhận việc khai sinh đã làm ở nước ngoài
- người đã có giấy tờ cá nhân nhưng chưa có khai sinh hợp lệ
- trường hợp lưu động

## 4.2. Binary flow mở đầu

Thay vì hiện một list dài, hệ thống hỏi tuần tự:

1. `Bạn đang làm giấy khai sinh lần đầu cho trẻ phải không?`
2. Nếu không: `Bạn đang xin bản sao hoặc trích lục giấy khai sinh phải không?`
3. Nếu không: `Bạn đang làm lại khai sinh vì đã mất hoặc thiếu bản chính hợp lệ?`
4. Nếu không: `Người cần làm thủ tục đã có giấy tờ cá nhân nhưng chưa có khai sinh hợp lệ?`
5. Nếu không: `Bạn đang ghi nhận vào sổ hộ tịch ở Việt Nam một việc khai sinh đã làm ở nước ngoài?`
6. Nếu không: `Đây có phải trường hợp làm theo diện lưu động không?`

Kết quả của tầng này là chốt `request_type`.

## 4.3. Các slot chính của khai sinh

- `request_type`
- `birth_location`
- `has_foreign_element`
- `combined_parent_recognition`
- `wants_linked_bundle`
- `service_channel`
- `request_type_detail`

## 4.4. Các câu hỏi chính sau khi vào đúng nhánh

Ví dụ với `khai sinh mới`:

1. `Người được đăng ký sinh trong nước hay ở nước ngoài?`
2. `Trường hợp này có yếu tố nước ngoài không?`
3. `Bạn có cần làm thủ tục nhận cha, mẹ, con cùng lúc với khai sinh không?`
4. `Bạn có muốn làm liên thông thêm bảo hiểm y tế hoặc đăng ký thường trú cho trẻ không?`
5. `Hồ sơ này theo diện thông thường, lưu động, khu vực biên giới hay cơ quan đại diện?`

## 4.5. Route khai sinh đang dùng

### Khai sinh mới

- `new_registration + domestic + no foreign element + no parent recognition + standard + no linked service`
  - `1.001193`
  - Thủ tục đăng ký khai sinh

- `new_registration + domestic + no foreign element + yes parent recognition`
  - `1.000689`
  - Đăng ký khai sinh kết hợp đăng ký nhận cha, mẹ, con

- `new_registration + domestic + yes foreign element + no parent recognition + standard`
  - `2.000528`
  - Đăng ký khai sinh có yếu tố nước ngoài

- `new_registration + domestic + yes foreign element + no parent recognition + border_area`
  - `1.000110`
  - Đăng ký khai sinh có yếu tố nước ngoài tại khu vực biên giới

- `new_registration + domestic + yes foreign element + yes parent recognition`
  - `1.001695`
  - Đăng ký khai sinh kết hợp nhận cha, mẹ, con có yếu tố nước ngoài

- `new_registration + abroad + consular`
  - `1.001020`
  - Đăng ký khai sinh cho trẻ em sinh ra ở nước ngoài và có quốc tịch Việt Nam

### Đăng ký lại

- `re_registration + no foreign element`
  - `1.004884`

- `re_registration + yes foreign element`
  - `2.000522`

### Người đã có hồ sơ cá nhân

- `existing_personal_documents + no foreign element`
  - `1.004772`

- `existing_personal_documents + yes foreign element`
  - `1.000893`

### Bản sao và trích lục

- `copy_extract`
  - `2.000635`

### Ghi nhận việc đã làm ở nước ngoài

- `foreign_record_note + birth_only`
  - `2.000712`

- `foreign_record_note + multi_civil_status`
  - `2.000547`

### Liên thông

- `new_registration + domestic + no foreign element + no parent recognition + linked BHYT only`
  - `2.001023`

- `new_registration + domestic + no foreign element + no parent recognition + linked BHYT + residence`
  - `2.000986`

### Lưu động

- `mobile_service`
  - `1.003583`

## 5. Flow cư trú

## 5.1. Mục tiêu

Phân biệt các nhóm:

- đăng ký ở mới
- gia hạn
- xóa đăng ký cũ
- tách hộ
- sửa dữ liệu
- khai báo tạm vắng
- thông báo lưu trú
- xin giấy xác nhận
- khai báo khi chưa đủ điều kiện

## 5.2. Vì sao phải chia nhỏ hơn

Nếu đưa thẳng những tên như:

- `xác nhận điều kiện`
- `khai báo thông tin cư trú khi chưa đủ điều kiện`
- `xác nhận thông tin cư trú`

thì đa số người dân sẽ không biết chọn gì.

Vì vậy flow cư trú nên bám theo câu chuyện đời thường:

- tôi mới chuyển chỗ ở
- tôi đang ở thuê
- tôi muốn xóa đăng ký cũ
- tôi cần giấy xác nhận
- thông tin cư trú của tôi đang sai

## 5.3. Binary flow mở đầu

Hệ thống hỏi lần lượt:

1. `Bạn đang muốn đăng ký nơi ở mới hoặc gia hạn nơi ở hiện tại phải không?`
2. Nếu có:
  - `Bạn muốn đăng ký ở ổn định lâu dài tại địa chỉ đó?`
  - nếu có: thường trú
  - nếu không: hỏi tiếp có phải gia hạn tạm trú không
3. Nếu không:
  - `Bạn đang muốn xóa một đăng ký cư trú cũ?`
4. Nếu không:
  - `Bạn muốn tách khỏi hộ hiện tại để thành hộ riêng?`
5. Nếu không:
  - `Bạn đang muốn sửa thông tin cư trú đang bị sai hoặc cần cập nhật?`
6. Nếu không:
  - `Bạn sắp vắng khỏi nơi ở hiện tại trong một thời gian và cần khai báo?`
7. Nếu không:
  - `Bạn cần báo có người đến ở ngắn hạn tại chỗ ở đó?`
8. Nếu không:
  - `Bạn đang cần một giấy xác nhận liên quan đến cư trú?`
9. Nếu vẫn không:
  - `Bạn chưa đủ điều kiện đăng ký cư trú chính thức nhưng vẫn muốn khai báo nơi ở hiện tại?`

## 5.4. Các slot chính của cư trú

- `residence_goal`
- `residence_place_type`
- `need_precondition_confirmation`
- `registration_status`

## 5.5. Route cư trú đang dùng

- `register_temporary`
  - `1.004194`
  - Đăng ký tạm trú

- `register_permanent + ready_for_main_registration`
  - `1.004222`
  - Đăng ký thường trú

- `extend_temporary`
  - `1.002755`
  - Gia hạn tạm trú

- `delete_temporary`
  - `1.010028`
  - Xóa đăng ký tạm trú

- `delete_permanent`
  - `1.003197`
  - Xóa đăng ký thường trú

- `split_household`
  - `1.010038`
  - Tách hộ

- `adjust_data`
  - `1.010039`
  - Điều chỉnh thông tin về cư trú trong cơ sở dữ liệu

- `absence_notice`
  - `1.003677`
  - Khai báo tạm vắng

- `lodging_notice`
  - `2.001159`
  - Thông báo lưu trú

- `residence_confirmation`
  - `1.010041`
  - Xác nhận thông tin về cư trú

- `eligibility_confirmation + rented_borrowed_stayed`
  - `1.013314`
  - Xác nhận điều kiện diện tích, tranh chấp, chỗ ở thuê/mượn/ở nhờ

- `eligibility_confirmation + vehicle_dwelling`
  - `1.013313`
  - Xác nhận nơi đậu, đỗ và việc dùng phương tiện để ở

- `fallback_info_declaration + not_eligible`
  - `1.010040`
  - Khai báo thông tin về cư trú đối với người chưa đủ điều kiện

## 6. Thứ tự ưu tiên khi hỏi

Một nguyên tắc quan trọng là:

- hỏi cái người dân hiểu dễ nhất trước
- hỏi cái giúp loại trừ nhiều nhánh nhất trước
- tránh hỏi thông tin pháp lý quá sớm

Ví dụ tốt:

- `Bạn đang làm lần đầu hay làm lại?`
- `Bạn ở lâu dài hay ở tạm?`
- `Bạn cần xóa đăng ký cũ hay đăng ký mới?`

Ví dụ chưa tốt nếu hỏi quá sớm:

- `Bạn có thuộc trường hợp xác nhận điều kiện hay xác nhận thông tin cư trú không?`

## 7. Khi nào dùng AI để giải thích

Không nên gọi AI để giải thích mọi lựa chọn ngay từ đầu.

Nên theo chiến lược 2 lớp:

### Lớp 1. Viết option theo ngôn ngữ dễ hiểu sẵn

Ví dụ:

- `Đăng ký ở ổn định lâu dài`
- `Đăng ký ở tạm`
- `Sửa thông tin cư trú`
- `Xin giấy xác nhận nơi ở`

### Lớp 2. Chỉ gọi AI khi user còn phân vân

Ví dụ:

- `Tôi không chắc`
- `Giải thích giúp tôi`
- `Khác nhau giữa hai lựa chọn này là gì?`

Khi đó AI có thể:

- diễn giải bằng tiếng Việt đời thường
- nêu ví dụ thực tế
- giải thích vì sao bot đang hỏi câu này

## 8. Rủi ro cần tránh

### 8.1. Một câu `Có / Không` bị map nhầm sang slot cũ

Đây là lỗi phổ biến nếu backend không khóa chặt `current_node`.

Cách xử lý:

- parser phải ưu tiên slot hiện tại
- quick reply nên gửi `value` kỹ thuật, không chỉ gửi text hiển thị

### 8.2. Nhiều text trên một button

Nếu dồn cả tên thủ tục và mô tả dài lên một dòng, UI sẽ rất rối.

Cách xử lý:

- tách `label`
- tách `description`
- nếu nhiều option, chuyển sang flow `Có / Không`

### 8.3. Hỏi lặp

Nếu backend không cập nhật state chuẩn, bot sẽ hỏi lặp câu cũ.

Cần kiểm tra:

- node hiện tại
- slot vừa được cập nhật
- route candidates sau mỗi lượt trả lời

## 9. Khuyến nghị tiếp theo

Để flow tốt hơn nữa, nên làm tiếp:

- nút `Quay lại`
- nút `Tôi không chắc`
- nút `Giải thích lựa chọn này`
- chia flow cư trú thành thêm các cụm đời thường thay vì giữ tên pháp lý
- thêm tài liệu `evidence` cho từng route để trace về raw-data

## 10. Kết luận

Decision tree tốt cho GovEase AI không phải là tree có nhiều nhánh nhất.

Decision tree tốt là tree:

- người dân thấy dễ trả lời
- backend dễ kiểm soát
- AI chỉ hỗ trợ hiểu ngôn ngữ tự nhiên
- kết quả cuối cùng map đúng sang thủ tục thật

Hiện tại hướng đúng là:

- bước đầu dùng `Có / Không` để gỡ rối
- bước giữa dùng câu hỏi ngắn, dễ hiểu
- bước cuối mới map sang thuật ngữ hành chính và `procedure_code`
