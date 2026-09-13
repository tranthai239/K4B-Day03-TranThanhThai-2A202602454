"""
🚀 CORE AGENT APPLICATION (DAY 03: CHATBOT VS REACT AGENT)
Thực thi so sánh giữa Chatbot Baseline (Cấp 2) và ReAct Agent kết nối MCP Server (Cấp 3).
"""

import json
import os
import re
import sys
import time
from datetime import datetime
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from mcp_server import MCPLibraryServer
from prompts import (
    CHATBOT_BASELINE_PROMPT,
    REACT_AGENT_SYSTEM_PROMPT,
    MAX_ITERATIONS
)
from providers import get_llm_provider

load_dotenv()

def load_test_cases():
    """Tải danh sách 5 test cases từ config/test_cases.json hoặc config/test_cases.example.json"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, "config", "test_cases.json")
    if not os.path.exists(config_path):
        example_path = os.path.join(base_dir, "config", "test_cases.example.json")
        if os.path.exists(example_path):
            print("⚠️ [CONFIG NOTICE]: Chưa thấy file 'config/test_cases.json'. Đang dùng mẫu 'config/test_cases.example.json'.")
            print("👉 Hãy chạy: copy config/test_cases.example.json config/test_cases.json và viết test cases theo đề tài của bạn!\n")
            config_path = example_path
        else:
            config_path = "test_cases.json"
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_waterfall_trace(trace_data):
    """Ghi vết log Waterfall Trace Log ra file docs/trace_waterfall.json"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    docs_dir = os.path.join(base_dir, "docs")
    os.makedirs(docs_dir, exist_ok=True)
    trace_path = os.path.join(docs_dir, "trace_waterfall.json")
    with open(trace_path, "w", encoding="utf-8") as f:
        json.dump(trace_data, f, ensure_ascii=False, indent=2)
    if isinstance(trace_data, dict):
        print(f"📊 [OBSERVABILITY]: Đã lưu {len(trace_data.get('events', []))} sự kiện Waterfall Trace tại '{trace_path}'!")
    else:
        print(f"📊 [OBSERVABILITY]: Đã lưu {len(trace_data)} sự kiện Waterfall Trace tại '{trace_path}'!")


def run_baseline_chatbot(user_query: str, provider):
    """Chạy Chatbot gốc (Cấp 2) không có công cụ gọi Tool"""
    print(f"\n💬 [CHATBOT BASELINE] Câu hỏi: {user_query}")
    response = provider.generate(user_query, system_prompt=CHATBOT_BASELINE_PROMPT)
    print(f"🤖 Chatbot phản hồi:\n{response}")


def _build_final_answer(obs_data: dict) -> str:
    """Tổng hợp câu trả lời từ Observation trả về bởi MCP Server."""
    status = obs_data.get("status")
    if status == "SUCCESS":
        if isinstance(obs_data.get("data"), list):
            books = obs_data["data"]
            book_lines = [
                f"- {book.get('title', 'Không rõ tên')} ({book.get('book_code', '')}) - {book.get('status', 'UNKNOWN')}"
                for book in books
            ]
            return f"Thư viện hiện có {len(books)} sách:\n" + "\n".join(book_lines)
        elif "data" in obs_data:
            book = obs_data["data"]
            return (
                f"Sách {book.get('title', 'không rõ')} (mã {book.get('book_code', '')}) đang ở {book.get('location', 'địa điểm chưa rõ')}. "
                f"Trạng thái: {book.get('status', '')}. Số bản sẵn: {book.get('available_copies', 0)}."
            )
        elif "message" in obs_data:
            return obs_data["message"]
        return f"Đã xử lý thành công: {json.dumps(obs_data, ensure_ascii=False)}"
    elif status == "NOT_FOUND":
        return obs_data.get("message", "Không tìm thấy tài liệu phù hợp trong thư viện.")
    return f"Phản hồi từ công cụ: {json.dumps(obs_data, ensure_ascii=False)}"


def _trace_event(step: int, action_type: str, llm_response: dict, latency_ms: float, test_case_id: str = None, **extra) -> dict:
    """Tạo một event trace chuẩn hoá với metadata đầy đủ."""
    event = {
        "test_case_id": test_case_id,
        "step": step,
        "timestamp": datetime.now().astimezone().isoformat(timespec="milliseconds"),
        "action_type": action_type,
        "execution_mode": llm_response.get("execution_mode"),
        "provider": llm_response.get("provider"),
        "model": llm_response.get("model"),
        "thought": llm_response.get("thought", "Đang suy luận..."),
        "latency_ms": latency_ms,
    }
    event.update(extra)
    return event


def run_react_agent(user_query: str, provider, mcp_server: MCPLibraryServer, test_case_id: str = None) -> list:
    """
    [REACT AGENT LOOP] Thực thi vòng lặp Thought -> Action -> Observation với MCP Server.
    - mcp_fast_path: gọi MCP trực tiếp rồi tổng hợp câu trả lời.
    - live_llm: đưa Observation trở lại LLM cho tới khi có Final Answer.
    Trả về danh sách trace log của phiên thực thi.
    """
    print(f"\n🤖 [REACT AGENT] Câu hỏi: {user_query}")

    step = 0
    trace_logs = []
    history = []
    tools_list = mcp_server.list_tools()

    while step < MAX_ITERATIONS:
        step += 1
        step_start_time = time.time()
        print(f"\n--- 🔄 Vòng lặp ReAct Loop (Step {step}/{MAX_ITERATIONS}) ---")

        llm_response = provider.generate_with_tools(user_query, tools_list, system_prompt=REACT_AGENT_SYSTEM_PROMPT, history=history)
        latency_ms = round((time.time() - step_start_time) * 1000, 2)

        thought = llm_response.get("thought", "Đang suy luận...")
        mode = llm_response.get("execution_mode")
        print(f"🧠 [Thought]: {thought}")

        if llm_response.get("type") == "error":
            print(f"🚨 [LLM Error]: {llm_response.get('content')}")
            trace_logs.append(_trace_event(step, "LLM_ERROR", llm_response, latency_ms, test_case_id,
                                           output=llm_response.get("content")))
            break

        if llm_response.get("type") == "text":
            final_content = llm_response.get("content", "")
            print(f"🏁 [Final Answer]: {final_content}")
            trace_logs.append(_trace_event(step, "FINAL_ANSWER", llm_response, latency_ms, test_case_id,
                                           output=final_content))
            break

        if llm_response.get("type") == "tool_call":
            tool_name = llm_response.get("tool_name")
            arguments = llm_response.get("arguments", {})

            print(f"🛠️ [Action Proposed]: {tool_name}({arguments})")

            mcp_result = mcp_server.call_tool(tool_name, arguments)
            obs_data = mcp_result.get("result", {})

            if not obs_data:
                print("👁️ [Observation từ MCP Server]: {}")
            else:
                print(f"👁️ [Observation từ MCP Server]: {json.dumps(obs_data, ensure_ascii=False)}")

            trace_logs.append(_trace_event(step, "TOOL_EXECUTION", llm_response, latency_ms, test_case_id,
                                           tool_name=tool_name, arguments=arguments, observation=obs_data,
                                           resolved_tool=llm_response.get("resolved_tool")))

            # Chỉ live_llm mới đưa Observation trở lại LLM; các mode còn lại tổng hợp ngay.
            if mode == "live_llm":
                history.append({"role": "assistant", "tool_name": tool_name, "arguments": arguments})
                history.append({"role": "tool", "tool_name": tool_name, "observation": obs_data})
                continue

            final_answer = _build_final_answer(obs_data) if obs_data else "Chưa thể trả lời vì MCP Server không trả về dữ liệu hợp lệ."
            print(f"🏁 [Final Answer]: {final_answer}")
            trace_logs.append(_trace_event(step + 1, "FINAL_ANSWER", llm_response, latency_ms, test_case_id,
                                           output=final_answer))
            break

    return trace_logs


if __name__ == "__main__":
    print("==========================================================")
    print("🏫 VINUNI AI COURSE - DAY 03 LAB: CHATBOT VS REACT AGENT")
    print("==========================================================")
    
    provider = get_llm_provider()
    mcp_server = MCPLibraryServer()
    
    print(f"🔌 LLM Provider: {provider.__class__.__name__}")
    print(f"🌐 MCP Server: {mcp_server.server_name}\n")
    
    tests = load_test_cases()
    print(f"✅ Đã tải thành công {len(tests)} Test Cases thử nghiệm.\n")
    
    if "--interactive" in sys.argv:
        print("🎮 [INTERACTIVE MODE] Trò chuyện trực tiếp với ReAct Agent:")
        print("💡 Gợi ý câu hỏi thử nghiệm:")
        print("   1. 'A001' đến 'A005' -> nhập mã sinh viên")
        print("   2. 'Hiển thị trạng thái sinh viên A001' -> xem sách đang mượn / đặt trước")
        print("   3. 'Sinh viên A001 muốn mượn DB101' / 'trả AI205' / 'gia hạn AI205 7 ngày' / 'đặt trước AI205'")
        print("   - Gõ 'logout' để đổi mã sinh viên; gõ 'exit' hoặc 'quit' để kết thúc phiên trò chuyện.\n")
        current_student_id = None
        while True:
            try:
                user_input = input("👤 Sinh viên hỏi: ").strip()
                if not user_input or user_input.lower() in ["exit", "quit"]:
                    print("👋 Tạm biệt! Kết thúc phiên trò chuyện.")
                    break
                if user_input.lower() == "logout":
                    current_student_id = None
                    print("🔓 Đã đăng xuất. Vui lòng nhập mã sinh viên mới.")
                    continue

                student_match = re.search(r"\bA\d{3}\b", user_input.upper())
                if student_match:
                    current_student_id = student_match.group(0)
                elif current_student_id:
                    user_input = f"Sinh viên {current_student_id} {user_input}"

                logs = run_react_agent(user_input, provider, mcp_server)
                save_waterfall_trace(logs)
            except (KeyboardInterrupt, EOFError):
                print("\n👋 Đã thoát phiên tương tác.")
                break
    elif "--all" in sys.argv:
        print("🚀 [TEST SUITE MODE] Kiểm tra 5 Test Cases:")
        completed_count = 0
        todo_count = 0
        all_traces = []
        results = []

        for tc in tests:
            print(f"\n==================================================")
            print(f"🧪 [{tc['id']}] Loại test: {tc['type']} (Độ phức tạp: {tc['complexity']})")
            print(f"📌 Kỳ vọng: {tc['expected_behavior']}")

            if tc["question"].strip().startswith("TODO"):
                print(f"⏸️ [CHƯA KÍCH HOẠT - ĐANG LÀ TODO]:")
                print(f"   {tc['question']}")
                print(f"   👉 Hãy mở file 'config/test_cases.json' để viết câu hỏi thực tế cho Test Case này!")
                todo_count += 1
                results.append({"id": tc["id"], "status": "TODO", "error": None, "modes": []})
            else:
                logs = run_react_agent(tc["question"], provider, mcp_server, test_case_id=tc["id"])
                all_traces.extend(logs)
                completed_count += 1

                has_error = any(e.get("action_type") == "LLM_ERROR" for e in logs)
                has_final = any(e.get("action_type") == "FINAL_ANSWER" for e in logs)
                modes = sorted({e.get("execution_mode") for e in logs if e.get("execution_mode")})
                error_event = next((e for e in logs if e.get("action_type") == "LLM_ERROR"), None)
                results.append({
                    "id": tc["id"],
                    "status": "ERROR" if has_error else ("PASS" if has_final else "NO_ANSWER"),
                    "error": error_event.get("output") if error_event else None,
                    "modes": modes,
                })

        live_count = sum(1 for r in results if "live_llm" in r.get("modes", []))
        pass_count = sum(1 for r in results if r.get("status") == "PASS")
        error_count = sum(1 for r in results if r.get("status") == "ERROR")
        summary = {
            "provider": getattr(provider, "provider_name", provider.__class__.__name__),
            "model": getattr(getattr(provider, "api_provider", provider), "model_name", getattr(provider, "model_name", "unknown")),
            "total": len(tests),
            "completed": completed_count,
            "todo": todo_count,
            "pass": pass_count,
            "error": error_count,
            "live_llm_test_cases": live_count,
            "results": results,
        }

        print(f"\n==================================================")
        print(f"📊 [KẾT QUẢ TEST SUITE]: {pass_count}/{completed_count} PASS | {error_count} ERROR | {todo_count} TODO")
        print(f"   Provider: {summary['provider']} | Model: {summary['model']} | Test dùng live_llm: {live_count}")
        if all_traces:
            save_waterfall_trace({"summary": summary, "events": all_traces})
        print(f"💡 Để trò chuyện trực tiếp từng câu: Chạy 'python src/app.py --interactive'")
    else:
        # Chế độ mặc định khi chỉ gõ 'python src/app.py'
        print("ℹ️ HƯỚNG DẪN SỬ DỤNG CHƯƠNG TRÌNH:")
        print("  1. Chat trực tiếp liên tục:   python src/app.py --interactive")
        print("  2. Chạy toàn bộ Test Cases:    python src/app.py --all\n")

        sample_query = tests[1]["question"]
        print(f"--- 🏁 DEMO CHẠY THỬ 1 TEST CASE MẪU (TC02: Tra cứu học vụ) ---")
        logs = run_react_agent(sample_query, provider, mcp_server, test_case_id=tests[1]["id"])
        save_waterfall_trace(logs)
        print("\n💡 Hãy thử ngay lệnh: python src/app.py --interactive để chat trực tiếp!")
