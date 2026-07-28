"""
🚀 CORE AGENT APP
Dành cho Role 4: Core Agent Developer / Integrator.

File chính ghép nối:
- Tools của Role 2
- Prompts và Guardrails của Role 3
- Test Cases của Role 1
- Multi-Provider LLM Adapter
- Vòng lặp ReAct: Thought -> Action -> Observation -> Final Answer
"""

import csv
import inspect
import json
import os
import re
import sys
from io import StringIO
from typing import Any, Optional

from dotenv import load_dotenv


# =============================================================================
# CẤU HÌNH IMPORT VÀ WINDOWS CONSOLE
# =============================================================================

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(CURRENT_DIR)

if CURRENT_DIR not in sys.path:
    sys.path.append(CURRENT_DIR)

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


from tools import AVAILABLE_TOOLS
from prompts import (
    CHATBOT_BASELINE_PROMPT,
    CONFIRMATION_REQUIRED_TOOLS,
    MAX_ITERATIONS,
    REACT_SYSTEM_PROMPT,
    SIDE_EFFECT_TOOLS,
)
from providers import get_llm_provider


load_dotenv()


# =============================================================================
# ĐỌC TEST CASE
# =============================================================================

def load_test_cases() -> list[dict[str, Any]]:
    """
    Đọc bộ test cases từ config/test_cases.json.
    """
    config_path = os.path.join(
        PROJECT_DIR,
        "config",
        "test_cases.json",
    )

    if not os.path.exists(config_path):
        config_path = os.path.join(
            os.getcwd(),
            "test_cases.json",
        )

    if not os.path.exists(config_path):
        raise FileNotFoundError(
            "Không tìm thấy file config/test_cases.json."
        )

    with open(config_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError(
            "test_cases.json phải chứa một danh sách test case."
        )

    return data


# =============================================================================
# CÁC HÀM TRÍCH XUẤT THÔNG TIN
# =============================================================================

def extract_order_id(text: str) -> Optional[str]:
    """
    Trích xuất mã đơn hàng dạng DH001.
    """
    match = re.search(
        r"\bDH\d+\b",
        text.upper(),
    )
    return match.group(0) if match else None


def extract_shipping_id(text: str) -> Optional[str]:
    """
    Trích xuất mã vận đơn dạng VD998877.
    """
    match = re.search(
        r"\bVD\d+\b",
        text.upper(),
    )
    return match.group(0) if match else None


def extract_return_request_id(text: str) -> Optional[str]:
    """
    Trích xuất mã yêu cầu đổi trả dạng RMA0001.
    """
    match = re.search(
        r"\bRMA\d+\b",
        text.upper(),
    )
    return match.group(0) if match else None


def extract_product_id(text: str) -> Optional[str]:
    """
    Trích xuất mã sản phẩm dạng SP-DT01 hoặc SP-TT02.
    """
    match = re.search(
        r"\bSP-[A-Z0-9]+\b",
        text.upper(),
    )
    return match.group(0) if match else None


def extract_phone_number(text: str) -> Optional[str]:
    """
    Trích xuất số điện thoại Việt Nam gồm 10 chữ số.
    """
    match = re.search(
        r"\b0\d{9}\b",
        text,
    )
    return match.group(0) if match else None


def extract_reason(text: str) -> str:
    """
    Tìm lý do đổi trả hoặc hoàn tiền trong câu hỏi.
    """
    text_lower = text.lower()

    known_reasons = [
        "lỗi nhà sản xuất",
        "sản phẩm bị lỗi",
        "hàng bị lỗi",
        "không đúng mô tả",
        "giao sai sản phẩm",
        "sản phẩm bị hỏng",
        "không còn nhu cầu",
        "đổi ý",
        "không vừa",
    ]

    for reason in known_reasons:
        if reason in text_lower:
            return reason

    return "người dùng yêu cầu hỗ trợ"


def extract_location(text: str) -> str:
    """
    Trích khu vực cơ bản dùng cho tool tìm điểm gửi trả hàng.
    """
    patterns = [
        r"(Hà Nội)",
        r"(TP\.?\s*HCM)",
        r"(Hồ Chí Minh)",
        r"(Đà Nẵng)",
        r"(Quận\s+\d+)",
        r"(Cầu Giấy)",
        r"(Thanh Xuân)",
        r"(Hai Bà Trưng)",
        r"(Hoàng Mai)",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )
        if match:
            return match.group(1)

    return "Hà Nội"


def user_has_confirmation(text: str) -> bool:
    """
    Kiểm tra người dùng đã xác nhận thực hiện hành động hay chưa.
    """
    normalized = text.lower().strip()

    confirmation_phrases = [
        "tôi xác nhận",
        "xác nhận thực hiện",
        "đồng ý thực hiện",
        "đồng ý tạo",
        "đồng ý hủy",
        "đồng ý huỷ",
        "chắc chắn hủy",
        "chắc chắn huỷ",
        "hãy tạo yêu cầu",
        "tạo luôn",
        "hủy luôn",
        "huỷ luôn",
        "yes, confirm",
    ]

    return any(
        phrase in normalized
        for phrase in confirmation_phrases
    )


# =============================================================================
# BASELINE CHATBOT
# =============================================================================

def run_baseline_chatbot(
    user_query: str,
    provider: Any,
) -> str:
    """
    Chạy Chatbot Baseline không có quyền sử dụng tool.
    """
    print(f"\n💬 [CHATBOT BASELINE] Câu hỏi: {user_query}")
    print(
        f"⚙️ System Prompt:\n"
        f"{CHATBOT_BASELINE_PROMPT.strip()}"
    )

    try:
        response = provider.generate(
            user_query,
            system_prompt=CHATBOT_BASELINE_PROMPT,
        )
    except Exception as error:
        response = (
            "Chatbot gặp lỗi khi gọi LLM Provider: "
            f"{error}"
        )

    print(f"🤖 Chatbot trả lời:\n{response}")
    return response


# =============================================================================
# PARSER ACTION
# =============================================================================

def parse_action(
    llm_output: str,
) -> tuple[Optional[str], list[str]]:
    """
    Phân tích output dạng:

    Action: tra_cuu_don_hang[DH001]

    hoặc:

    Action: tinh_toan_hoan_tien[
        DH001,
        sản phẩm bị lỗi
    ]

    Returns:
        (tool_name, tool_arguments)
    """
    match = re.search(
        r"Action\s*:\s*"
        r"([a-zA-Z_][a-zA-Z0-9_]*)"
        r"\s*\[(.*?)\]",
        llm_output,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if not match:
        return None, []

    tool_name = match.group(1).strip()
    raw_arguments = match.group(2).strip()

    if not raw_arguments:
        return tool_name, []

    try:
        reader = csv.reader(
            StringIO(raw_arguments),
            skipinitialspace=True,
            quotechar='"',
        )
        arguments = next(reader)
    except Exception:
        arguments = raw_arguments.split(",")

    cleaned_arguments = []

    for argument in arguments:
        cleaned = argument.strip()

        if (
            len(cleaned) >= 2
            and cleaned[0] == cleaned[-1]
            and cleaned[0] in {"'", '"'}
        ):
            cleaned = cleaned[1:-1]

        cleaned_arguments.append(cleaned.strip())

    return tool_name, cleaned_arguments


def extract_final_answer(
    llm_output: str,
) -> Optional[str]:
    """
    Trích nội dung sau Final Answer:.
    """
    match = re.search(
        r"Final Answer\s*:\s*(.+)",
        llm_output,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if not match:
        return None

    return match.group(1).strip()


# =============================================================================
# TOOL EXECUTION
# =============================================================================

def validate_tool_arguments(
    tool_name: str,
    arguments: list[str],
) -> Optional[str]:
    """
    Kiểm tra số lượng tham số trước khi gọi tool.
    """
    tool = AVAILABLE_TOOLS.get(tool_name)

    if tool is None:
        return (
            f"Tool '{tool_name}' không tồn tại trong "
            "AVAILABLE_TOOLS."
        )

    try:
        signature = inspect.signature(tool)

        required_parameters = [
            parameter
            for parameter in signature.parameters.values()
            if parameter.default is inspect.Parameter.empty
            and parameter.kind
            in {
                inspect.Parameter.POSITIONAL_ONLY,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
            }
        ]

        minimum_arguments = len(required_parameters)

        maximum_arguments = len(
            [
                parameter
                for parameter in signature.parameters.values()
                if parameter.kind
                in {
                    inspect.Parameter.POSITIONAL_ONLY,
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                }
            ]
        )

        if len(arguments) < minimum_arguments:
            return (
                f"Tool '{tool_name}' cần ít nhất "
                f"{minimum_arguments} tham số nhưng chỉ nhận được "
                f"{len(arguments)}."
            )

        if len(arguments) > maximum_arguments:
            return (
                f"Tool '{tool_name}' nhận tối đa "
                f"{maximum_arguments} tham số nhưng nhận được "
                f"{len(arguments)}."
            )

    except (TypeError, ValueError):
        return None

    return None


def call_tool(
    tool_name: str,
    arguments: list[str],
) -> str:
    """
    Gọi tool thông qua AVAILABLE_TOOLS.
    """
    if tool_name not in AVAILABLE_TOOLS:
        return (
            f"LỖI: Tool '{tool_name}' không được đăng ký."
        )

    validation_error = validate_tool_arguments(
        tool_name,
        arguments,
    )

    if validation_error:
        return f"LỖI: {validation_error}"

    try:
        result = AVAILABLE_TOOLS[tool_name](*arguments)
        return str(result)

    except TypeError as error:
        return (
            f"LỖI: Gọi sai tham số của tool "
            f"'{tool_name}': {error}"
        )

    except Exception as error:
        return (
            f"LỖI: Tool '{tool_name}' gặp sự cố: "
            f"{error}"
        )


# =============================================================================
# MOCK REACT PLANNER
# =============================================================================

def mock_react_response(
    user_query: str,
    scratchpad: str,
) -> str:
    """
    Bộ lập kế hoạch ReAct offline.

    Hàm này giúp LLM_PROVIDER=mock vẫn có thể:
    - Chọn tool theo câu hỏi
    - Đọc Observation
    - Chuyển sang bước tiếp theo
    - Tạo Final Answer

    Khi dùng Gemini/OpenAI/Anthropic/OpenRouter,
    agent sẽ sử dụng provider thật thay cho hàm này.
    """
    query = user_query.lower()
    order_id = extract_order_id(user_query)
    shipping_id = extract_shipping_id(user_query)
    request_id = extract_return_request_id(user_query)
    product_id = extract_product_id(user_query)
    phone_number = extract_phone_number(user_query)

    has_order_observation = (
        "Observation từ tra_cuu_don_hang:" in scratchpad
    )

    has_return_observation = (
        "Observation từ kiem_tra_dieu_kien_doi_tra:"
        in scratchpad
    )

    has_refund_observation = (
        "Observation từ tinh_toan_hoan_tien:"
        in scratchpad
    )

    has_shipping_observation = (
        "Observation từ tra_cuu_van_chuyen:"
        in scratchpad
    )

    has_policy_observation = (
        "Observation từ tra_cuu_chinh_sach_san_pham:"
        in scratchpad
    )

    has_request_status_observation = (
        "Observation từ "
        "tra_cuu_trang_thai_yeu_cau_doi_tra:"
        in scratchpad
    )

    has_customer_orders_observation = (
        "Observation từ "
        "tra_cuu_don_hang_theo_khach_hang:"
        in scratchpad
    )

    has_return_point_observation = (
        "Observation từ tra_cuu_diem_gui_tra_hang:"
        in scratchpad
    )

    has_create_observation = (
        "Observation từ tao_yeu_cau_doi_tra:"
        in scratchpad
    )

    has_cancel_observation = (
        "Observation từ huy_don_hang:"
        in scratchpad
    )

    last_observation = get_last_observation(scratchpad)

    # -------------------------------------------------------------------------
    # Tra cứu trạng thái yêu cầu đổi trả
    # -------------------------------------------------------------------------

    if (
        "rma" in query
        or "trạng thái yêu cầu" in query
        or "yêu cầu đổi trả" in query
    ) and request_id:

        if not has_request_status_observation:
            return (
                "Thought: Tôi cần tra cứu trạng thái "
                "yêu cầu đổi trả.\n"
                "Action: "
                "tra_cuu_trang_thai_yeu_cau_doi_tra"
                f"[{request_id}]"
            )

        return (
            "Thought: Tôi đã có đủ thông tin để trả lời.\n"
            f"Final Answer: {last_observation}"
        )

    # -------------------------------------------------------------------------
    # Tra cứu theo số điện thoại
    # -------------------------------------------------------------------------

    if phone_number and (
        "số điện thoại" in query
        or "đơn của tôi" in query
        or "đơn hàng của tôi" in query
    ):

        if not has_customer_orders_observation:
            return (
                "Thought: Tôi cần tra cứu các đơn hàng "
                "gắn với số điện thoại đã cung cấp.\n"
                "Action: "
                "tra_cuu_don_hang_theo_khach_hang"
                f"[{phone_number}]"
            )

        return (
            "Thought: Tôi đã có đủ thông tin để trả lời.\n"
            f"Final Answer: {last_observation}"
        )

    # -------------------------------------------------------------------------
    # Tra cứu điểm gửi trả hàng
    # -------------------------------------------------------------------------

    if (
        "điểm gửi" in query
        or "bưu cục" in query
        or "gửi trả ở đâu" in query
    ):
        location = extract_location(user_query)

        if not has_return_point_observation:
            return (
                "Thought: Tôi cần tìm điểm gửi trả hàng "
                "phù hợp với khu vực người dùng.\n"
                "Action: "
                f"tra_cuu_diem_gui_tra_hang[{location}]"
            )

        return (
            "Thought: Tôi đã có đủ thông tin để trả lời.\n"
            f"Final Answer: {last_observation}"
        )

    # -------------------------------------------------------------------------
    # Chính sách sản phẩm
    # -------------------------------------------------------------------------

    if (
        "chính sách" in query
        or "thời hạn đổi trả sản phẩm" in query
    ):

        if not product_id:
            return (
                "Thought: Người dùng chưa cung cấp mã sản phẩm.\n"
                "Final Answer: Vui lòng cung cấp mã sản phẩm, "
                "ví dụ SP-DT01 hoặc SP-TT02, để tôi tra cứu "
                "chính sách đổi trả."
            )

        if not has_policy_observation:
            return (
                "Thought: Tôi cần tra cứu chính sách "
                "đổi trả của sản phẩm.\n"
                "Action: "
                f"tra_cuu_chinh_sach_san_pham[{product_id}]"
            )

        return (
            "Thought: Tôi đã có đủ thông tin để trả lời.\n"
            f"Final Answer: {last_observation}"
        )

    # -------------------------------------------------------------------------
    # Tra cứu vận chuyển
    # -------------------------------------------------------------------------

    if (
        "vận chuyển" in query
        or "đang ở đâu" in query
        or "giao đến đâu" in query
        or "mã vận đơn" in query
    ):

        if shipping_id:
            if not has_shipping_observation:
                return (
                    "Thought: Người dùng đã cung cấp mã vận đơn, "
                    "tôi cần tra cứu trạng thái vận chuyển.\n"
                    "Action: "
                    f"tra_cuu_van_chuyen[{shipping_id}]"
                )

            return (
                "Thought: Tôi đã có đủ thông tin để trả lời.\n"
                f"Final Answer: {last_observation}"
            )

        if order_id:
            if not has_order_observation:
                return (
                    "Thought: Người dùng chỉ cung cấp mã đơn hàng, "
                    "tôi cần tra cứu đơn hàng trước.\n"
                    f"Action: tra_cuu_don_hang[{order_id}]"
                )

            return (
                "Thought: Kết quả tra cứu đơn hàng đã cung cấp "
                "trạng thái hiện tại.\n"
                f"Final Answer: {last_observation}"
            )

        return (
            "Thought: Người dùng chưa cung cấp mã đơn hoặc "
            "mã vận đơn.\n"
            "Final Answer: Vui lòng cung cấp mã đơn hàng dạng "
            "DH001 hoặc mã vận đơn dạng VD998877."
        )

    # -------------------------------------------------------------------------
    # Hủy đơn hàng
    # -------------------------------------------------------------------------

    if "hủy" in query or "huỷ" in query:
        if not order_id:
            return (
                "Thought: Người dùng chưa cung cấp mã đơn hàng.\n"
                "Final Answer: Vui lòng cung cấp mã đơn hàng "
                "cần hủy, ví dụ DH002."
            )

        if not has_order_observation:
            return (
                "Thought: Tôi cần kiểm tra trạng thái đơn hàng "
                "trước khi hủy.\n"
                f"Action: tra_cuu_don_hang[{order_id}]"
            )

        if not user_has_confirmation(user_query):
            return (
                "Thought: Hủy đơn là hành động làm thay đổi dữ liệu "
                "và chưa có xác nhận rõ ràng.\n"
                "Final Answer: Tôi đã kiểm tra đơn hàng. "
                f"Bạn có xác nhận muốn hủy đơn {order_id} không? "
                "Hãy trả lời theo mẫu: "
                f'“Tôi xác nhận hủy đơn {order_id}”.'
            )

        if not has_cancel_observation:
            return (
                "Thought: Người dùng đã xác nhận hủy đơn, "
                "tôi có thể thực hiện hành động.\n"
                f"Action: huy_don_hang[{order_id}]"
            )

        return (
            "Thought: Tôi đã có kết quả hủy đơn.\n"
            f"Final Answer: {last_observation}"
        )

    # -------------------------------------------------------------------------
    # Tạo yêu cầu đổi trả
    # -------------------------------------------------------------------------

    wants_create_return = (
        "tạo yêu cầu" in query
        or "trả đơn" in query
        or "trả hàng" in query
        or "đổi hàng" in query
    )

    if wants_create_return:
        if not order_id:
            return (
                "Thought: Người dùng chưa cung cấp mã đơn hàng.\n"
                "Final Answer: Vui lòng cung cấp mã đơn hàng "
                "cần đổi hoặc trả, ví dụ DH001."
            )

        if not has_order_observation:
            return (
                "Thought: Tôi cần tra cứu đơn hàng trước.\n"
                f"Action: tra_cuu_don_hang[{order_id}]"
            )

        if not has_return_observation:
            return (
                "Thought: Tôi cần kiểm tra điều kiện đổi trả "
                "trước khi tạo yêu cầu.\n"
                "Action: "
                f"kiem_tra_dieu_kien_doi_tra[{order_id}]"
            )

        if (
            "KHÔNG ĐỦ ĐIỀU KIỆN"
            in last_observation.upper()
        ):
            return (
                "Thought: Đơn hàng không đủ điều kiện đổi trả, "
                "tôi không được tạo yêu cầu.\n"
                f"Final Answer: {last_observation}"
            )

        if not user_has_confirmation(user_query):
            return (
                "Thought: Đơn hàng đủ điều kiện nhưng đây là "
                "hành động làm thay đổi dữ liệu và chưa có "
                "xác nhận rõ ràng.\n"
                "Final Answer: Đơn hàng đủ điều kiện đổi trả. "
                f"Bạn có xác nhận muốn tạo yêu cầu cho {order_id} "
                "không? Hãy trả lời theo mẫu: "
                f'“Tôi xác nhận tạo yêu cầu trả đơn {order_id}”.'
            )

        if not has_create_observation:
            request_type = (
                "đổi hàng"
                if "đổi hàng" in query
                else "trả hàng hoàn tiền"
            )
            reason = extract_reason(user_query)

            return (
                "Thought: Người dùng đã xác nhận và đơn hàng "
                "đủ điều kiện, tôi có thể tạo yêu cầu.\n"
                "Action: "
                f"tao_yeu_cau_doi_tra["
                f"{order_id}, {request_type}, {reason}]"
            )

        return (
            "Thought: Tôi đã có kết quả tạo yêu cầu.\n"
            f"Final Answer: {last_observation}"
        )

    # -------------------------------------------------------------------------
    # Tính hoàn tiền
    # -------------------------------------------------------------------------

    if (
        "hoàn tiền" in query
        or "hoàn lại bao nhiêu" in query
        or "tiền hoàn" in query
    ):
        if not order_id:
            return (
                "Thought: Người dùng chưa cung cấp mã đơn hàng.\n"
                "Final Answer: Vui lòng cung cấp mã đơn hàng "
                "để tôi ước tính số tiền hoàn lại."
            )

        if not has_order_observation:
            return (
                "Thought: Tôi cần tra cứu đơn hàng trước "
                "khi tính hoàn tiền.\n"
                f"Action: tra_cuu_don_hang[{order_id}]"
            )

        if not has_refund_observation:
            reason = extract_reason(user_query)

            return (
                "Thought: Tôi đã có thông tin đơn hàng và cần "
                "ước tính tiền hoàn theo lý do.\n"
                "Action: "
                f"tinh_toan_hoan_tien[{order_id}, {reason}]"
            )

        return (
            "Thought: Tôi đã có kết quả ước tính hoàn tiền.\n"
            "Final Answer: "
            f"{last_observation} Đây là mức hoàn tiền ước tính, "
            "chưa phải quyết định phê duyệt cuối cùng."
        )

    # -------------------------------------------------------------------------
    # Kiểm tra điều kiện đổi trả
    # -------------------------------------------------------------------------

    if (
        "đủ điều kiện" in query
        or "có được đổi trả" in query
        or "có được trả" in query
        or "hạn đổi trả" in query
    ):
        if not order_id:
            return (
                "Thought: Người dùng chưa cung cấp mã đơn hàng.\n"
                "Final Answer: Vui lòng cung cấp mã đơn hàng "
                "cần kiểm tra, ví dụ DH001."
            )

        if not has_order_observation:
            return (
                "Thought: Tôi cần tra cứu đơn hàng trước.\n"
                f"Action: tra_cuu_don_hang[{order_id}]"
            )

        if not has_return_observation:
            return (
                "Thought: Tôi cần kiểm tra điều kiện đổi trả.\n"
                "Action: "
                f"kiem_tra_dieu_kien_doi_tra[{order_id}]"
            )

        return (
            "Thought: Tôi đã có đủ thông tin để trả lời.\n"
            f"Final Answer: {last_observation}"
        )

    # -------------------------------------------------------------------------
    # Tra cứu đơn hàng thông thường
    # -------------------------------------------------------------------------

    if order_id:
        if not has_order_observation:
            return (
                "Thought: Tôi cần tra cứu thông tin đơn hàng.\n"
                f"Action: tra_cuu_don_hang[{order_id}]"
            )

        return (
            "Thought: Tôi đã có đủ thông tin để trả lời.\n"
            f"Final Answer: {last_observation}"
        )

    # -------------------------------------------------------------------------
    # Không xác định được yêu cầu
    # -------------------------------------------------------------------------

    return (
        "Thought: Tôi chưa có đủ thông tin để chọn công cụ.\n"
        "Final Answer: Vui lòng cung cấp mã đơn hàng và mô tả "
        "rõ nhu cầu, ví dụ tra cứu trạng thái, kiểm tra đổi trả, "
        "tính hoàn tiền hoặc hủy đơn."
    )


def get_last_observation(scratchpad: str) -> str:
    """
    Lấy Observation gần nhất từ scratchpad.
    """
    matches = re.findall(
        r"Observation từ [^:]+:\n"
        r"(.*?)(?=\n\nThought:|\Z)",
        scratchpad,
        flags=re.DOTALL,
    )

    if not matches:
        return "Chưa có dữ liệu Observation."

    return matches[-1].strip()


# =============================================================================
# GỌI LLM CHO REACT
# =============================================================================

def generate_react_step(
    provider: Any,
    user_query: str,
    scratchpad: str,
) -> str:
    """
    Sinh một bước ReAct.

    MockProvider:
        dùng bộ mock planner offline.

    Provider thật:
        gửi câu hỏi và scratchpad cho LLM.
    """
    provider_name = provider.__class__.__name__

    if provider_name == "MockProvider":
        return mock_react_response(
            user_query,
            scratchpad,
        )

    react_prompt = (
        f"Câu hỏi ban đầu của người dùng:\n"
        f"{user_query}\n\n"
        f"Lịch sử Thought, Action và Observation:\n"
        f"{scratchpad if scratchpad else 'Chưa có bước nào.'}\n\n"
        "Hãy sinh đúng một bước tiếp theo theo định dạng "
        "trong System Prompt."
    )

    try:
        return provider.generate(
            react_prompt,
            system_prompt=REACT_SYSTEM_PROMPT,
        )
    except Exception as error:
        return (
            "Thought: LLM Provider gặp lỗi.\n"
            f"Final Answer: Không thể tiếp tục xử lý do lỗi: {error}"
        )


# =============================================================================
# GUARDRAILS
# =============================================================================

def check_action_guardrails(
    tool_name: str,
    arguments: list[str],
    user_query: str,
    executed_actions: set[tuple[str, tuple[str, ...]]],
) -> Optional[str]:
    """
    Kiểm tra Action trước khi gọi tool.
    """
    if tool_name not in AVAILABLE_TOOLS:
        return (
            f"Tool '{tool_name}' không nằm trong "
            "AVAILABLE_TOOLS."
        )

    action_key = (
        tool_name,
        tuple(arguments),
    )

    if action_key in executed_actions:
        return (
            "Agent đã lặp lại cùng một Action với "
            "cùng tham số."
        )

    if (
        tool_name in CONFIRMATION_REQUIRED_TOOLS
        and not user_has_confirmation(user_query)
    ):
        return (
            f"Tool '{tool_name}' yêu cầu xác nhận rõ ràng "
            "từ người dùng."
        )

    return None


# =============================================================================
# REACT AGENT LOOP
# =============================================================================

def run_react_agent(
    user_query: str,
    provider: Any,
) -> str:
    """
    Chạy vòng lặp ReAct động:

    User Query
        -> LLM sinh Thought + Action
        -> Parser tách tool và tham số
        -> Guardrail kiểm tra
        -> Tool thực thi
        -> Observation
        -> LLM đọc Observation
        -> Final Answer
    """
    print(f"\n🤖 [REACT AGENT] Câu hỏi: {user_query}")

    scratchpad = ""
    executed_actions: set[
        tuple[str, tuple[str, ...]]
    ] = set()

    for step in range(1, MAX_ITERATIONS + 1):
        print(
            f"\n--- 🔄 Vòng lặp ReAct "
            f"(Step {step}/{MAX_ITERATIONS}) ---"
        )

        llm_output = generate_react_step(
            provider,
            user_query,
            scratchpad,
        )

        print(llm_output)

        final_answer = extract_final_answer(llm_output)

        if final_answer is not None:
            return final_answer

        tool_name, arguments = parse_action(llm_output)

        if not tool_name:
            final_answer = (
                "Agent không sinh đúng định dạng Action hoặc "
                "Final Answer."
            )
            print(
                f"🛡️ GUARDRAIL TRIGGERED: "
                f"{final_answer}"
            )
            return final_answer

        guardrail_error = check_action_guardrails(
            tool_name,
            arguments,
            user_query,
            executed_actions,
        )

        if guardrail_error:
            final_answer = (
                "Không thể thực hiện Action vì "
                f"{guardrail_error}"
            )
            print(
                f"🛡️ GUARDRAIL TRIGGERED: "
                f"{final_answer}"
            )
            return final_answer

        action_key = (
            tool_name,
            tuple(arguments),
        )
        executed_actions.add(action_key)

        observation = call_tool(
            tool_name,
            arguments,
        )

        print(
            f"👁️ Observation từ {tool_name}:\n"
            f"{observation}"
        )

        scratchpad += (
            f"\n\n{llm_output.strip()}\n"
            f"Observation từ {tool_name}:\n"
            f"{observation}"
        )

        if observation.startswith("LỖI:"):
            scratchpad += (
                "\nTool vừa gặp lỗi. Không được bịa dữ liệu "
                "và không được lặp lại cùng Action."
            )

    final_answer = (
        f"Agent đã đạt giới hạn tối đa "
        f"{MAX_ITERATIONS} bước nhưng chưa hoàn thành yêu cầu."
    )

    print(
        f"\n🛡️ GUARDRAIL TRIGGERED: "
        f"{final_answer}"
    )

    return final_answer


# =============================================================================
# CHỌN TEST CASE PHÙ HỢP
# =============================================================================

import random

def choose_sample_query(
    tests: list[dict[str, Any]],
) -> str:
    """
    Chọn ngẫu nhiên 1 test case từ bộ test_cases.json mỗi lần chạy.
    """
    valid_candidates = []
    for test_case in tests:
        question = test_case.get("question", "")

        if isinstance(question, str) and question.strip():
            valid_candidates.append(question)

    if valid_candidates:
        return random.choice(valid_candidates)

    return (
        "Kiểm tra giúp tôi đơn hàng DH001 "
        "có được đổi trả không?"
    )


# =============================================================================
# MAIN
# =============================================================================

def main() -> None:
    """
    Hàm khởi chạy chương trình.
    """
    print("=" * 62)
    print(
        "🏫 ĐẠI HỌC VINUNI - "
        "BÀI LAB 3: CHATBOT VS REACT AGENT"
    )
    print("=" * 62)

    try:
        provider = get_llm_provider()
    except Exception as error:
        print(
            f"❌ Không thể khởi tạo LLM Provider: "
            f"{error}"
        )
        return

    model_name = getattr(
        provider,
        "model_name",
        "Offline Mock Mode",
    )

    print(
        f"🔌 LLM Provider đang hoạt động: "
        f"{provider.__class__.__name__} "
        f"(Model: {model_name})"
    )

    try:
        tests = load_test_cases()
    except (
        FileNotFoundError,
        ValueError,
        json.JSONDecodeError,
    ) as error:
        print(
            f"❌ Không thể tải test cases: "
            f"{error}"
        )
        return

    print(
        f"✅ Đã tải thành công {len(tests)} Test Cases "
        "từ config/test_cases.json\n"
    )

    sample_query = choose_sample_query(tests)

    print(f"🧪 Test được chọn: {sample_query}\n")

    print(
        "--- DEMO 1: "
        "CHẠY TRÊN CHATBOT BASELINE ---"
    )
    run_baseline_chatbot(
        sample_query,
        provider,
    )

    print(
        "\n--- DEMO 2: "
        "CHẠY TRÊN REACT AGENT ---"
    )
    run_react_agent(
        sample_query,
        provider,
    )


if __name__ == "__main__":
    main()