"""
🧠 PROMPTS & SAFEGUARDS (Dành cho Role 3: Prompt & Safeguard Engineer)
Nơi cấu hình System Prompt và Phanh An Toàn (Guardrails) cho AI.
"""
# =============================================================================
# MỐC 1 - ĐỊNH HÌNH ĐỀ TÀI
# =============================================================================

PROJECT_TOPIC = "Trợ lý tra cứu đơn hàng & xử lý đổi trả"

EXPECTED_TOOL_CONTRACTS = {
    "get_order_status": "get_order_status(order_id: str) -> str",
    "check_return_eligibility": "check_return_eligibility(order_id: str, reason: str) -> str",
    "create_return_request": "create_return_request(order_id: str, reason: str) -> str",
}

FAILURE_MODES = [
    "Không có mã đơn hàng",
    "Mã đơn không tồn tại",
    "Tool timeout",
    "Tool trả lỗi",
    "Agent gọi sai tên tool",
    "Agent gọi sai tham số",
    "Agent lặp Action",
    "Đơn hàng quá hạn đổi trả",
    "Đơn chưa giao",
    "Agent trả lời khi chưa có Observation",
]
# Baseline Chatbot Prompt (Chỉ dùng LLM thông thường, không có Tool)
CHATBOT_BASELINE_PROMPT = """Bạn là một Chatbot tư vấn thông thường.
Hãy trả lời câu hỏi của người dùng một cách thân thiện dựa trên kiến thức có sẵn của bạn.
Nếu không biết thông tin thực tế thời gian thực, hãy lịch sự thông báo cho người dùng.
"""

# ReAct Agent Prompt (Ép LLM suy luận theo chuỗi Thought -> Action)
REACT_SYSTEM_PROMPT = """Bạn là một ReAct Agent thông minh có khả năng sử dụng công cụ (Tools).

Danh sách các công cụ bạn có thể sử dụng:
1. get_weather[location]: Tra cứu thời tiết hiện tại của một thành phố.
2. search_flights[origin, destination]: Tra cứu chuyến bay giữa 2 địa điểm.

QUY TẮC BẮT BUỘC: Khi trả lời, bạn PHẢI tuân theo định dạng từng dòng như sau:

Thought: Suy luận của bạn về bước tiếp theo cần làm.
Action: tên_công_cụ[tham_số]
(Sau đó dừng lại chờ hệ thống trả về kết quả Observation)

Khi đã có đủ thông tin để trả lời người dùng, hãy dùng định dạng:
Thought: Tôi đã có đủ thông tin để trả lời.
Final Answer: Câu trả lời hoàn chỉnh cuối cùng gửi cho người dùng.

BẮT ĐẦU:
"""

# 🛡️ GUARDRAILS CONFIGURATION (PHANH AN TOÀN)
MAX_ITERATIONS = 3  # Giới hạn tối đa 3 vòng lặp Thought-Action để tránh lặp vô tận
TIMEOUT_SECONDS = 10  # Timeout cho mỗi lần gọi tool
