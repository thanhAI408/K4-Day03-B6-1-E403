"""
🚀 CORE AGENT APP (Dành cho Role 4: Core Agent Developer)
File chính ghép nối tất cả các thành phần:
Tools + Prompts + Test Cases + Multi-Provider.
"""

import json
import os
import re
import sys
from typing import Any

from dotenv import load_dotenv

# Đảm bảo import các module cùng thư mục src/ hoạt động trên Windows
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.append(CURRENT_DIR)

# Đảm bảo in tiếng Việt và emoji không lỗi trên Windows Console
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Import các thành phần từ Role 2, Role 3 và Multi-Provider Adapter
from tools import AVAILABLE_TOOLS
from prompts import CHATBOT_BASELINE_PROMPT, REACT_SYSTEM_PROMPT, MAX_ITERATIONS
from providers import get_llm_provider

load_dotenv()


def load_test_cases() -> list[dict[str, Any]]:
    """
    Đọc bộ test cases từ config/test_cases.json của Role 1.
    """
    base_dir = os.path.dirname(CURRENT_DIR)
    config_path = os.path.join(base_dir, "config", "test_cases.json")

    if not os.path.exists(config_path):
        config_path = "test_cases.json"

    if not os.path.exists(config_path):
        raise FileNotFoundError(
            "Không tìm thấy file config/test_cases.json."
        )

    with open(config_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError(
            "Nội dung test_cases.json phải là một danh sách test case."
        )

    return data


def run_baseline_chatbot(user_query: str, provider: Any) -> str:
    """
    Chạy Chatbot Baseline không được phép sử dụng tool.

    Args:
        user_query: Câu hỏi của người dùng.
        provider: LLM provider đang được cấu hình.

    Returns:
        Câu trả lời của chatbot baseline.
    """
    print(f"\n💬 [CHATBOT BASELINE] Câu hỏi: {user_query}")
    print(f"⚙️ System Prompt: {CHATBOT_BASELINE_PROMPT.strip()}")

    try:
        response = provider.generate(
            user_query,
            system_prompt=CHATBOT_BASELINE_PROMPT,
        )
    except Exception as error:
        response = f"LỖI khi gọi LLM Provider: {error}"

    print(f"🤖 Chatbot trả lời:\n{response}")
    return response


def extract_order_id(user_query: str) -> str | None:
    """
    Tìm mã đơn hàng trong câu hỏi.

    Các mã mock hiện dùng dạng:
        DH001
        DH002

    Args:
        user_query: Câu hỏi của người dùng.

    Returns:
        Mã đơn hàng nếu tìm thấy, ngược lại trả về None.
    """
    match = re.search(r"\bDH\d+\b", user_query.upper())
    return match.group(0) if match else None


def call_tool(tool_name: str, *args: Any) -> str:
    """
    Gọi tool thông qua AVAILABLE_TOOLS và xử lý lỗi an toàn.

    Args:
        tool_name: Tên tool cần gọi.
        *args: Danh sách tham số truyền cho tool.

    Returns:
        Observation do tool trả về hoặc thông báo lỗi.
    """
    tool = AVAILABLE_TOOLS.get(tool_name)

    if tool is None:
        return f"LỖI: Tool '{tool_name}' chưa được đăng ký."

    try:
        return str(tool(*args))
    except TypeError as error:
        return (
            f"LỖI: Gọi sai tham số của tool '{tool_name}': {error}"
        )
    except Exception as error:
        return (
            f"LỖI: Tool '{tool_name}' gặp sự cố khi thực thi: {error}"
        )


def run_react_agent(user_query: str, provider: Any) -> str:
    """
    Chạy demo ReAct Agent cho bài toán:
    tra cứu đơn hàng và kiểm tra điều kiện đổi trả.

    Luồng demo:
        Thought
        -> Action: tra_cuu_don_hang
        -> Observation
        -> Thought
        -> Action: kiem_tra_dieu_kien_doi_tra
        -> Observation
        -> Final Answer

    Args:
        user_query: Câu hỏi của người dùng.
        provider: LLM provider, giữ lại để tích hợp ở mốc sau.

    Returns:
        Câu trả lời cuối cùng của Agent.
    """
    del provider  # Hiện tại demo dùng logic xác định, chưa gọi LLM trong loop

    print(f"\n🤖 [REACT AGENT] Câu hỏi: {user_query}")

    order_id = extract_order_id(user_query)

    if not order_id:
        final_answer = (
            "Bạn chưa cung cấp mã đơn hàng. "
            "Vui lòng nhập mã theo dạng DH001 hoặc DH002."
        )
        print("\n🧠 Thought: Chưa có mã đơn hàng để tra cứu.")
        print(f"🏁 Final Answer: {final_answer}")
        return final_answer

    step = 0
    observations: list[str] = []

    while step < MAX_ITERATIONS:
        step += 1

        print(
            f"\n--- 🔄 Vòng lặp ReAct "
            f"(Step {step}/{MAX_ITERATIONS}) ---"
        )

        if step == 1:
            print(
                "🧠 Thought: Cần tra cứu thông tin đơn hàng trước "
                "khi đưa ra kết luận."
            )
            print(
                f"🛠️ Action: tra_cuu_don_hang['{order_id}']"
            )

            observation = call_tool(
                "tra_cuu_don_hang",
                order_id,
            )
            observations.append(observation)

            print(f"👁️ Observation:\n{observation}")

            if observation.startswith("LỖI"):
                final_answer = (
                    f"Không thể tra cứu đơn hàng {order_id}. "
                    f"Chi tiết: {observation}"
                )
                print(f"🏁 Final Answer: {final_answer}")
                return final_answer

        elif step == 2:
            print(
                "🧠 Thought: Đơn hàng tồn tại. "
                "Tiếp theo cần kiểm tra điều kiện đổi trả."
            )
            print(
                f"🛠️ Action: "
                f"kiem_tra_dieu_kien_doi_tra['{order_id}']"
            )

            observation = call_tool(
                "kiem_tra_dieu_kien_doi_tra",
                order_id,
            )
            observations.append(observation)

            print(f"👁️ Observation: {observation}")

        elif step == 3:
            order_observation = observations[0]
            eligibility_observation = (
                observations[1]
                if len(observations) > 1
                else "Chưa có kết quả kiểm tra đổi trả."
            )

            print(
                "🧠 Thought: Đã có đủ Observation để trả lời "
                "người dùng."
            )

            final_answer = (
                f"Thông tin đơn hàng {order_id}:\n"
                f"{order_observation}\n\n"
                f"Kết quả kiểm tra đổi trả:\n"
                f"{eligibility_observation}"
            )

            print(f"🏁 Final Answer:\n{final_answer}")
            return final_answer

    final_answer = (
        f"Agent đã đạt giới hạn tối đa {MAX_ITERATIONS} bước "
        "nhưng chưa hoàn thành yêu cầu."
    )
    print(f"🛡️ GUARDRAIL TRIGGERED: {final_answer}")
    return final_answer


def choose_sample_query(
    tests: list[dict[str, Any]],
) -> str:
    """
    Chọn một câu hỏi test phù hợp với đề tài đơn hàng.

    Nếu file test case chưa cập nhật đúng đề tài,
    dùng câu hỏi mặc định để app vẫn chạy được.
    """
    for test_case in tests:
        question = test_case.get("question", "")

        if isinstance(question, str) and extract_order_id(question):
            return question

    return "Kiểm tra giúp tôi đơn hàng DH001 có được đổi trả không?"


def main() -> None:
    """
    Hàm khởi chạy chương trình.
    """
    print("=" * 58)
    print("🏫 ĐẠI HỌC VINUNI - BÀI LAB 3: CHATBOT VS REACT AGENT")
    print("=" * 58)

    try:
        provider = get_llm_provider()
    except Exception as error:
        print(f"❌ Không thể khởi tạo LLM Provider: {error}")
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
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as error:
        print(f"❌ Không thể tải test cases: {error}")
        return

    print(
        f"✅ Đã tải thành công {len(tests)} Test Cases "
        "từ config/test_cases.json\n"
    )

    sample_query = choose_sample_query(tests)

    print(f"🧪 Test được chọn: {sample_query}\n")

    print("--- DEMO 1: CHẠY TRÊN CHATBOT BASELINE ---")
    run_baseline_chatbot(sample_query, provider)

    print("\n--- DEMO 2: CHẠY TRÊN REACT AGENT ---")
    run_react_agent(sample_query, provider)


if __name__ == "__main__":
    main()