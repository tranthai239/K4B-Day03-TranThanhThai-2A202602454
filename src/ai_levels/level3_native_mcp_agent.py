"""
📚 [REFERENCE ONLY / CODE MẪU THAM KHẢO]
🧠 CẤP ĐỘ 3: NATIVE MCP AGENT (Native Tool Calling + MCP Server Integration)
⚠️ Lưu ý: File này chỉ dùng để đọc tham khảo kiến trúc. Không chỉnh sửa hay debug file này.
"""

import json

def get_weather(city: str) -> str:
    return f"Thời tiết {city}: 28°C, Nắng nhẹ."

def run_level3_demo():
    print("=== DEMO CẤP ĐỘ 3: NATIVE MCP AGENT ===")
    user_goal = "Tra cứu thông tin sách trong thư viện VinUni"
    print(f"🎯 Goal: {user_goal}")
    print("🧠 [Thought]: Phát sinh Native Tool Call 'library_search'...")
    print("🛠️ [Native Tool Call]: library_search({'book_code': 'DB101'})")
    print("👁️ [MCP Server Observation]: {'status': 'SUCCESS', 'book_code': 'DB101', 'data': {'title': 'Database Systems', 'location': 'Tầng 2 - Khu A'}}")
    print("🏁 [Final Answer]: Sách Database Systems (DB101) đang ở Tầng 2 - Khu A.")

if __name__ == "__main__":
    run_level3_demo()
