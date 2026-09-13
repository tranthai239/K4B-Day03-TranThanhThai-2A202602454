"""Small browser API for the VinUni library assistant."""

import contextlib
import io
import json
import os
import re
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import run_react_agent
from mcp_server import MCPLibraryServer
from providers import get_llm_provider

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_DIR = os.path.join(BASE_DIR, "web")
PROVIDER = get_llm_provider()
MCP_SERVER = MCPLibraryServer()


def json_response(handler, payload, status=200):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def run_agent(message, student_id=None):
    query = message.strip()
    if student_id and not re.search(r"\bA\d{3}\b", query.upper()):
        query = f"Sinh viên {student_id} {query}"

    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        trace = run_react_agent(query, PROVIDER, MCP_SERVER)

    final_answers = [item.get("output") for item in trace if item.get("action_type") == "FINAL_ANSWER"]
    return {
        "answer": final_answers[-1] if final_answers else "Chưa nhận được phản hồi từ Agent.",
        "trace": trace,
        "query": query,
    }


class LibraryRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/catalog":
            result = MCP_SERVER.call_tool("library_search", {"book_code": "__ALL__"})
            json_response(self, result["result"])
            return

        if parsed.path == "/api/status":
            student_id = parse_qs(parsed.query).get("student_id", [""])[0]
            result = MCP_SERVER.call_tool("get_student_status", {"student_id": student_id})
            json_response(self, result["result"])
            return

        super().do_GET()

    def do_POST(self):
        if self.path == "/api/chat":
            try:
                length = int(self.headers.get("Content-Length", 0))
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                message = payload.get("message", "")
                student_id = payload.get("student_id")
                if not message.strip():
                    json_response(self, {"status": "ERROR", "message": "Vui lòng nhập nội dung yêu cầu."}, 400)
                    return
                json_response(self, {"status": "SUCCESS", **run_agent(message, student_id)})
            except (ValueError, json.JSONDecodeError):
                json_response(self, {"status": "ERROR", "message": "Dữ liệu gửi lên không hợp lệ."}, 400)
            return

        json_response(self, {"status": "NOT_FOUND"}, 404)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    server = ThreadingHTTPServer(("127.0.0.1", port), LibraryRequestHandler)
    print(f"VinUni Library UI: http://127.0.0.1:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nĐã dừng Library UI.")
    finally:
        server.server_close()
