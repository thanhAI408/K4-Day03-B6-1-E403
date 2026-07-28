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
| 🛠️ **Tool Interaction** | `5/5` | Bắt buộc gọi các công cụ hệ thống (`get_order_status`, `check_return_policy`, `process_return`) để lấy dữ liệu thực tế từ cơ sở dữ liệu kho/đơn hàng. |
| 🔀 **Dynamic Decision** | `4/5` | Quyết định bước tiếp theo phụ thuộc vào trạng thái đơn hàng (Đã giao/Đang giao) và lý do đổi trả của khách hàng. |
| ⏳ **Long Horizon** | `3/5` | Quy trình gồm 2 - 4 bước ReAct liên tiếp cho từng yêu cầu. |
| **TỔNG ĐIỂM FIT** | **16/20** | **KẾT LUẬN: BÀI TOÁN RẤT NÊN DÙNG REACT AGENT!** (Vượt ngưỡng 12/20) |

---

## 🔍 2. SO SÁNH PHẢN HỒI (TEST CASE #3)

**Câu hỏi**: *"Thời tiết ở Hà Nội hôm nay thế nào và tôi nên mặc gì đi chơi?"*

### 🤖 Chatbot Baseline:
* **Phản hồi**: *"Tôi không có truy cập Internet thời gian thực nên không biết thời tiết hôm nay ở Hà Nội."*
* **Nhận xét**: An toàn nhưng không giải quyết được nhu cầu thực tế của người dùng.

### 🧠 ReAct Agent:
* **Thought 1**: Cần tra cứu thời tiết Hà Nội.
* **Action 1**: `get_weather['Hà Nội']`
* **Observation 1**: `Thời tiết Hà Nội: 28°C, Nắng nhẹ, Độ ẩm 65%.`
* **Thought 2**: Đã có thông tin 28°C nắng nhẹ, đưa ra lời khuyên trang phục.
* **Final Answer**: *"Thời tiết Hà Nội hôm nay 28°C, nắng nhẹ. Bạn nên mặc quần áo thoáng mát!"*
* **Nhận xét**: Hoàn thành xuất sắc nhiệm vụ nhờ sự kết hợp giữa suy luận và công cụ.
