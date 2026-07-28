import contextlib
import io
import json
import os
import sys

from app import get_llm_provider, run_baseline_chatbot, run_react_agent


def main():
    payload = json.loads(sys.stdin.read() or "{}")
    mode = payload.get("mode")
    query = str(payload.get("query", "")).strip()
    if mode not in {"baseline", "react"} or not query:
        raise ValueError("mode và query là bắt buộc")

    # Mặc định vẫn offline để repo chạy ngay; khi cấu hình .env,
    # UI sẽ dùng provider/model thật mà không cần sửa code.
    provider = get_llm_provider(os.getenv("LLM_PROVIDER", "mock"))
    trace_buffer = io.StringIO()
    with contextlib.redirect_stdout(trace_buffer):
        answer = (run_baseline_chatbot(query, provider)
                  if mode == "baseline" else run_react_agent(query, provider))
    print(json.dumps({
        "mode": mode,
        "query": query,
        "answer": answer,
        "trace": trace_buffer.getvalue(),
        "provider": provider.__class__.__name__,
        "model": getattr(provider, "model_name", "Offline Mock Mode"),
    }, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False))
        sys.exit(1)
