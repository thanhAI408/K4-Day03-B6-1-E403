"""
🌐 WEB AGENT UI (Flask Web App)
Đại Học VinUni - Bài Lab 3: Chatbot vs ReAct Agent
Trợ Lý Tra Cứu Đơn Hàng & Xử Lý Đổi Trả

Chạy ứng dụng: python src/web_app.py
Truy cập Web: http://127.0.0.1:5000
"""

import json
import os
import sys
import random
from flask import Flask, jsonify, render_template_string, request

# Đảm bảo import từ thư mục src/
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(CURRENT_DIR)

if CURRENT_DIR not in sys.path:
    sys.path.append(CURRENT_DIR)

from tools import (
    AVAILABLE_TOOLS,
    MOCK_ORDERS_DB,
    MOCK_PRODUCT_POLICY,
    MOCK_SHIPPING_DB,
    MOCK_RETURN_REQUESTS,
)
from prompts import (
    CHATBOT_BASELINE_PROMPT,
    REACT_SYSTEM_PROMPT,
    MAX_ITERATIONS,
    CONFIRMATION_REQUIRED_TOOLS,
)
from providers import get_llm_provider
from app import (
    load_test_cases,
    parse_action,
    extract_final_answer,
    check_action_guardrails,
    generate_react_step,
    call_tool,
)

app = Flask(__name__)


# =============================================================================
# CHẠY AGENT & CHATBOT CHO WEB API
# =============================================================================

def execute_baseline(user_query: str, provider) -> str:
    """Chạy Chatbot Baseline và trả về kết quả string"""
    try:
        return provider.generate(user_query, system_prompt=CHATBOT_BASELINE_PROMPT)
    except Exception as e:
        return f"[Lỗi Baseline]: {str(e)}"


def execute_react_trace(user_query: str, provider) -> dict:
    """Chạy ReAct Agent và thu thập chi tiết từng bước (Trace Steps)"""
    scratchpad = ""
    executed_actions = set()
    steps_log = []
    final_ans = None
    guardrail_notice = None

    for step in range(1, MAX_ITERATIONS + 1):
        print(f"--- 🔄 ReAct Step {step}/{MAX_ITERATIONS} ---", flush=True)
        llm_output = generate_react_step(provider, user_query, scratchpad)
        print(f"🧠 Output:\n{llm_output}", flush=True)
        
        # Phân tích Final Answer
        final_answer = extract_final_answer(llm_output)
        
        if final_answer is not None:
            print(f"🏁 Final Answer Found: {final_answer[:100]}...", flush=True)
            steps_log.append({
                "step": step,
                "thought": llm_output.strip(),
                "action": None,
                "observation": None,
                "final_answer": final_answer,
                "is_final": True
            })
            final_ans = final_answer
            break

        tool_name, arguments = parse_action(llm_output)

        if not tool_name:
            guardrail_notice = "Agent không sinh đúng định dạng Action hoặc Final Answer."
            print(f"🛡️ Guardrail: {guardrail_notice}", flush=True)
            steps_log.append({
                "step": step,
                "thought": llm_output.strip(),
                "action": None,
                "observation": None,
                "guardrail": guardrail_notice,
                "is_final": True
            })
            final_ans = guardrail_notice
            break

        # Kiểm tra Guardrail
        guardrail_error = check_action_guardrails(tool_name, arguments, user_query, executed_actions)
        if guardrail_error:
            guardrail_notice = f"Không thể thực hiện Action vì {guardrail_error}"
            print(f"🛡️ Guardrail Error: {guardrail_notice}", flush=True)
            steps_log.append({
                "step": step,
                "thought": llm_output.strip(),
                "action": f"{tool_name}[{', '.join(arguments)}]",
                "observation": None,
                "guardrail": guardrail_notice,
                "is_final": True
            })
            final_ans = guardrail_notice
            break

        action_key = (tool_name, tuple(arguments))
        executed_actions.add(action_key)

        # Gọi Tool thực tế
        observation = call_tool(tool_name, arguments)
        print(f"👁️ Obs: {observation[:100]}...", flush=True)

        steps_log.append({
            "step": step,
            "thought": llm_output.strip(),
            "action": f"{tool_name}[{', '.join(arguments)}]",
            "observation": observation,
            "guardrail": None,
            "is_final": False
        })

        scratchpad += f"\n\n{llm_output.strip()}\nObservation từ {tool_name}:\n{observation}"

        if observation.startswith("LỖI:"):
            scratchpad += "\nTool vừa gặp lỗi. Không được bịa dữ liệu và không được lặp lại cùng Action."

    if final_ans is None:
        guardrail_notice = f"Agent đã đạt giới hạn tối đa {MAX_ITERATIONS} bước."
        final_ans = guardrail_notice

    return {
        "steps": steps_log,
        "final_answer": final_ans,
        "guardrail_triggered": guardrail_notice
    }


# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.route("/api/test-cases", methods=["GET"])
def get_cases():
    try:
        cases = load_test_cases()
        return jsonify(cases)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/mock-data", methods=["GET"])
def get_mock_data():
    return jsonify({
        "orders": MOCK_ORDERS_DB,
        "product_policies": MOCK_PRODUCT_POLICY,
        "shipping": MOCK_SHIPPING_DB,
        "return_requests": MOCK_RETURN_REQUESTS
    })


@app.route("/api/run", methods=["POST"])
def run_agent_api():
    data = request.json or {}
    query = data.get("query", "").strip()

    if not query:
        return jsonify({"error": "Câu hỏi không được để trống!"}), 400

    print(f"\n==================================================", flush=True)
    print(f"📥 [WEB CLIENT REQUEST]: {query}", flush=True)
    print(f"==================================================", flush=True)

    provider = get_llm_provider()
    provider_name = provider.__class__.__name__
    model_name = getattr(provider, "model_name", "Offline Mock Mode")
    print(f"🔌 Using Provider: {provider_name} ({model_name})", flush=True)

    # 1. Run Baseline
    print("💬 Executing Chatbot Baseline...", flush=True)
    baseline_res = execute_baseline(query, provider)
    print(f"🤖 Baseline Done. Length: {len(baseline_res)} chars", flush=True)

    # 2. Run ReAct Trace
    print("🧠 Executing ReAct Agent Trace...", flush=True)
    react_res = execute_react_trace(query, provider)
    print(f"🏁 ReAct Trace Done. Steps count: {len(react_res.get('steps', []))}", flush=True)

    return jsonify({
        "query": query,
        "provider_info": f"{provider_name} ({model_name})",
        "baseline_response": baseline_res,
        "react_data": react_res
    })


# =============================================================================
# HTML FRONTEND TEMPLATE (MODERN VINAI THEME WITH GLASSMORPHISM & TABS)
# =============================================================================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VinUni Lab 3 — Trợ Lý Tra Cứu Đơn Hàng & Xử Lý Đổi Trả</title>
    <!-- Google Fonts & Font Awesome Icons -->
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    
    <style>
        :root {
            --bg-dark: #0f172a;
            --card-bg: rgba(30, 41, 59, 0.7);
            --card-border: rgba(255, 255, 255, 0.1);
            --primary: #6366f1;
            --primary-hover: #4f46e5;
            --accent: #06b6d4;
            --accent-green: #10b981;
            --accent-orange: #f59e0b;
            --accent-red: #ef4444;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: 'Plus Jakarta Sans', sans-serif;
        }

        body {
            background-color: var(--bg-dark);
            background-image: 
                radial-gradient(at 0% 0%, rgba(99, 102, 241, 0.15) 0px, transparent 50%),
                radial-gradient(at 100% 100%, rgba(6, 182, 212, 0.15) 0px, transparent 50%);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }

        header {
            padding: 1.25rem 2rem;
            background: rgba(15, 23, 42, 0.8);
            backdrop-filter: blur(12px);
            border-bottom: 1px solid var(--card-border);
            display: flex;
            justify-content: space-between;
            align-items: center;
            position: sticky;
            top: 0;
            z-index: 100;
        }

        .logo-area {
            display: flex;
            align-items: center;
            gap: 1rem;
        }

        .logo-icon {
            width: 42px;
            height: 42px;
            background: linear-gradient(135deg, var(--primary), var(--accent));
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.25rem;
            box-shadow: 0 4px 15px rgba(99, 102, 241, 0.4);
        }

        .logo-text h1 {
            font-size: 1.2rem;
            font-weight: 800;
            background: linear-gradient(90deg, #ffffff, #cbd5e1);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .logo-text p {
            font-size: 0.8rem;
            color: var(--text-muted);
        }

        .nav-tabs {
            display: flex;
            gap: 0.5rem;
            background: rgba(30, 41, 59, 0.8);
            padding: 0.35rem;
            border-radius: 12px;
            border: 1px solid var(--card-border);
        }

        .nav-btn {
            padding: 0.6rem 1.2rem;
            border-radius: 8px;
            border: none;
            background: transparent;
            color: var(--text-muted);
            font-weight: 600;
            font-size: 0.88rem;
            cursor: pointer;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .nav-btn.active {
            background: var(--primary);
            color: #fff;
            box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
        }

        .container {
            max-width: 1350px;
            width: 100%;
            margin: 1.5rem auto;
            padding: 0 1.5rem;
            flex: 1;
        }

        .tab-content {
            display: none;
        }

        .tab-content.active {
            display: block;
        }

        /* ---------------------------------------------------- */
        /* TAB 1: DEMO CHATBOT VS REACT AGENT */
        /* ---------------------------------------------------- */

        .input-panel {
            background: var(--card-bg);
            backdrop-filter: blur(16px);
            border: 1px solid var(--card-border);
            border-radius: 16px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }

        .input-controls {
            display: flex;
            gap: 1rem;
            margin-top: 1rem;
            align-items: center;
            flex-wrap: wrap;
        }

        .query-textarea {
            width: 100%;
            background: rgba(15, 23, 42, 0.7);
            border: 1px solid rgba(255, 255, 255, 0.15);
            border-radius: 12px;
            padding: 1rem;
            color: #fff;
            font-size: 0.98rem;
            resize: vertical;
            min-height: 80px;
            outline: none;
            transition: border-color 0.2s;
        }

        .query-textarea:focus {
            border-color: var(--primary);
        }

        .select-custom {
            background: rgba(15, 23, 42, 0.8);
            color: var(--text-main);
            border: 1px solid var(--card-border);
            padding: 0.75rem 1rem;
            border-radius: 10px;
            font-size: 0.88rem;
            outline: none;
            flex: 1;
            min-width: 250px;
        }

        .btn {
            padding: 0.75rem 1.4rem;
            border-radius: 10px;
            border: none;
            font-weight: 600;
            font-size: 0.9rem;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            transition: all 0.2s;
        }

        .btn-primary {
            background: linear-gradient(135deg, var(--primary), var(--primary-hover));
            color: #fff;
            box-shadow: 0 4px 15px rgba(99, 102, 241, 0.4);
        }

        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(99, 102, 241, 0.6);
        }

        .btn-secondary {
            background: rgba(255,255,255,0.08);
            color: var(--text-main);
            border: 1px solid var(--card-border);
        }

        .btn-secondary:hover {
            background: rgba(255,255,255,0.15);
        }

        /* GRID SO SÁNH */
        .comparison-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1.5rem;
        }

        @media (max-width: 900px) {
            .comparison-grid {
                grid-template-columns: 1fr;
            }
        }

        .demo-card {
            background: var(--card-bg);
            backdrop-filter: blur(16px);
            border: 1px solid var(--card-border);
            border-radius: 16px;
            padding: 1.5rem;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            display: flex;
            flex-direction: column;
        }

        .demo-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding-bottom: 1rem;
            margin-bottom: 1rem;
            border-bottom: 1px solid var(--card-border);
        }

        .demo-title {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            font-size: 1.1rem;
            font-weight: 700;
        }

        .badge {
            padding: 0.25rem 0.6rem;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 700;
            text-transform: uppercase;
        }

        .badge-baseline { background: rgba(239, 68, 68, 0.2); color: #fca5a5; }
        .badge-react { background: rgba(16, 185, 129, 0.2); color: #6ee7b7; }

        .response-box {
            background: rgba(15, 23, 42, 0.6);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 12px;
            padding: 1.2rem;
            font-size: 0.95rem;
            line-height: 1.6;
            white-space: pre-wrap;
            flex: 1;
        }

        /* REACT STEPS TRACE UI */
        .step-block {
            background: rgba(15, 23, 42, 0.7);
            border: 1px solid rgba(255,255,255,0.08);
            border-left: 4px solid var(--accent);
            border-radius: 10px;
            padding: 1rem;
            margin-bottom: 1rem;
        }

        .step-title {
            font-weight: 700;
            color: var(--accent);
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 0.5rem;
        }

        .thought-text {
            color: #cbd5e1;
            font-size: 0.92rem;
            margin-bottom: 0.5rem;
        }

        .action-chip {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            background: rgba(99, 102, 241, 0.2);
            color: #a5b4fc;
            border: 1px solid rgba(99, 102, 241, 0.3);
            padding: 0.3rem 0.75rem;
            border-radius: 6px;
            font-family: monospace;
            font-size: 0.88rem;
            margin-bottom: 0.5rem;
        }

        .obs-box {
            background: rgba(0,0,0,0.3);
            border-radius: 6px;
            padding: 0.6rem 0.8rem;
            font-size: 0.85rem;
            color: #94a3b8;
            font-family: monospace;
            white-space: pre-wrap;
        }

        .final-box {
            background: rgba(16, 185, 129, 0.15);
            border: 1px solid rgba(16, 185, 129, 0.4);
            border-radius: 12px;
            padding: 1rem;
            color: #a7f3d0;
            font-weight: 500;
            margin-top: 1rem;
        }

        .guardrail-box {
            background: rgba(239, 68, 68, 0.15);
            border: 1px solid rgba(239, 68, 68, 0.4);
            border-radius: 12px;
            padding: 1rem;
            color: #fca5a5;
            font-weight: 600;
            margin-top: 1rem;
        }

        /* ---------------------------------------------------- */
        /* TAB 2: DATA MOCK EXPLORER */
        /* ---------------------------------------------------- */

        .mock-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 1.5rem;
        }

        .mock-card {
            background: var(--card-bg);
            backdrop-filter: blur(16px);
            border: 1px solid var(--card-border);
            border-radius: 16px;
            padding: 1.25rem;
        }

        .mock-card h3 {
            font-size: 1.05rem;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            color: var(--accent);
            border-bottom: 1px solid var(--card-border);
            padding-bottom: 0.6rem;
        }

        .json-view {
            background: rgba(15, 23, 42, 0.8);
            border-radius: 10px;
            padding: 1rem;
            font-family: monospace;
            font-size: 0.85rem;
            color: #38bdf8;
            max-height: 380px;
            overflow-y: auto;
            white-space: pre-wrap;
        }

        /* LOADER */
        .spinner {
            display: inline-block;
            width: 18px;
            height: 18px;
            border: 3px solid rgba(255,255,255,.3);
            border-radius: 50%;
            border-top-color: #fff;
            animation: spin 1s ease-in-out infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }
    </style>
</head>
<body>

    <header>
        <div class="logo-area">
            <div class="logo-icon"><i class="fa-solid fa-robot"></i></div>
            <div class="logo-text">
                <h1>VinUni — Agentic AI Platform</h1>
                <p>Đề tài 5: Tra Cứu Đơn Hàng & Xử Lý Đổi Trả (Lab 3)</p>
            </div>
        </div>

        <nav class="nav-tabs">
            <button class="nav-btn active" onclick="switchTab('demo-tab')">
                <i class="fa-solid fa-flask"></i> Live Demo & Comparison
            </button>
            <button class="nav-btn" onclick="switchTab('mock-tab')">
                <i class="fa-solid fa-database"></i> Mock Data Explorer
            </button>
        </nav>
    </header>

    <div class="container">
        <!-- ======================================================== -->
        <!-- TAB 1: LIVE DEMO -->
        <!-- ======================================================== -->
        <div id="demo-tab" class="tab-content active">
            <div class="input-panel">
                <label style="font-weight: 700; margin-bottom: 0.5rem; display: block; font-size: 0.95rem;">
                    💬 Nhập câu hỏi hoặc chọn từ bộ Test Case:
                </label>
                <textarea id="queryInput" class="query-textarea" placeholder="Nhập câu hỏi tại đây (Ví dụ: Kiểm tra đơn hàng DH001 giúp tôi...)"></textarea>

                <div class="input-controls">
                    <select id="testCaseSelect" class="select-custom" onchange="onSelectTestCase()">
                        <option value="">-- Chọn câu hỏi từ Test Cases (15 câu) --</option>
                    </select>

                    <button class="btn btn-secondary" onclick="pickRandomCase()">
                        <i class="fa-solid fa-dice"></i> Pick Random Test Case
                    </button>

                    <button class="btn btn-primary" id="btnRun" onclick="runAnalysis()">
                        <i class="fa-solid fa-paper-plane"></i> Chạy So Sánh (Run Test)
                    </button>
                </div>
            </div>

            <!-- BẢNG KẾT QUẢ SO SÁNH -->
            <div class="comparison-grid">
                <!-- CARD 1: BASELINE -->
                <div class="demo-card">
                    <div class="demo-header">
                        <div class="demo-title">
                            <i class="fa-solid fa-comment" style="color: var(--accent-red);"></i>
                            Chatbot Baseline
                        </div>
                        <span class="badge badge-baseline">Không có Tool</span>
                    </div>

                    <div id="baselineBox" class="response-box">
                        <span style="color: var(--text-muted);">Bấm "Chạy So Sánh" để xem phản hồi từ Chatbot Baseline...</span>
                    </div>
                </div>

                <!-- CARD 2: REACT AGENT -->
                <div class="demo-card">
                    <div class="demo-header">
                        <div class="demo-title">
                            <i class="fa-solid fa-brain" style="color: var(--accent-green);"></i>
                            ReAct Agent (Thought -> Action -> Obs)
                        </div>
                        <span class="badge badge-react">Có Tool & Guardrails</span>
                    </div>

                    <div id="reactTraceBox" class="response-box">
                        <span style="color: var(--text-muted);">Bấm "Chạy So Sánh" để xem chuỗi suy luận Thought ➔ Action ➔ Observation...</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- ======================================================== -->
        <!-- TAB 2: MOCK DATA EXPLORER -->
        <!-- ======================================================== -->
        <div id="mock-tab" class="tab-content">
            <div class="mock-grid">
                <div class="mock-card">
                    <h3><i class="fa-solid fa-boxes-packing"></i> MOCK_ORDERS_DB (8 Đơn hàng)</h3>
                    <div id="jsonOrders" class="json-view">Loading...</div>
                </div>

                <div class="mock-card">
                    <h3><i class="fa-solid fa-shield-halved"></i> MOCK_PRODUCT_POLICY (6 Chính sách)</h3>
                    <div id="jsonPolicies" class="json-view">Loading...</div>
                </div>

                <div class="mock-card">
                    <h3><i class="fa-solid fa-truck-fast"></i> MOCK_SHIPPING_DB (Vận chuyển)</h3>
                    <div id="jsonShipping" class="json-view">Loading...</div>
                </div>

                <div class="mock-card">
                    <h3><i class="fa-solid fa-rotate-left"></i> MOCK_RETURN_REQUESTS (RMA)</h3>
                    <div id="jsonReturns" class="json-view">Loading...</div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let globalTestCases = [];

        // Chuyển Tab
        function switchTab(tabId) {
            document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.nav-btn').forEach(el => el.classList.remove('active'));
            
            document.getElementById(tabId).classList.add('active');
            event.currentTarget.classList.add('active');

            if (tabId === 'mock-tab') {
                loadMockData();
            }
        }

        // Tải danh sách Test Cases khi mở trang
        async function loadTestCases() {
            try {
                const res = await fetch('/api/test-cases');
                globalTestCases = await res.json();

                const select = document.getElementById('testCaseSelect');
                select.innerHTML = '<option value="">-- Chọn câu hỏi từ Test Cases (15 câu) --</option>';

                globalTestCases.forEach((tc, idx) => {
                    const opt = document.createElement('option');
                    opt.value = tc.question;
                    opt.textContent = `[#${tc.id}] ${tc.category} — ${tc.question.substring(0, 55)}...`;
                    select.appendChild(opt);
                });
            } catch (err) {
                console.error('Lỗi tải test cases:', err);
            }
        }

        function onSelectTestCase() {
            const select = document.getElementById('testCaseSelect');
            if (select.value) {
                document.getElementById('queryInput').value = select.value;
            }
        }

        function pickRandomCase() {
            if (globalTestCases.length === 0) return;
            const randomCase = globalTestCases[Math.floor(Math.random() * globalTestCases.length)];
            document.getElementById('queryInput').value = randomCase.question;
            
            // Cập nhật lại dropdown
            const select = document.getElementById('testCaseSelect');
            select.value = randomCase.question;
        }

        // Tải dữ liệu Mock Data Tab
        async function loadMockData() {
            try {
                const res = await fetch('/api/mock-data');
                const data = await res.json();

                document.getElementById('jsonOrders').textContent = JSON.stringify(data.orders, null, 2);
                document.getElementById('jsonPolicies').textContent = JSON.stringify(data.product_policies, null, 2);
                document.getElementById('jsonShipping').textContent = JSON.stringify(data.shipping, null, 2);
                document.getElementById('jsonReturns').textContent = JSON.stringify(data.return_requests, null, 2);
            } catch (err) {
                console.error('Lỗi tải mock data:', err);
            }
        }

        // Thực thi chạy so sánh
        async function runAnalysis() {
            const query = document.getElementById('queryInput').value.trim();
            if (!query) {
                alert('Vui lòng nhập câu hỏi hoặc chọn 1 test case!');
                return;
            }

            const btn = document.getElementById('btnRun');
            const baselineBox = document.getElementById('baselineBox');
            const reactTraceBox = document.getElementById('reactTraceBox');

            btn.disabled = true;
            btn.innerHTML = '<span class="spinner"></span> Đang chạy...';

            baselineBox.innerHTML = '<div style="color: var(--accent);"><span class="spinner"></span> Đang suy luận phản hồi Chatbot Baseline...</div>';
            reactTraceBox.innerHTML = '<div style="color: var(--accent);"><span class="spinner"></span> Đang kích hoạt vòng lặp ReAct Agent...</div>';

            try {
                const res = await fetch('/api/run', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query: query })
                });

                const data = await res.json();

                // 1. Render Baseline Result
                baselineBox.textContent = data.baseline_response;

                // 2. Render ReAct Steps Trace
                renderReactTrace(data.react_data);

            } catch (err) {
                baselineBox.textContent = 'Lỗi kết nối API: ' + err.message;
                reactTraceBox.textContent = 'Lỗi kết nối API: ' + err.message;
            } finally {
                btn.disabled = false;
                btn.innerHTML = '<i class="fa-solid fa-paper-plane"></i> Chạy So Sánh (Run Test)';
            }
        }

        function renderReactTrace(reactData) {
            const container = document.getElementById('reactTraceBox');
            container.innerHTML = '';

            if (!reactData || !reactData.steps) {
                container.textContent = 'Không có thông tin trace.';
                return;
            }

            reactData.steps.forEach(stepObj => {
                const stepEl = document.createElement('div');
                stepEl.className = 'step-block';

                let contentHtml = `<div class="step-title">🔄 STEP ${stepObj.step}</div>`;
                
                if (stepObj.thought) {
                    contentHtml += `<div class="thought-text">${escapeHtml(stepObj.thought)}</div>`;
                }

                if (stepObj.action) {
                    contentHtml += `<div class="action-chip"><i class="fa-solid fa-wrench"></i> ${escapeHtml(stepObj.action)}</div>`;
                }

                if (stepObj.observation) {
                    contentHtml += `<div class="obs-box">👁️ ${escapeHtml(stepObj.observation)}</div>`;
                }

                stepEl.innerHTML = contentHtml;
                container.appendChild(stepEl);
            });

            // Guardrail hoặc Final Answer
            if (reactData.guardrail_triggered) {
                const gBox = document.createElement('div');
                gBox.className = 'guardrail-box';
                gBox.innerHTML = `<i class="fa-solid fa-shield-halved"></i> <strong>GUARDRAIL TRIGGERED:</strong> ${escapeHtml(reactData.guardrail_triggered)}`;
                container.appendChild(gBox);
            } else if (reactData.final_answer) {
                const fBox = document.createElement('div');
                fBox.className = 'final-box';
                fBox.innerHTML = `<i class="fa-solid fa-circle-check"></i> <strong>FINAL ANSWER:</strong> ${escapeHtml(reactData.final_answer)}`;
                container.appendChild(fBox);
            }
        }

        function escapeHtml(text) {
            if (!text) return '';
            return text
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;")
                .replace(/'/g, "&#039;");
        }

        // Init
        loadTestCases();
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)


if __name__ == "__main__":
    print("==================================================")
    print("🚀 MỞ ỨNG DỤNG WEB AGENT UI")
    print("👉 Mở trình duyệt truy cập: http://127.0.0.1:5000")
    print("==================================================")
    app.run(host="127.0.0.1", port=5000, debug=True)
