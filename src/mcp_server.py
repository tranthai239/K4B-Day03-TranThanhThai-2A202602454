"""
🔌 MODEL CONTEXT PROTOCOL (MCP) SERVER MODULE
Mô phỏng kiến trúc MCP Server (Client-Server Architecture) cung cấp công cụ chuẩn hóa.
"""

import json
import sys
from typing import Dict, Any, List
from tools import TOOLS_SCHEMA, dispatch_tool_call

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

class MCPLibraryServer:
    """
    Giả lập MCP Server quản lý thư viện theo chuẩn Model Context Protocol.
    """
    def __init__(self, server_name: str = "vinuni-library-mcp-server"):
        self.server_name = server_name
        self.version = "2026.1.0"
        
    def list_tools(self) -> List[Dict[str, Any]]:
        """Trả về danh sách các Tools chuẩn giao thức MCP"""
        return TOOLS_SCHEMA
        
    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Thực thi request gọi Tool theo chuẩn MCP JSON-RPC 2.0.
        """
        raw_result = dispatch_tool_call(tool_name, arguments)

        try:
            payload = json.loads(raw_result)
        except (TypeError, json.JSONDecodeError):
            payload = {
                "status": "INVALID_RESPONSE",
                "error": "Tool trả về dữ liệu không hợp lệ",
                "raw": raw_result,
            }

        return {
            "jsonrpc": "2.0",
            "server": self.server_name,
            "tool": tool_name,
            "result": payload,
        }


if __name__ == "__main__":
    print("==========================================================")
    print("🔌 KIỂM THỬ ĐỘC LẬP MCP SERVER (vinuni-academic-mcp-server)")
    print("==========================================================")
    
    server = MCPLibraryServer()
    tools = server.list_tools()
    print(f"✅ Khởi tạo thành công MCP Server: {server.server_name} (Version: {server.version})")
    print(f"📦 Số lượng Tools công bố: {len(tools)}")
    
    # Kiểm tra trạng thái Tool Schema theo chủ đề thư viện
    library_tool = next((t for t in tools if t.get("name") == "library_search"), None)
    reserve_tool = next((t for t in tools if t.get("name") == "reserve_book"), None)

    if library_tool and library_tool.get("parameters", {}).get("properties"):
        print("✅ [TODO 1.2]: Tool 'library_search' đã có schema đầy đủ.")
    else:
        print("⏳ [TODO 1.2]: Tool 'library_search' chưa được định nghĩa đúng trong 'src/tools.py'.")

    if reserve_tool and reserve_tool.get("parameters", {}).get("properties"):
        print("✅ [TODO 1.2]: Tool 'reserve_book' đã có schema đầy đủ.")
    else:
        print("⏳ [TODO 1.2]: Tool 'reserve_book' chưa được định nghĩa đúng trong 'src/tools.py'.")

    # Kiểm tra trạng thái TODO 2.1 (call_tool) theo chủ đề thư viện
    test_result = server.call_tool("library_search", {"book_code": "DB101"})
    if not test_result:
        print("⏳ [TODO 2.1]: Hàm call_tool() đang trả về rỗng. Học viên hãy hoàn thiện TODO 2.1 trong 'src/mcp_server.py'!")
    else:
        print("✅ [TODO 2.1]: Test dispatch tool 'library_search' thành công:")
        print(f"   Phản hồi JSON-RPC: {json.dumps(test_result, ensure_ascii=False)}")
