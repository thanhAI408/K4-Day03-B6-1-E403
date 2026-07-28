"""
🚀 CORE AGENT APP (Dành cho Role 4: Core Agent Developer)
File chính ghép nối tất cả các thành phần: Tools + Prompts + Test Cases + Multi-Provider.
"""

import json
import os
import sys
from dotenv import load_dotenv

# Đảm bảo import các module cùng thư mục src/ hoạt động mượt mà
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Đảm bảo in ra Tiếng Việt và Emojis không bị lỗi trên Windows Console
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Import các thành phần từ file của Role 2, Role 3 & Multi-Provider Adapter
from tools import (
    AVAILABLE_TOOLS,
    tra_cuu_don_hang,
    kiem_tra_dieu_kien_doi_tra,
    tao_yeu_cau_doi_tra,
    chuyen_nhan_vien_ho_tro,
)
from prompts import CHATBOT_BASELINE_PROMPT, REACT_SYSTEM_PROMPT, MAX_ITERATIONS
from providers import get_llm_provider

load_dotenv()

def load_test_cases():
    """Đọc bộ test cases từ config/test_cases.json của Role 1"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, "config", "test_cases.json")
    
    # Fallback kiểm tra nếu file ở thư mục hiện tại
    if not os.path.exists(config_path):
        config_path = "test_cases.json"
        
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def run_baseline_chatbot(user_query: str, provider):
    """
    Dựng Chatbot gốc (Baseline) không có công cụ.
    Dùng để làm baseline so sánh với ReAct Agent.
    """
    print(f"\n💬 [CHATBOT BASELINE] Câu hỏi: {user_query}")
    print(f"⚙️ System Prompt: {CHATBOT_BASELINE_PROMPT.strip()}")
    
    # Gọi LLM Provider thực hiện sinh câu trả lời — không có tool
    response = provider.generate(user_query, system_prompt=CHATBOT_BASELINE_PROMPT)
    print(f"🤖 Chatbot trả lời:\n{response}")


def run_react_agent(user_query: str, provider):
    """
    Dựng vòng lặp ReAct Agent (Thought -> Action -> Observation) có Guardrails.
    Demo hardcode cho đề tài: Tra Cứu Đơn Hàng & Xử Lý Đổi Trả.
    """
    print(f"\n🤖 [REACT AGENT] Câu hỏi: {user_query}")
    step = 0
    
    while step < MAX_ITERATIONS:
        step += 1
        print(f"\n--- 🔄 Vòng lặp ReAct (Step {step}/{MAX_ITERATIONS}) ---")
        
        if step == 1:
            print("🧠 Thought: Khách hỏi về đơn hàng DH001. Tôi cần tra cứu trạng thái đơn hàng này.")
            print("🛠️ Action: tra_cuu_don_hang['DH001']")
            obs = tra_cuu_don_hang("DH001")
            print(f"👁️ Observation: {obs}")
            
        elif step == 2:
            print("🧠 Thought: Đơn đã giao. Khách muốn đổi trả, tôi cần kiểm tra điều kiện đổi trả.")
            print("🛠️ Action: kiem_tra_dieu_kien_doi_tra['DH001']")
            obs = kiem_tra_dieu_kien_doi_tra("DH001")
            print(f"👁️ Observation: {obs}")

        elif step == 3:
            print("🧠 Thought: Đã có đủ thông tin. Tổng hợp câu trả lời cho khách.")
            print("🏁 Final Answer: Đơn hàng DH001 của bạn đã giao thành công. "
                  "Tôi đã kiểm tra điều kiện đổi trả — vui lòng xem kết quả phía trên để biết chi tiết.")
            break
            
    if step >= MAX_ITERATIONS:
        print(f"🛡️ GUARDRAIL TRIGGERED: Đã đạt giới hạn tối đa {MAX_ITERATIONS} bước. Ngắt lặp an toàn!")


if __name__ == "__main__":
    print("==================================================")
    print("🏫 ĐẠI HỌC VINUNI - BÀI LAB 3: CHATBOT VS REACT AGENT")
    print("🎯 Đề tài: Trợ Lý Tra Cứu Đơn Hàng & Xử Lý Đổi Trả")
    print("==================================================")
    
    # Khởi tạo Multi-Provider LLM Adapter (Đọc từ biến môi trường LLM_PROVIDER)
    provider = get_llm_provider()
    model_name = getattr(provider, "model_name", "Offline Mock Mode")
    print(f"🔌 LLM Provider đang hoạt động: {provider.__class__.__name__} (Model: {model_name})")
    
    tests = load_test_cases()
    print(f"✅ Đã tải thành công {len(tests)} Test Cases từ config/test_cases.json\n")
    
    # Demo với Test Case #6 (Multi-step, tra cứu đơn hàng)
    sample_query = tests[5]["question"]  # ID 6: "Đơn hàng DH001 đang ở đâu rồi?"
    
    print("--- DEMO 1: CHẠY TRÊN CHATBOT BASELINE ---")
    run_baseline_chatbot(sample_query, provider)
    
    print("\n--- DEMO 2: CHẠY TRÊN REACT AGENT ---")
    run_react_agent(sample_query, provider)
