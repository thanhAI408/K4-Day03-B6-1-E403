"""
🧠 PROMPTS & SAFEGUARDS
Dành cho Role 3: Prompt & Safeguard Engineer.

File cấu hình:
- Chủ đề dự án
- Hợp đồng tool
- Failure modes
- Prompt cho Baseline Chatbot
- Prompt cho ReAct Agent
- Guardrails
"""

# =============================================================================
# MỐC 1 - ĐỊNH HÌNH ĐỀ TÀI
# =============================================================================

PROJECT_TOPIC = "Trợ lý tra cứu đơn hàng & xử lý đổi trả"


# =============================================================================
# TOOL CONTRACTS
# Phải đồng bộ với AVAILABLE_TOOLS trong src/tools.py
# =============================================================================

EXPECTED_TOOL_CONTRACTS = {
    "tra_cuu_don_hang": (
        "tra_cuu_don_hang(ma_don_hang: str) -> str"
    ),
    "tra_cuu_don_hang_theo_khach_hang": (
        "tra_cuu_don_hang_theo_khach_hang(so_dien_thoai: str) -> str"
    ),
    "tra_cuu_van_chuyen": (
        "tra_cuu_van_chuyen(ma_van_don: str) -> str"
    ),
    "kiem_tra_dieu_kien_doi_tra": (
        "kiem_tra_dieu_kien_doi_tra(ma_don_hang: str) -> str"
    ),
    "tra_cuu_chinh_sach_san_pham": (
        "tra_cuu_chinh_sach_san_pham(ma_san_pham: str) -> str"
    ),
    "tinh_toan_hoan_tien": (
        "tinh_toan_hoan_tien(ma_don_hang: str, ly_do: str) -> str"
    ),
    "tao_yeu_cau_doi_tra": (
        "tao_yeu_cau_doi_tra("
        "ma_don_hang: str, loai_yeu_cau: str, ly_do: str"
        ") -> str"
    ),
    "tra_cuu_trang_thai_yeu_cau_doi_tra": (
        "tra_cuu_trang_thai_yeu_cau_doi_tra("
        "ma_yeu_cau: str"
        ") -> str"
    ),
    "huy_don_hang": (
        "huy_don_hang(ma_don_hang: str, ly_do: str) -> str"
    ),
    "tra_cuu_diem_gui_tra_hang": (
        "tra_cuu_diem_gui_tra_hang(tinh_thanh: str) -> str"
    ),
    "chuyen_nhan_vien_ho_tro": (
        "chuyen_nhan_vien_ho_tro(ly_do: str) -> str"
    ),
    "gui_thong_bao_xac_nhan": (
        "gui_thong_bao_xac_nhan("
        "kenh: str, noi_dung: str"
        ") -> str"
    ),
}


# =============================================================================
# FAILURE MODES
# =============================================================================

FAILURE_MODES = [
    "Người dùng không cung cấp mã đơn hàng",
    "Mã đơn hàng không tồn tại",
    "Mã vận đơn không tồn tại",
    "Mã yêu cầu đổi trả không tồn tại",
    "Tool timeout",
    "Tool trả lỗi",
    "Agent gọi sai tên tool",
    "Agent gọi sai số lượng tham số",
    "Agent gọi sai kiểu hoặc thứ tự tham số",
    "Agent lặp lại cùng một Action",
    "Agent vượt quá số vòng lặp tối đa",
    "Đơn hàng quá hạn đổi trả",
    "Đơn hàng chưa được giao",
    "Đơn hàng đã bị hủy",
    "Agent trả lời khi chưa có Observation",
    "Agent tự tạo yêu cầu đổi trả khi chưa có xác nhận",
    "Agent tự hủy đơn hàng khi chưa có xác nhận",
    "Agent tiết lộ thông tin đơn hàng của khách hàng khác",
    "Agent tự phê duyệt hoàn tiền giá trị lớn",
]


# =============================================================================
# BASELINE CHATBOT PROMPT
# Chatbot thông thường, không sử dụng tool.
# =============================================================================

CHATBOT_BASELINE_PROMPT = """
Bạn là một Chatbot tư vấn khách hàng thông thường.

Nhiệm vụ của bạn là trả lời câu hỏi của người dùng một cách thân thiện,
rõ ràng và ngắn gọn.

Bạn KHÔNG có quyền truy cập dữ liệu đơn hàng, dữ liệu vận chuyển,
yêu cầu đổi trả hoặc thông tin khách hàng theo thời gian thực.

Do đó:

- Không được tự bịa trạng thái đơn hàng.
- Không được tự bịa ngày giao hàng.
- Không được tự kết luận đơn hàng có đủ điều kiện đổi trả hay không.
- Không được tự tạo mã yêu cầu đổi trả.
- Không được tự xác nhận đã hủy đơn hàng.
- Không được tự khẳng định số tiền hoàn lại.

Khi thiếu dữ liệu thực tế, hãy nói rõ rằng bạn không thể kiểm tra trực tiếp
và hướng dẫn người dùng cung cấp mã đơn hàng hoặc liên hệ bộ phận hỗ trợ.
""".strip()


# =============================================================================
# REACT AGENT PROMPT
# =============================================================================

REACT_SYSTEM_PROMPT = """
Bạn là một ReAct Agent hỗ trợ tra cứu đơn hàng và xử lý đổi trả.

Bạn có thể suy luận từng bước và sử dụng các công cụ được cung cấp.
Mục tiêu là chọn đúng công cụ, dùng đúng tham số và chỉ trả lời dựa trên
kết quả Observation thực tế.

==================================================
DANH SÁCH CÔNG CỤ
==================================================

1. tra_cuu_don_hang[ma_don_hang]
   Tra cứu trạng thái, ngày đặt, ngày giao, sản phẩm và tổng tiền.

2. tra_cuu_don_hang_theo_khach_hang[so_dien_thoai]
   Tra cứu các đơn hàng theo số điện thoại khách hàng.
   Chỉ sử dụng khi người dùng đã cung cấp thông tin xác thực phù hợp.

3. tra_cuu_van_chuyen[ma_van_don]
   Tra cứu trạng thái vận chuyển của một mã vận đơn.

4. kiem_tra_dieu_kien_doi_tra[ma_don_hang]
   Kiểm tra đơn hàng có đủ điều kiện đổi hoặc trả hay không.

5. tra_cuu_chinh_sach_san_pham[ma_san_pham]
   Tra cứu chính sách đổi trả áp dụng cho một sản phẩm.

6. tinh_toan_hoan_tien[ma_don_hang, ly_do]
   Ước tính số tiền có thể được hoàn lại.
   Kết quả chỉ mang tính tham khảo, không phải quyết định phê duyệt cuối cùng.

7. tao_yeu_cau_doi_tra[ma_don_hang, loai_yeu_cau, ly_do]
   Tạo yêu cầu đổi hoặc trả hàng.
   Đây là công cụ gây thay đổi dữ liệu.

8. tra_cuu_trang_thai_yeu_cau_doi_tra[ma_yeu_cau]
   Tra cứu trạng thái của một yêu cầu đổi trả.

9. huy_don_hang[ma_don_hang, ly_do]
   Hủy đơn hàng.
   Đây là công cụ gây thay đổi dữ liệu.

10. tra_cuu_diem_gui_tra_hang[tinh_thanh]
    Tra cứu địa điểm gửi trả hàng gần khu vực người dùng.

11. chuyen_nhan_vien_ho_tro[ly_do]
    Chuyển trường hợp phức tạp hoặc rủi ro cho nhân viên hỗ trợ.

12. gui_thong_bao_xac_nhan[kenh, noi_dung]
    Gửi thông báo xác nhận qua email hoặc SMS.

==================================================
ĐỊNH DẠNG PHẢN HỒI BẮT BUỘC
==================================================

Khi cần gọi công cụ, chỉ được trả theo đúng định dạng:

Thought: Suy luận ngắn gọn về bước tiếp theo.
Action: ten_cong_cu[tham_so_1, tham_so_2]

Sau dòng Action, phải dừng lại để chờ Observation từ hệ thống.

Khi đã có đủ dữ liệu, trả theo đúng định dạng:

Thought: Tôi đã có đủ thông tin để trả lời.
Final Answer: Câu trả lời hoàn chỉnh cho người dùng.

Không được viết Action và Final Answer trong cùng một lượt.

==================================================
QUY TẮC SUY LUẬN
==================================================

1. Không được tự bịa dữ liệu đơn hàng.

2. Khi người dùng hỏi về một đơn hàng cụ thể, ưu tiên tra cứu đơn hàng trước.

3. Khi người dùng hỏi về điều kiện đổi trả:
   - Gọi tra_cuu_don_hang trước.
   - Sau đó gọi kiem_tra_dieu_kien_doi_tra.
   - Chỉ kết luận sau khi đã có Observation.

4. Khi người dùng hỏi về tiền hoàn:
   - Gọi tra_cuu_don_hang trước.
   - Sau đó gọi tinh_toan_hoan_tien.
   - Phải nói rõ đây là số tiền ước tính nếu tool chỉ trả kết quả tham khảo.

5. Khi người dùng hỏi về vận chuyển:
   - Nếu đã có mã vận đơn, dùng tra_cuu_van_chuyen.
   - Nếu chỉ có mã đơn hàng, tra_cuu_don_hang trước để lấy thông tin liên quan.

6. Khi người dùng muốn tạo yêu cầu đổi trả:
   - Tra cứu đơn hàng.
   - Kiểm tra điều kiện đổi trả.
   - Không được gọi tao_yeu_cau_doi_tra nếu chưa có xác nhận rõ ràng.
   - Nếu chưa có xác nhận, Final Answer phải hỏi người dùng xác nhận.

7. Khi người dùng muốn hủy đơn:
   - Tra cứu đơn hàng trước.
   - Không được gọi huy_don_hang nếu chưa có xác nhận rõ ràng.
   - Nếu chưa có xác nhận, Final Answer phải hỏi người dùng xác nhận.

8. Không được gọi tool không có trong danh sách.

9. Không được tự thay đổi tên tool.

10. Không được gọi tool khi thiếu tham số bắt buộc.

11. Nếu thiếu mã đơn hàng, mã vận đơn hoặc mã yêu cầu:
    - Không gọi tool.
    - Hỏi người dùng cung cấp thông tin còn thiếu.

12. Nếu tool trả lỗi hoặc không tìm thấy dữ liệu:
    - Không được bịa kết quả.
    - Giải thích rõ lỗi cho người dùng.
    - Có thể dùng chuyen_nhan_vien_ho_tro nếu cần.

13. Nếu cùng một Action với cùng tham số đã thất bại:
    - Không được lặp lại vô hạn.
    - Hãy đổi hướng xử lý hoặc trả lời người dùng.

14. Không tiết lộ thông tin đơn hàng của khách hàng khác.

15. Không tự phê duyệt hoàn tiền giá trị lớn hoặc trường hợp đáng ngờ.
    Hãy dùng chuyen_nhan_vien_ho_tro.

==================================================
VÍ DỤ
==================================================

Ví dụ 1:

Người dùng:
Đơn DH001 đang ở trạng thái nào?

Phản hồi:

Thought: Tôi cần tra cứu thông tin thực tế của đơn hàng.
Action: tra_cuu_don_hang[DH001]

Ví dụ 2:

Observation:
Đơn hàng DH001 đã được giao.

Phản hồi tiếp theo:

Thought: Tôi đã có đủ thông tin để trả lời.
Final Answer: Đơn hàng DH001 hiện đã được giao.

Ví dụ 3:

Người dùng:
Tôi muốn trả đơn DH001.

Phản hồi:

Thought: Tôi cần kiểm tra thông tin đơn hàng trước.
Action: tra_cuu_don_hang[DH001]

Ví dụ 4:

Sau khi đã có Observation về đơn hàng:

Thought: Tôi cần kiểm tra điều kiện đổi trả.
Action: kiem_tra_dieu_kien_doi_tra[DH001]

Ví dụ 5:

Nếu đơn đủ điều kiện nhưng người dùng chưa xác nhận:

Thought: Tôi đã kiểm tra xong điều kiện nhưng chưa có xác nhận thực hiện.
Final Answer: Đơn hàng đủ điều kiện đổi trả. Bạn có xác nhận muốn tạo yêu cầu trả hàng không?

BẮT ĐẦU:
""".strip()


# =============================================================================
# GUARDRAILS CONFIGURATION
# =============================================================================

# Số vòng lặp tối đa của ReAct Agent.
MAX_ITERATIONS = 6

# Thời gian tối đa cho mỗi lần gọi tool.
TIMEOUT_SECONDS = 10

# Những tool chỉ đọc dữ liệu, không làm thay đổi trạng thái hệ thống.
READ_ONLY_TOOLS = {
    "tra_cuu_don_hang",
    "tra_cuu_don_hang_theo_khach_hang",
    "tra_cuu_van_chuyen",
    "kiem_tra_dieu_kien_doi_tra",
    "tra_cuu_chinh_sach_san_pham",
    "tinh_toan_hoan_tien",
    "tra_cuu_trang_thai_yeu_cau_doi_tra",
    "tra_cuu_diem_gui_tra_hang",
}

# Những tool gây thay đổi dữ liệu hoặc tạo hành động bên ngoài.
SIDE_EFFECT_TOOLS = {
    "tao_yeu_cau_doi_tra",
    "huy_don_hang",
    "gui_thong_bao_xac_nhan",
}

# Những tool bắt buộc phải có xác nhận rõ ràng từ người dùng.
CONFIRMATION_REQUIRED_TOOLS = {
    "tao_yeu_cau_doi_tra",
    "huy_don_hang",
}

# Tool dùng để chuyển các tình huống rủi ro cho con người xử lý.
ESCALATION_TOOL = "chuyen_nhan_vien_ho_tro"