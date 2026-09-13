# 📊 BÁO CÁO THU HOẠCH NGHIỆM THU BÀI LAB 3 (BƯỚC 3 — SUBMISSION ARTIFACT)

> **Họ và Tên Học viên:** Trần Thanh Thái
>
> **Mã Sinh Viên / Mã Học viên:** 2A202602454
>
> **Chủ đề Lựa chọn:** Trợ lý Quản lý Thư viện & Tài liệu

---

## 1. BẢNG CHẤM ĐIỂM AGENTIC FIT SCORING MATRIX (ĐÁNH GIÁ CHỦ ĐỀ)

| Tiêu chí Đánh giá | Mức độ (1 - 5) | Giải trình chi tiết lý do chọn điểm |
| :--- | :---: | :--- |
| **1. Multi-step Reasoning** | 4 / 5 | Bài toán có nhiều bước nối tiếp: xác định sinh viên, kiểm tra trạng thái mượn/đặt trước, rồi thực hiện hành động mượn/trả/gia hạn/đặt trước. |
| **2. Tool Interaction** | 5 / 5 | Hệ thống cần gọi tool bên ngoài để kiểm tra thông tin sách, trạng thái sinh viên và xử lý nghiệp vụ thư viện. |
| **3. Dynamic Decision** | 4 / 5 | Quyết định phụ thuộc vào trạng thái thực tế: sách còn sẵn hay đã mượn, sinh viên đã mượn hay đặt trước, cần gia hạn hay không. |
| **4. Long Horizon Goal** | 4 / 5 | Hệ thống phải duy trì mục tiêu xuyên suốt nhiều lượt: trạng thái sinh viên → lựa chọn hành động → kết quả thực thi → phản hồi cho người dùng. |
| **TỔNG ĐIỂM AGENTIC FIT** | **17 / 20** | *Nếu tổng điểm > 12/20: Bài toán phù hợp triển khai Agentic System.* |

---

## 2. TRÍCH XUẤT KẾT QUẢ WATERFALL TRACE LOG

> Hệ thống chạy trên **LLM API thật (Gemini)** qua `HybridProvider` với 3 chế độ thực thi: `static_response` (câu quy định trả lời local), `mcp_fast_path` (tra cứu nhanh gọi MCP trực tiếp) và `live_llm` (nghiệp vụ mượn/trả/gia hạn/đặt trước đi qua LLM thật).

Trích từ `docs/trace_waterfall.json` — Test Case TC04 (multi-step ReAct, minh chứng Observation quay lại LLM):

```json
[
  {
    "test_case_id": "TC04",
    "step": 1,
    "action_type": "TOOL_EXECUTION",
    "execution_mode": "live_llm",
    "provider": "GeminiProvider",
    "model": "gemini-2.5-flash",
    "thought": "Gemini quyết định gọi công cụ 'get_student_status' với tham số: {\"student_id\": \"A001\"}",
    "tool_name": "get_student_status",
    "arguments": { "student_id": "A001" },
    "observation": {
      "status": "SUCCESS",
      "student_id": "A001",
      "borrowed_books": ["AI205"],
      "reserved_books": ["DB101", "AI205"],
      "overdue_books": []
    },
    "latency_ms": 2671.41
  },
  {
    "test_case_id": "TC04",
    "step": 2,
    "action_type": "TOOL_EXECUTION",
    "execution_mode": "live_llm",
    "provider": "GeminiProvider",
    "model": "gemini-2.5-flash",
    "thought": "Gemini quyết định gọi công cụ 'extend_loan' với tham số: {\"book_code\": \"AI205\", \"student_id\": \"A001\", \"days\": 7}",
    "tool_name": "extend_loan",
    "arguments": { "book_code": "AI205", "student_id": "A001", "days": 7 },
    "observation": {
      "status": "SUCCESS",
      "days_extended": 7,
      "new_due_date": "2026-09-27",
      "message": "Đã gia hạn 7 ngày cho sinh viên A001 đối với sách Artificial Intelligence Foundations."
    },
    "latency_ms": 2843.82
  },
  {
    "test_case_id": "TC04",
    "step": 3,
    "action_type": "FINAL_ANSWER",
    "execution_mode": "live_llm",
    "provider": "GeminiProvider",
    "model": "gemini-2.5-flash",
    "thought": "Gemini phản hồi trực tiếp bằng văn bản (không cần gọi công cụ).",
    "output": "Sinh viên A001 đang mượn sách AI205 (Artificial Intelligence Foundations) và đã được gia hạn thêm 7 ngày. Ngày trả mới là 2026-09-27.",
    "latency_ms": 2392.38
  }
]
```

Đây là minh chứng cho flow đúng chuẩn ReAct:
1. **Thought** — LLM suy luận cần kiểm tra trạng thái sinh viên trước.
2. **Action** — gọi `get_student_status(A001)`.
3. **Observation** — nhận kết quả `borrowed_books: ["AI205"]`.
4. **Observation quay lại LLM** — LLM quyết định gọi tiếp `extend_loan(A001, AI205, 7)`.
5. **Final Answer** — tổng hợp trả lời người dùng (Anti-Hallucination).

---

## 3. TỔNG KẾT KẾT QUẢ NGHIỆM THU & NỘP BÀI

- **LLM Provider đang dùng:** GeminiProvider (`gemini-2.5-flash`) — LLM API thật
- **Đã chạy Test Suite:** 5/5 test cases PASS (0 error, 0 TODO)
- **Số lượt gọi Tool qua MCP Server:** 5 tool executions
  - TC02: `library_search` · TC03: `reserve_book` · TC04: `get_student_status` + `extend_loan` · TC05: `library_search`
- **Số test case chạy qua LLM thật (`live_llm`):** 2 (TC03, TC04)
- **Chế độ thực thi theo thiết kế Hybrid:** TC01 = `static_response` · TC02 = `mcp_fast_path` · TC03 = `live_llm` · TC04 = `live_llm` (multi-step) · TC05 = `mcp_fast_path`
- **Kết quả:** ReAct loop hoạt động đúng, Observation được đưa trở lại LLM, tool routing đúng theo workflow thư viện, trace ghi đầy đủ provider/model/latency thật.

### Kết luận bài thực hiện
- Chủ đề thư viện đã được đồng bộ đúng vào tool, prompt, workflow và test case.
- ReAct loop hoạt động với trình tự: nhập mã sinh viên → kiểm tra trạng thái → thực hiện hành động mượn/trả/gia hạn/đặt trước.
- Các tool nghiệp vụ (`borrow_book`, `return_book`, `reserve_book`, `extend_loan`) nhận cả **mã sách lẫn tên sách** (tự resolve tên → mã) để tránh `NOT_FOUND` sai khi người dùng tra cứu bằng tên.
- Trace log đã được lưu tại `docs/trace_waterfall.json` với đầy đủ chuỗi `Thought → Action → Observation → Final Answer` trên LLM API thật.

---

> ✅ **HOÀN TẤT NỘP BÀI:** Sao chép đường link GitHub Repository cá nhân của bạn và dán vào ô nộp bài trên LMS để hoàn tất Bài Lab 3.
