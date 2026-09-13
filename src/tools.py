"""
🛠️ TOOL DEFINITIONS & EXECUTION BACKEND
Mã nguồn chứa danh sách Tool Schemas (JSON Schema) và Execution Layer phục vụ cho MCP Server.
"""

import json
from datetime import date, timedelta
from typing import Dict, Any

# ==============================================================================
# 1. KHAI BÁO TOOL SCHEMAS CHUẨN NATIVE JSON SCHEMA (TASK 1.2)
# ==============================================================================

TOOLS_SCHEMA = [
    {
        "name": "library_search",
        "description": "Tra cứu thông tin sách, tình trạng mượn/trả và vị trí tài liệu trong thư viện VinUni.",
        "parameters": {
            "type": "object",
            "properties": {
                "book_code": {
                    "type": "string",
                    "description": "Mã sách, tên sách hoặc yêu cầu liệt kê toàn bộ sách cần tra cứu (ví dụ: 'DB101', 'Database Systems' hoặc '__ALL__')"
                }
            },
            "required": ["book_code"]
        }
    },
    {
        "name": "get_student_status",
        "description": "Hiển thị thông tin trạng thái sinh viên: sách đang mượn, sách đặt trước, thời hạn và các yêu cầu đang chờ xử lý.",
        "parameters": {
            "type": "object",
            "properties": {
                "student_id": {
                    "type": "string",
                    "description": "Mã sinh viên cần kiểm tra trạng thái (ví dụ: 'A001')"
                }
            },
            "required": ["student_id"]
        }
    },
    {
        "name": "borrow_book",
        "description": "Mượn sách nếu sách còn sẵn và sinh viên đủ điều kiện. Nếu đã mượn, trả về thông báo trạng thái hiện tại.",
        "parameters": {
            "type": "object",
            "properties": {
                "student_id": {
                    "type": "string",
                    "description": "Mã sinh viên muốn mượn"
                },
                "book_code": {
                    "type": "string",
                    "description": "Mã sách cần mượn"
                }
            },
            "required": ["student_id", "book_code"]
        }
    },
    {
        "name": "return_book",
        "description": "Trả sách đã mượn và cập nhật trạng thái tài liệu trong thư viện.",
        "parameters": {
            "type": "object",
            "properties": {
                "student_id": {
                    "type": "string",
                    "description": "Mã sinh viên trả sách"
                },
                "book_code": {
                    "type": "string",
                    "description": "Mã sách cần trả"
                }
            },
            "required": ["student_id", "book_code"]
        }
    },
    {
        "name": "reserve_book",
        "description": "Đặt chỗ mượn sách khi sách đang được người khác mượn hoặc đang ở trạng thái chờ xử lý.",
        "parameters": {
            "type": "object",
            "properties": {
                "student_id": {
                    "type": "string",
                    "description": "Mã sinh viên đặt chỗ (ví dụ: 'A001')"
                },
                "book_code": {
                    "type": "string",
                    "description": "Mã sách cần đặt chỗ"
                }
            },
            "required": ["student_id", "book_code"]
        }
    },
    {
        "name": "extend_loan",
        "description": "Gia hạn thời gian mượn sách nếu tài liệu vẫn còn trong giới hạn cho phép gia hạn.",
        "parameters": {
            "type": "object",
            "properties": {
                "student_id": {
                    "type": "string",
                    "description": "Mã sinh viên cần gia hạn"
                },
                "book_code": {
                    "type": "string",
                    "description": "Mã sách cần gia hạn"
                },
                "days": {
                    "type": "integer",
                    "description": "Số ngày muốn gia hạn (ví dụ: 7)"
                }
            },
            "required": ["student_id", "book_code", "days"]
        }
    }
]

# ==============================================================================
# 2. MÔ PHỎNG DỮ LIỆU & HÀM THỰC THI TOOL (EXECUTION LAYER)
# ==============================================================================

BOOK_LIBRARY = {
    "DB101": {
        "book_code": "DB101",
        "title": "Database Systems",
        "status": "AVAILABLE",
        "location": "Tầng 2 - Khu A",
        "borrower": None,
        "due_date": None,
        "available_copies": 3
    },
    "AI205": {
        "book_code": "AI205",
        "title": "Artificial Intelligence Foundations",
        "status": "BORROWED",
        "location": "Tầng 3 - Khu B",
        "borrower": "A001",
        "due_date": "2026-09-20",
        "available_copies": 0
    },
    "CS440": {
        "book_code": "CS440",
        "title": "Computer Networks",
        "status": "AVAILABLE",
        "location": "Tầng 1 - Khu C",
        "borrower": None,
        "due_date": None,
        "available_copies": 2
    }
}

STUDENT_LIBRARY_STATE = {
    "A001": {
        "borrowed_books": ["AI205"],
        "reserved_books": ["DB101"],
        "loan_history": [
            {"book_code": "AI205", "status": "BORROWED", "due_date": "2026-09-20"}
        ]
    },
    "A002": {
        "borrowed_books": [],
        "reserved_books": [],
        "loan_history": []
    },
    "A003": {
        "borrowed_books": [],
        "reserved_books": [],
        "loan_history": []
    },
    "A004": {
        "borrowed_books": [],
        "reserved_books": [],
        "loan_history": []
    },
    "A005": {
        "borrowed_books": [],
        "reserved_books": [],
        "loan_history": []
    }
}


def _resolve_book(identifier: str):
    """Trả về dict sách theo mã hoặc tên sách (không phân biệt hoa thường), hoặc None nếu không tìm thấy."""
    normalized = identifier.strip().upper()

    # Ưu tiên khớp đúng theo mã sách (nhanh và chính xác).
    if normalized in BOOK_LIBRARY:
        return BOOK_LIBRARY[normalized]

    # Khớp theo tên sách (chứa lẫn nhau) giống library_search.
    for item in BOOK_LIBRARY.values():
        title = item["title"].upper()
        if title == normalized or title in normalized or normalized in title:
            return item

    return None


def execute_library_search(book_code: str) -> str:
    """Tra cứu thông tin sách trong thư viện theo mã hoặc tên sách"""
    normalized = book_code.strip().upper()

    if normalized in {"__ALL__", "ALL", "DANH SACH", "DANH SÁCH"}:
        return json.dumps({
            "status": "SUCCESS",
            "total_books": len(BOOK_LIBRARY),
            "data": list(BOOK_LIBRARY.values())
        }, ensure_ascii=False)

    book = None

    for item in BOOK_LIBRARY.values():
        title = item["title"].upper()
        if item["book_code"] == normalized or title == normalized or title in normalized or normalized in title:
            book = item
            break

    if book:
        return json.dumps({
            "status": "SUCCESS",
            "book_code": book["book_code"],
            "data": book
        }, ensure_ascii=False)
    else:
        return json.dumps({
            "status": "NOT_FOUND",
            "message": f"Không tìm thấy sách có mã hoặc tên '{book_code}' trong thư viện."
        }, ensure_ascii=False)


def execute_get_student_status(student_id: str) -> str:
    """Hiển thị toàn bộ trạng thái tài liệu của sinh viên."""
    normalized_student_id = student_id.strip().upper()
    student_state = STUDENT_LIBRARY_STATE.get(normalized_student_id)

    if student_state is None:
        return json.dumps({
            "status": "NOT_FOUND",
            "student_id": normalized_student_id,
            "message": f"Không có sinh viên nào tồn tại với mã '{normalized_student_id}'."
        }, ensure_ascii=False)

    loan_history = student_state.get("loan_history", [])
    overdue_books = [
        loan["book_code"]
        for loan in loan_history
        if loan.get("status") == "BORROWED"
        and loan.get("due_date")
        and date.fromisoformat(loan["due_date"]) < date.today()
    ]

    def book_titles(book_codes):
        return [
            BOOK_LIBRARY[book_code]["title"]
            for book_code in book_codes
            if book_code in BOOK_LIBRARY
        ]

    borrowed_titles = book_titles(student_state.get("borrowed_books", []))
    reserved_titles = book_titles(student_state.get("reserved_books", []))
    overdue_titles = book_titles(overdue_books)

    borrowed_text = ", ".join(borrowed_titles) if borrowed_titles else "Không có"
    reserved_text = ", ".join(reserved_titles) if reserved_titles else "Không có"
    overdue_text = ", ".join(overdue_titles) if overdue_titles else "Không có"

    return json.dumps({
        "status": "SUCCESS",
        "student_id": normalized_student_id,
        "borrowed_books": student_state.get("borrowed_books", []),
        "reserved_books": student_state.get("reserved_books", []),
        "loan_history": loan_history,
        "overdue_books": overdue_books,
        "message": (
            f"Sinh viên {normalized_student_id}:\n"
            f"- Đang mượn ({len(borrowed_titles)}): {borrowed_text}\n"
            f"- Đặt trước ({len(reserved_titles)}): {reserved_text}\n"
            f"- Quá hạn ({len(overdue_titles)}): {overdue_text}"
        )
    }, ensure_ascii=False)


def execute_borrow_book(student_id: str, book_code: str) -> str:
    """Sinh viên mượn sách nếu tài liệu còn sẵn."""
    normalized_student_id = student_id.strip().upper()
    normalized_book_code = book_code.strip().upper()
    student_state = STUDENT_LIBRARY_STATE.get(normalized_student_id)
    if student_state is None:
        return json.dumps({
            "status": "NOT_FOUND",
            "student_id": normalized_student_id,
            "message": f"Không có sinh viên nào tồn tại với mã '{normalized_student_id}'."
        }, ensure_ascii=False)

    book = _resolve_book(book_code)
    if not book:
        return json.dumps({
            "status": "NOT_FOUND",
            "message": f"Không tìm thấy sách '{book_code}' để mượn."
        }, ensure_ascii=False)
    normalized_book_code = book["book_code"]

    if normalized_book_code in student_state.get("borrowed_books", []):
        return json.dumps({
            "status": "SUCCESS",
            "student_id": normalized_student_id,
            "book_code": normalized_book_code,
            "message": f"Sinh viên {normalized_student_id} đang mượn sách {book['title']}."
        }, ensure_ascii=False)

    if book["status"] == "AVAILABLE" and book.get("available_copies", 0) > 0:
        book["available_copies"] -= 1
        book["status"] = "AVAILABLE" if book["available_copies"] else "BORROWED"
        book["borrower"] = normalized_student_id if book["available_copies"] == 0 else None
        book["due_date"] = "2026-10-05" if book["available_copies"] == 0 else None
        student_state["borrowed_books"].append(normalized_book_code)
        student_state["loan_history"].append({
            "book_code": normalized_book_code,
            "status": "BORROWED",
            "due_date": "2026-10-05"
        })
        return json.dumps({
            "status": "SUCCESS",
            "student_id": normalized_student_id,
            "book_code": normalized_book_code,
            "message": f"Sinh viên {normalized_student_id} đã mượn thành công sách {book['title']}."
        }, ensure_ascii=False)

    return json.dumps({
        "status": "SUCCESS",
        "student_id": normalized_student_id,
        "book_code": normalized_book_code,
        "message": f"Sách {book['title']} hiện không còn sẵn để mượn. Hệ thống đã giữ trạng thái hiện tại cho sinh viên {normalized_student_id}."
    }, ensure_ascii=False)


def execute_return_book(student_id: str, book_code: str) -> str:
    """Sinh viên trả sách đã mượn."""
    normalized_student_id = student_id.strip().upper()
    normalized_book_code = book_code.strip().upper()
    student_state = STUDENT_LIBRARY_STATE.get(normalized_student_id)
    if student_state is None:
        return json.dumps({
            "status": "NOT_FOUND",
            "student_id": normalized_student_id,
            "message": f"Không có sinh viên nào tồn tại với mã '{normalized_student_id}'."
        }, ensure_ascii=False)

    book = _resolve_book(book_code)
    if not book:
        return json.dumps({
            "status": "NOT_FOUND",
            "message": f"Không tìm thấy sách '{book_code}' để trả."
        }, ensure_ascii=False)
    normalized_book_code = book["book_code"]

    if normalized_book_code in student_state.get("borrowed_books", []):
        book["available_copies"] = book.get("available_copies", 0) + 1
        book["status"] = "AVAILABLE"
        book["borrower"] = None
        book["due_date"] = None
        student_state["borrowed_books"] = [b for b in student_state["borrowed_books"] if b != normalized_book_code]
        student_state["loan_history"].append({
            "book_code": normalized_book_code,
            "status": "RETURNED",
            "due_date": None
        })
        return json.dumps({
            "status": "SUCCESS",
            "student_id": normalized_student_id,
            "book_code": normalized_book_code,
            "message": f"Sinh viên {normalized_student_id} đã trả thành công sách {book['title']}."
        }, ensure_ascii=False)

    return json.dumps({
        "status": "SUCCESS",
        "student_id": normalized_student_id,
        "book_code": normalized_book_code,
        "message": f"Sinh viên {normalized_student_id} không đang mượn sách {book['title']} nên không cần trả.",
    }, ensure_ascii=False)


def execute_reserve_book(student_id: str, book_code: str) -> str:
    """Đặt chỗ mượn sách"""
    normalized_student_id = student_id.strip().upper()
    normalized_book_code = book_code.strip().upper()
    student_state = STUDENT_LIBRARY_STATE.get(normalized_student_id)
    if student_state is None:
        return json.dumps({
            "status": "NOT_FOUND",
            "student_id": normalized_student_id,
            "message": f"Không có sinh viên nào tồn tại với mã '{normalized_student_id}'."
        }, ensure_ascii=False)

    book = _resolve_book(book_code)
    if not book:
        return json.dumps({
            "status": "NOT_FOUND",
            "message": f"Không tìm thấy sách '{book_code}' để đặt chỗ."
        }, ensure_ascii=False)
    normalized_book_code = book["book_code"]

    if normalized_book_code in student_state.get("reserved_books", []):
        return json.dumps({
            "status": "SUCCESS",
            "student_id": normalized_student_id,
            "book_code": normalized_book_code,
            "message": f"Sinh viên {normalized_student_id} đã đặt trước sách {book['title']} trước đó."
        }, ensure_ascii=False)

    if book["status"] == "AVAILABLE":
        return json.dumps({
            "status": "SUCCESS",
            "student_id": normalized_student_id,
            "book_code": normalized_book_code,
            "message": f"Sách {book['title']} hiện còn sẵn. Sinh viên {normalized_student_id} có thể mượn ngay."
        }, ensure_ascii=False)

    student_state["reserved_books"].append(normalized_book_code)
    return json.dumps({
        "status": "SUCCESS",
        "reservation_id": f"RES-{normalized_student_id}-{normalized_book_code}",
        "student_id": normalized_student_id,
        "book_code": normalized_book_code,
        "message": f"Sách {book['title']} đang được mượn. Hệ thống đã ghi nhận đặt chỗ cho sinh viên {normalized_student_id}."
    }, ensure_ascii=False)


def execute_extend_loan(student_id: str, book_code: str, days: int) -> str:
    """Gia hạn sách"""
    normalized_student_id = student_id.strip().upper()
    normalized_book_code = book_code.strip().upper()
    student_state = STUDENT_LIBRARY_STATE.get(normalized_student_id)
    if student_state is None:
        return json.dumps({
            "status": "NOT_FOUND",
            "student_id": normalized_student_id,
            "message": f"Không có sinh viên nào tồn tại với mã '{normalized_student_id}'."
        }, ensure_ascii=False)

    book = _resolve_book(book_code)
    if not book:
        return json.dumps({
            "status": "NOT_FOUND",
            "message": f"Không tìm thấy sách '{book_code}' để gia hạn."
        }, ensure_ascii=False)
    normalized_book_code = book["book_code"]

    if normalized_book_code not in student_state.get("borrowed_books", []):
        return json.dumps({
            "status": "SUCCESS",
            "student_id": normalized_student_id,
            "book_code": normalized_book_code,
            "message": f"Sinh viên {normalized_student_id} không đang mượn sách {book['title']} nên không thể gia hạn."
        }, ensure_ascii=False)

    active_loan = next(
        (loan for loan in student_state.get("loan_history", [])
         if loan.get("book_code") == normalized_book_code and loan.get("status") == "BORROWED"),
        None
    )
    if active_loan and active_loan.get("due_date"):
        active_loan["due_date"] = (date.fromisoformat(active_loan["due_date"]) + timedelta(days=days)).isoformat()

    return json.dumps({
        "status": "SUCCESS",
        "student_id": normalized_student_id,
        "book_code": normalized_book_code,
        "days_extended": days,
        "new_due_date": active_loan.get("due_date") if active_loan else None,
        "message": f"Đã gia hạn {days} ngày cho sinh viên {normalized_student_id} đối với sách {book['title']}."
    }, ensure_ascii=False)


# Router gọi tool thực tế
TOOL_ROUTER = {
    "library_search": execute_library_search,
    "get_student_status": execute_get_student_status,
    "borrow_book": execute_borrow_book,
    "return_book": execute_return_book,
    "reserve_book": execute_reserve_book,
    "extend_loan": execute_extend_loan
}


def dispatch_tool_call(tool_name: str, arguments: Dict[str, Any]) -> str:
    """Hàm trung chuyển thực thi tool"""
    if tool_name in TOOL_ROUTER:
        try:
            return TOOL_ROUTER[tool_name](**arguments)
        except Exception as e:
            return json.dumps({"status": "EXECUTION_ERROR", "error": str(e)}, ensure_ascii=False)
    return json.dumps({"status": "UNKNOWN_TOOL", "error": f"Tool '{tool_name}' không tồn tại!"}, ensure_ascii=False)
