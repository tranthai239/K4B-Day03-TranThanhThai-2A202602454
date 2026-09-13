"""
🔌 MULTI-PROVIDER LLM ADAPTER (Google Gemini, OpenAI & Offline Mock)
Hỗ trợ Native Tool Calling và chuyển đổi linh hoạt qua biến môi trường LLM_PROVIDER.
"""

import os
import sys
import json
import re
from typing import Dict, Any, List
from dotenv import load_dotenv

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

load_dotenv()

# Các chế độ thực thi được ghi vào trace để phân biệt nguồn gốc câu trả lời.
MODE_STATIC = "static_response"
MODE_FAST_PATH = "mcp_fast_path"
MODE_LIVE_LLM = "live_llm"
MODE_MOCK = "mock"

# Từ khoá nghiệp vụ cần đi qua LLM thật (ReAct loop).
ACTION_KEYWORDS = [
    "mượn", "trả", "gia hạn", "đặt trước", "đặt chỗ",
    "borrow", "return", "extend", "reserve",
]


def _tag(mode: str, provider_name: str, model_name: str, result: Dict[str, Any], resolved_tool: str = None) -> Dict[str, Any]:
    """Gắn metadata execution_mode/provider/model vào một result đã chuẩn hoá."""
    result["execution_mode"] = mode
    result["provider"] = provider_name
    result["model"] = model_name
    if resolved_tool:
        result["resolved_tool"] = resolved_tool
    return result


def _static(content: str, thought: str) -> Dict[str, Any]:
    return _tag(MODE_STATIC, "local", "static", {
        "type": "text",
        "content": content,
        "thought": thought,
    })


def _fastpath(tool_name: str, arguments: Dict[str, Any], thought: str) -> Dict[str, Any]:
    return _tag(MODE_FAST_PATH, "local", "mcp_fast_path", {
        "type": "tool_call",
        "tool_name": tool_name,
        "arguments": arguments,
        "thought": thought,
    }, resolved_tool=tool_name)


def _live(tag: Dict[str, Any], provider_name: str, model_name: str) -> Dict[str, Any]:
    return _tag(MODE_LIVE_LLM, provider_name, model_name, tag)


def _error(content: str) -> Dict[str, Any]:
    return {
        "type": "error",
        "content": content,
        "thought": "Không thể hoàn tất bước suy luận vì lỗi kết nối LLM.",
        "execution_mode": MODE_LIVE_LLM,
        "provider": "error",
        "model": "error",
        "resolved_tool": None,
    }


class BaseLLMProvider:
    """Interface cơ sở cho các LLM Provider hỗ trợ Native Tool Calling"""
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        raise NotImplementedError

    def generate_with_tools(self, prompt: str, tools_schema: List[Dict[str, Any]], system_prompt: str = "", history: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        raise NotImplementedError


class MockOfflineProvider(BaseLLMProvider):
    """Offline Mock Provider dùng để chạy thử mà không tốn API Key"""
    def __init__(self):
        self.model_name = "Offline-Mock-Model-2026"

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        return f"[Mock Chatbot Response]: Xin chào! Tôi đã nhận được câu hỏi '{prompt}'. (Chế độ Chatbot không có Tool tra cứu dữ liệu thời gian thực)."

    def generate_with_tools(self, prompt: str, tools_schema: List[Dict[str, Any]], system_prompt: str = "", history: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        prompt_lower = prompt.lower()
        student_match = re.search(r"\bA\d{3}\b", prompt.upper())
        student_id = student_match.group(0) if student_match else "A001"

        book_match = re.search(r"\b(DB101|AI205|CS440)\b", prompt.upper())
        if book_match:
            requested_book = book_match.group(1)
        elif "database systems" in prompt_lower or "database" in prompt_lower:
            requested_book = "DB101"
        elif "computer networks" in prompt_lower:
            requested_book = "CS440"
        elif "artificial intelligence" in prompt_lower:
            requested_book = "AI205"
        else:
            requested_book = "AI205"

        result = None

        if ("mã sinh viên" in prompt_lower or "student_id" in prompt_lower) and not student_match:
            result = {
                "type": "text",
                "content": "Vui lòng nhập mã sinh viên để kiểm tra trạng thái mượn/trả và xử lý yêu cầu thư viện.",
                "thought": "Người dùng cần xác định mã sinh viên trước khi kiểm tra trạng thái hoặc thực hiện nghiệp vụ thư viện."
            }

        if result is None and any(phrase in prompt_lower for phrase in ["có những cuốn sách", "có những sách", "có sách gì", "thư viện có sách", "danh sách sách", "liệt kê sách", "tất cả sách", "toàn bộ sách"]):
            result = {
                "type": "tool_call",
                "tool_name": "library_search",
                "arguments": {"book_code": "__ALL__"},
                "thought": "Người dùng muốn xem danh mục sách của thư viện. Tôi sẽ gọi library_search để lấy toàn bộ danh sách sách."
            }

        if result is None and "theo tên" in prompt_lower:
            result = {
                "type": "tool_call",
                "tool_name": "library_search",
                "arguments": {"book_code": prompt},
                "thought": "Người dùng muốn tra cứu sách theo tên. Tôi sẽ gọi library_search để tìm trong tên tài liệu."
            }

        if result is None and any(phrase in prompt_lower for phrase in ["quy định", "quy chế", "giới thiệu", "chào bạn"]):
            result = {
                "type": "text",
                "content": "Thư viện VinUni cho phép sinh viên tra cứu tài liệu, mượn sách còn sẵn, trả sách đang mượn, gia hạn trong thời hạn cho phép và đặt trước sách đang được mượn.",
                "thought": "Đây là câu hỏi chung về quy định thư viện, có thể trả lời trực tiếp mà không cần dữ liệu thời gian thực."
            }

        if result is None and "zz999" in prompt_lower:
            result = {
                "type": "tool_call",
                "tool_name": "library_search",
                "arguments": {"book_code": "ZZ999"},
                "thought": "Người dùng yêu cầu tìm mã sách ZZ999. Tôi sẽ gọi library_search để xác nhận sách có tồn tại hay không."
            }

        if result is None:
            action_requested = any(keyword in prompt_lower for keyword in ACTION_KEYWORDS)
            if action_requested and not student_match:
                result = {
                    "type": "text",
                    "content": "Vui lòng nhập mã sinh viên trước khi thực hiện yêu cầu này.",
                    "thought": "Yêu cầu nghiệp vụ cần có mã sinh viên đã được xác thực trước khi gọi tool."
                }

        if result is None and student_match and not any(keyword in prompt_lower for keyword in ACTION_KEYWORDS):
            result = {
                "type": "tool_call",
                "tool_name": "get_student_status",
                "arguments": {"student_id": student_id},
                "thought": f"Người dùng đã nhập mã sinh viên {student_id}. Tôi sẽ gọi get_student_status để kiểm tra sinh viên và hiển thị thông tin mượn/trả."
            }

        if result is None and ("trả sách" in prompt_lower or "return" in prompt_lower):
            result = {
                "type": "tool_call",
                "tool_name": "return_book",
                "arguments": {"student_id": student_id, "book_code": requested_book},
                "thought": f"Người dùng yêu cầu trả sách. Tôi sẽ gọi tool return_book cho sinh viên {student_id}."
            }

        if result is None and ("gia hạn" in prompt_lower or "extend" in prompt_lower):
            result = {
                "type": "tool_call",
                "tool_name": "extend_loan",
                "arguments": {"student_id": student_id, "book_code": requested_book, "days": 7},
                "thought": "Người dùng yêu cầu gia hạn mượn sách. Tôi sẽ gọi tool extend_loan với thời gian gia hạn 7 ngày."
            }

        if result is None and ("đặt trước" in prompt_lower or "reserve" in prompt_lower or "đặt chỗ" in prompt_lower):
            result = {
                "type": "tool_call",
                "tool_name": "reserve_book",
                "arguments": {"student_id": student_id, "book_code": "AI205" if "ai205" in prompt_lower or "artificial intelligence" in prompt_lower else "DB101" if "db101" in prompt_lower or "database systems" in prompt_lower else "AI205"},
                "thought": f"Người dùng muốn đặt trước sách. Tôi sẽ gọi tool reserve_book cho sinh viên {student_id}."
            }

        if result is None and ("mượn sách" in prompt_lower or "borrow" in prompt_lower):
            result = {
                "type": "tool_call",
                "tool_name": "borrow_book",
                "arguments": {"student_id": student_id, "book_code": "CS440" if "cs440" in prompt_lower or "computer networks" in prompt_lower else "DB101" if "db101" in prompt_lower or "database systems" in prompt_lower else "AI205"},
                "thought": "Người dùng yêu cầu mượn sách. Tôi sẽ gọi tool borrow_book với mã sách phù hợp."
            }

        if result is None and ("trạng thái" in prompt_lower or "đang mượn" in prompt_lower or "đặt trước" in prompt_lower or "có đang mượn" in prompt_lower or "hiển thị" in prompt_lower):
            result = {
                "type": "tool_call",
                "tool_name": "get_student_status",
                "arguments": {"student_id": student_id},
                "thought": "Người dùng yêu cầu xem trạng thái sinh viên. Tôi sẽ gọi tool get_student_status để hiển thị sách đang mượn và đặt trước."
            }

        if result is None and ("có thể mượn" in prompt_lower or "còn có thể mượn" in prompt_lower or "sẵn" in prompt_lower or "trạng thái" in prompt_lower):
            if "database systems" in prompt_lower or "db101" in prompt_lower:
                result = {
                    "type": "tool_call",
                    "tool_name": "library_search",
                    "arguments": {"book_code": "DB101"},
                    "thought": "Người dùng hỏi tình trạng mượn của sách cụ thể. Tôi sẽ kiểm tra bằng tool library_search để xác định trạng thái hiện tại."
                }
            elif "artificial intelligence" in prompt_lower or "ai205" in prompt_lower:
                result = {
                    "type": "tool_call",
                    "tool_name": "library_search",
                    "arguments": {"book_code": "AI205"},
                    "thought": "Người dùng đang kiểm tra khả năng mượn của sách cụ thể. Tôi sẽ gọi tool library_search để đọc trạng thái thực tế."
                }

        if result is None and ("db101" in prompt_lower or "database systems" in prompt_lower or "cs440" in prompt_lower or "computer networks" in prompt_lower or ("tra cứu" in prompt_lower and "sách" in prompt_lower) or ("tìm" in prompt_lower and "sách" in prompt_lower)):
            result = {
                "type": "tool_call",
                "tool_name": "library_search",
                "arguments": {"book_code": "CS440" if "cs440" in prompt_lower or "computer networks" in prompt_lower else "DB101"},
                "thought": "Người dùng muốn tra cứu thông tin sách trong thư viện. Tôi sẽ gọi tool library_search theo mã hoặc tên sách được cung cấp."
            }

        if result is None and ("ai205" in prompt_lower or "artificial intelligence" in prompt_lower or "zz999" in prompt_lower):
            result = {
                "type": "tool_call",
                "tool_name": "library_search",
                "arguments": {"book_code": "AI205" if "ai205" in prompt_lower or "artificial intelligence" in prompt_lower else "ZZ999"},
                "thought": "Người dùng đang kiểm tra tình trạng sách cụ thể. Tôi sẽ gọi tool library_search cho mã sách phù hợp."
            }

        if result is None:
            result = {
                "type": "text",
                "content": "[Mock Agent Response]: Thư viện VinUni hỗ trợ bạn tra cứu sách, kiểm tra trạng thái sinh viên, mượn, trả, đặt trước và gia hạn theo quy định tài liệu.",
                "thought": "Câu hỏi chung về thư viện, không cần gọi Tool."
            }

        return _tag(MODE_MOCK, "mock", self.model_name, result)


class HybridProvider(BaseLLMProvider):
    """Kết hợp đường xử lý nhanh (local/MCP) và LLM API cho nghiệp vụ cần suy luận."""
    def __init__(self, api_provider: BaseLLMProvider):
        self.api_provider = api_provider
        self.script_provider = MockOfflineProvider()
        self.model_name = f"Hybrid({api_provider.model_name})"
        self.provider_name = api_provider.__class__.__name__

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        return self.api_provider.generate(prompt, system_prompt)

    @staticmethod
    def _is_action_query(prompt_lower: str) -> bool:
        return any(keyword in prompt_lower for keyword in ACTION_KEYWORDS)

    @staticmethod
    def _catalog_phrases():
        return ["có những cuốn sách", "có những sách", "có sách gì", "thư viện có sách",
                "danh sách sách", "liệt kê sách", "tất cả sách", "toàn bộ sách"]

    def generate_with_tools(self, prompt: str, tools_schema: List[Dict[str, Any]], system_prompt: str = "", history: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        prompt_lower = prompt.lower()

        # Đang ở giữa vòng ReAct (đã có Observation) -> phải gọi LLM thật để suy luận tiếp.
        if history and history[-1].get("role") == "tool":
            return self._live_call(prompt, tools_schema, system_prompt, history)

        student_match = re.search(r"\bA\d{3}\b", prompt.upper())

        # 1) Static response: câu hỏi chung về quy định / chào hỏi.
        if any(phrase in prompt_lower for phrase in ["quy định", "quy chế", "giới thiệu"]):
            return _static(
                "Thư viện VinUni cho phép sinh viên tra cứu tài liệu, mượn sách còn sẵn, trả sách đang mượn, gia hạn trong thời hạn cho phép và đặt trước sách đang được mượn.",
                "Câu hỏi chung về quy định thư viện, trả lời trực tiếp không cần dữ liệu thời gian thực."
            )

        # 2) Fast path: liệt kê toàn bộ danh mục sách.
        if any(phrase in prompt_lower for phrase in self._catalog_phrases()):
            return _fastpath("library_search", {"book_code": "__ALL__"},
                             "Người dùng muốn xem danh mục sách, gọi library_search để lấy toàn bộ danh sách.")

        # 3) Fast path: tra cứu theo mã/tên sách.
        book_code = None
        if "zz999" in prompt_lower:
            book_code = "ZZ999"
        elif "ai205" in prompt_lower or "artificial intelligence" in prompt_lower:
            book_code = "AI205"
        elif "db101" in prompt_lower or "database systems" in prompt_lower or "database" in prompt_lower:
            book_code = "DB101"
        elif "cs440" in prompt_lower or "computer networks" in prompt_lower:
            book_code = "CS440"
        elif "theo tên" in prompt_lower:
            book_code = prompt
        elif ("tra cứu" in prompt_lower and "sách" in prompt_lower) or ("tìm" in prompt_lower and "sách" in prompt_lower):
            book_code = prompt

        if book_code and not self._is_action_query(prompt_lower):
            return _fastpath("library_search", {"book_code": book_code},
                             "Người dùng muốn tra cứu thông tin sách, gọi library_search theo mã/tên được cung cấp.")

        # 4) Fast path: xem trạng thái sinh viên khi đã có mã và KHÔNG kèm nghiệp vụ.
        if student_match and not self._is_action_query(prompt_lower):
            return _fastpath("get_student_status", {"student_id": student_match.group(0)},
                             "Người dùng đã cung cấp mã sinh viên, gọi get_student_status để hiển thị thông tin mượn/trả.")

        # 5) Còn lại (nghiệp vụ, đa bước, hoặc không rõ ý định) -> LLM thật.
        return self._live_call(prompt, tools_schema, system_prompt, history)

    def _live_call(self, prompt: str, tools_schema: List[Dict[str, Any]], system_prompt: str, history: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        tag = self.api_provider.generate_with_tools(prompt, tools_schema, system_prompt, history)
        # Không gắn live_llm cho kết quả error (đã có metadata riêng).
        if tag.get("type") == "error":
            return tag
        return _live(tag, self.provider_name, self.api_provider.model_name)


def _history_to_gemini_contents(prompt: str, history: List[Dict[str, Any]], types):
    """Chuyển lịch sử ReAct về dạng Parts cho Gemini native function calling."""
    parts = [types.Part(text=prompt)]
    for item in history or []:
        role = item.get("role")
        if role == "user":
            parts.append(types.Part(text=item.get("content", "")))
        elif role == "assistant":
            if item.get("tool_name"):
                parts.append(types.Part(function_call=types.FunctionCall(
                    name=item.get("tool_name"),
                    args=item.get("arguments", {}),
                )))
            elif item.get("content"):
                parts.append(types.Part(text=item.get("content", "")))
        elif role == "tool":
            response = item.get("observation", {})
            parts.append(types.Part(function_response=types.FunctionResponse(
                name=item.get("tool_name", ""),
                response=response,
            )))
    return parts


def _history_to_openai_messages(prompt: str, history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Chuyển lịch sử ReAct về dạng messages cho OpenAI native function calling."""
    messages = [{"role": "user", "content": prompt}]
    for item in history or []:
        role = item.get("role")
        if role == "user":
            messages.append({"role": "user", "content": item.get("content", "")})
        elif role == "assistant":
            if item.get("tool_name"):
                messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": f"call_{len(messages)}",
                        "type": "function",
                        "function": {
                            "name": item.get("tool_name"),
                            "arguments": json.dumps(item.get("arguments", {}), ensure_ascii=False),
                        },
                    }],
                })
            else:
                messages.append({"role": "assistant", "content": item.get("content", "")})
        elif role == "tool":
            messages.append({
                "role": "tool",
                "tool_call_id": f"call_{len(messages) - 1}",
                "content": json.dumps(item.get("observation", {}), ensure_ascii=False),
            })
    return messages


class GeminiProvider(BaseLLMProvider):
    """Google Gemini Provider (Native Tool Calling với Google GenAI SDK)"""
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model or os.getenv("LLM_MODEL") or "gemini-2.5-flash"

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            return "[Gemini Error]: Chưa cấu hình GEMINI_API_KEY trong file .env! Đang sử dụng chế độ Mock."
        try:
            from google import genai
            client = genai.Client(api_key=self.api_key)
            contents = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            response = client.models.generate_content(model=self.model_name, contents=contents)
            return response.text
        except Exception as e:
            return f"[Gemini Exception]: {str(e)}"

    def generate_with_tools(self, prompt: str, tools_schema: List[Dict[str, Any]], system_prompt: str = "", history: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            print("ℹ️ [Gemini Provider]: Chưa tìm thấy GEMINI_API_KEY hợp lệ. Tự động chuyển sang Mock Offline.")
            return MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt, history)

        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.api_key)

            # Chuẩn hóa function declarations cho Gemini SDK
            function_declarations = []
            for tool in tools_schema:
                # Bỏ qua các tool schema chưa được định nghĩa hoàn chỉnh
                if not tool.get("name") or not tool.get("parameters"):
                    continue
                function_declarations.append({
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("parameters", {})
                })

            config = types.GenerateContentConfig(
                system_instruction=system_prompt if system_prompt else None,
                tools=[{"function_declarations": function_declarations}] if function_declarations else None,
                temperature=0.2
            )

            contents = _history_to_gemini_contents(prompt, history, types) if history else prompt
            response = client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=config
            )

            # Kiểm tra xem Gemini có trả về Tool Call không
            if response.function_calls:
                call = response.function_calls[0]
                args = dict(call.args) if hasattr(call, 'args') and call.args else {}
                return {
                    "type": "tool_call",
                    "tool_name": call.name,
                    "arguments": args,
                    "thought": f"Gemini quyết định gọi công cụ '{call.name}' với tham số: {json.dumps(args, ensure_ascii=False)}"
                }
            else:
                return {
                    "type": "text",
                    "content": response.text or "",
                    "thought": "Gemini phản hồi trực tiếp bằng văn bản (không cần gọi công cụ)."
                }

        except Exception as e:
            print(f"⚠️ [Gemini API Error]: {str(e)}")
            return _error(str(e))


class OpenAIProvider(BaseLLMProvider):
    """OpenAI Provider (Native Tool Calling với OpenAI SDK)"""
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model_name = model or os.getenv("LLM_MODEL") or "gpt-4o-mini"

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not self.api_key or self.api_key == "your_openai_api_key_here":
            return "[OpenAI Error]: Chưa cấu hình OPENAI_API_KEY trong file .env! Đang sử dụng chế độ Mock."
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            response = client.chat.completions.create(model=self.model_name, messages=messages)
            return response.choices[0].message.content or ""
        except Exception as e:
            return f"[OpenAI Exception]: {str(e)}"

    def generate_with_tools(self, prompt: str, tools_schema: List[Dict[str, Any]], system_prompt: str = "", history: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not self.api_key or self.api_key == "your_openai_api_key_here":
            print("ℹ️ [OpenAI Provider]: Chưa tìm thấy OPENAI_API_KEY hợp lệ. Tự động chuyển sang Mock Offline.")
            return MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt, history)

        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)

            tools = []
            for tool in tools_schema:
                if not tool.get("name"):
                    continue
                tools.append({
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool.get("description", ""),
                        "parameters": tool.get("parameters", {})
                    }
                })

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.extend(_history_to_openai_messages(prompt, history))

            response = client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                tools=tools if tools else None,
                tool_choice="auto" if tools else None
            )

            msg = response.choices[0].message
            if msg.tool_calls:
                call = msg.tool_calls[0]
                args = json.loads(call.function.arguments) if call.function.arguments else {}
                return {
                    "type": "tool_call",
                    "tool_name": call.function.name,
                    "arguments": args,
                    "thought": f"OpenAI quyết định gọi công cụ '{call.function.name}' với tham số: {json.dumps(args, ensure_ascii=False)}"
                }
            else:
                return {
                    "type": "text",
                    "content": msg.content or "",
                    "thought": "OpenAI phản hồi trực tiếp bằng văn bản (không cần gọi công cụ)."
                }
        except Exception as e:
            print(f"⚠️ [OpenAI API Error]: {str(e)}")
            return _error(str(e))


def get_llm_provider() -> BaseLLMProvider:
    """Factory function khởi tạo Provider theo LLM_PROVIDER env variable"""
    provider_type = os.getenv("LLM_PROVIDER", "gemini").lower()

    if provider_type == "gemini":
        key = os.getenv("GEMINI_API_KEY")
        if key and key != "your_gemini_api_key_here":
            return HybridProvider(GeminiProvider())
        else:
            return MockOfflineProvider()
    elif provider_type == "openai":
        key = os.getenv("OPENAI_API_KEY")
        if key and key != "your_openai_api_key_here":
            return HybridProvider(OpenAIProvider())
        else:
            return MockOfflineProvider()
    elif provider_type == "mock":
        return MockOfflineProvider()
    else:
        return MockOfflineProvider()
