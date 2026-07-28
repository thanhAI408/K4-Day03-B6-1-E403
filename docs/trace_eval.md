# 📊 BÁO CÁO GIÁM SÁT & ĐÁNH GIÁ (OBSERVABILITY TRACE LOGS)
*Dành cho Role 5: Observability & Reviewer*

---

## 📌 CHỦ ĐỀ BÀI TOÁN (Role 1 & Cả nhóm thống nhất)
> **Đề tài được chọn**: **Đề tài 5 - Trợ Lý Tra Cứu Đơn Hàng & Xử Lý Đổi Trả (Order Tracking & Returns Assistant)**
> **Thành viên đảm nhận (Role 1 & Role 5)**: Pham Quoc Bao

---

## 🎯 1. BẢNG CHẤM ĐIỂM AGENTIC FIT (SCORING MATRIX - MỐC 1)

| Tiêu chí | Điểm (1-5) | Lý do đánh giá chi tiết |
| :--- | :---: | :--- |
| 🧠 **Multi-step Reasoning** | `4/5` | Cần suy luận qua chuỗi bước: Tra cứu trạng thái đơn hàng -> Kiểm tra điều kiện chính sách đổi trả -> Gọi API xử lý đổi trả/hoàn tiền. |
| 🛠️ **Tool Interaction** | `5/5` | Bắt buộc gọi các công cụ hệ thống (`tra_cuu_don_hang`, `kiem_tra_dieu_kien_doi_tra`, `tao_yeu_cau_doi_tra`) để lấy dữ liệu thực tế từ cơ sở dữ liệu kho/đơn hàng. |
| 🔀 **Dynamic Decision** | `4/5` | Quyết định bước tiếp theo phụ thuộc vào trạng thái đơn hàng (Đã giao/Đang giao) và lý do đổi trả của khách hàng. |
| ⏳ **Long Horizon** | `3/5` | Quy trình gồm 2 - 4 bước ReAct liên tiếp cho từng yêu cầu. |
| **TỔNG ĐIỂM FIT** | **16/20** | **KẾT LUẬN: BÀI TOÁN RẤT NÊN DÙNG REACT AGENT!** (Vượt ngưỡng 12/20) |

---

## 🤖 2. QUAN SÁT CHATBOT BASELINE (MỐC 2)

*Mục tiêu: Ghi lại phản hồi của Chatbot gốc (không có Tool) để thấy rõ hạn chế so với ReAct Agent.*

### 📋 Test Case #6 — Multi-step (Cần 1 Tool)
**Câu hỏi**: *"Đơn hàng DH001 của tôi đang ở đâu rồi?"*

**🤖 Chatbot Baseline phản hồi**:
> *"Xin chào! Rất tiếc, tôi không có quyền truy cập vào hệ thống quản lý đơn hàng để tra cứu trạng thái đơn hàng cụ thể của bạn. Bạn vui lòng kiểm tra trên ứng dụng của chúng tôi hoặc liên hệ hotline để được hỗ trợ tra cứu đơn hàng DH001."*

**Nhận xét**: Câu trả lời an toàn, không bịa đặt, nhưng **không giải quyết được nhu cầu thực tế** vì thiếu công cụ tra cứu. Khách hàng phải tự tìm kênh khác.

---

### 📋 Test Case #9 — Multi-step (Cần gọi 2 Tools)
**Câu hỏi**: *"Đơn hàng DH002 của tôi đã giao chưa? Nếu giao rồi thì tôi muốn đổi trả vì hàng bị lỗi, tôi có đủ điều kiện không?"*

**🤖 Chatbot Baseline phản hồi**:
> *"Bạn ơi, tôi không thể tra cứu trạng thái đơn hàng DH002 vì tôi không có quyền truy cập hệ thống. Tuy nhiên, về chính sách đổi trả, nếu hàng bị lỗi do nhà sản xuất, bạn có thể đổi trả trong vòng 7 ngày (hàng điện tử) hoặc 30 ngày (hàng thời trang) kể từ ngày nhận hàng. Hãy liên hệ hotline để được hỗ trợ kiểm tra đơn hàng và mở yêu cầu đổi trả."*

**Nhận xét**: Chatbot **bịa đặt chính sách chung** mà không biết đơn hàng cụ thể đang ở trạng thái nào. Không thể xác nhận đủ/không đủ điều kiện đổi trả mà không có dữ liệu thực.

---

### 📋 Test Case #13 — Edge Case (Bẫy Guardrail)
**Câu hỏi**: *"Kiểm tra và xử lý đổi trả cho đơn hàng ORD-9999-XYZ, đơn này tôi mua cách đây 2 năm."*

**🤖 Chatbot Baseline phản hồi**:
> *"Xin chào! Với đơn hàng mua cách đây 2 năm, rất tiếc đơn hàng này đã vượt quá thời hạn đổi trả theo chính sách của chúng tôi (tối đa 30 ngày). Tuy nhiên, sản phẩm vẫn có thể được hỗ trợ qua chính sách bảo hành. Vui lòng liên hệ hotline để được tư vấn."*

**Nhận xét**: Chatbot **suy đoán đúng** về quá hạn nhưng không xác minh được mã đơn hàng có tồn tại không. Trả lời an toàn nhưng thiếu chính xác.

---

### 📊 Tổng kết quan sát Mốc 2

| Tiêu chí quan sát | Kết quả |
| :--- | :--- |
| Chatbot có tra cứu được đơn hàng thực tế không? | ❌ Không — không có Tool |
| Chatbot có xác nhận được điều kiện đổi trả không? | ❌ Không — chỉ tư vấn chung chung |
| Chatbot có tạo được yêu cầu đổi trả không? | ❌ Không — không có Tool |
| Chatbot có bịa đặt thông tin không? | ⚠️ Có một phần — tư vấn chính sách mà không biết sản phẩm cụ thể |
| Kết luận | **ReAct Agent VƯỢT TRỘI** — cần Tool để phục vụ khách hàng thực sự |

---

## 🧠 3. NHẬT KÝ VÒNG LẶP REACT AGENT (TRACE LOG THỰC TẾ)

**Câu hỏi thực thi**: *"Đơn hàng DH001 của tôi đang ở đâu rồi?"*

### 🔄 Chi tiết luồng Thought -> Action -> Observation:

- 🔄 **Step 1/6**:
  - 🧠 **Thought 1**: Khách hỏi về đơn hàng DH001. Tôi cần tra cứu trạng thái đơn hàng này.
  - 🛠️ **Action 1**: `tra_cuu_don_hang['DH001']`
  - 👁️ **Observation 1**: 
    ```text
    Đơn hàng DH001:
    Trạng thái: Đã giao
    Ngày đặt: 2026-07-15 | Ngày giao: 2026-07-18
    Sản phẩm:
      - Tai nghe Bluetooth X1 (x1) - 590,000 VNĐ
    Tổng tiền: 590,000 VNĐ
    ```

- 🔄 **Step 2/6**:
  - 🧠 **Thought 2**: Đơn đã giao. Khách muốn đổi trả, tôi cần kiểm tra điều kiện đổi trả.
  - 🛠️ **Action 2**: `kiem_tra_dieu_kien_doi_tra['DH001']`
  - 👁️ **Observation 2**: 
    ```text
    KHÔNG ĐỦ ĐIỀU KIỆN: Đã quá hạn đổi trả (hết hạn 2026-07-25).
    ```

- 🔄 **Step 3/6**:
  - 🧠 **Thought 3**: Đã có đủ thông tin. Tổng hợp câu trả lời cho khách.
  - 🏁 **Final Answer**: *"Đơn hàng DH001 của bạn đã giao thành công. Tôi đã kiểm tra điều kiện đổi trả — vui lòng xem kết quả phía trên để biết chi tiết."*

