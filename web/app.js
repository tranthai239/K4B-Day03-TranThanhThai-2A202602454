const state = { studentId: null };
const $ = (selector) => document.querySelector(selector);

function setStudent(studentId, status) {
  state.studentId = studentId;
  $('#studentBadge').textContent = studentId;
  $('#sessionText').textContent = 'Đã xác thực qua MCP';
  $('#logoutBtn').hidden = false;
  $('#statusSummary').hidden = false;
  $('#borrowedCount').textContent = status.borrowed_books.length;
  $('#reservedCount').textContent = status.reserved_books.length;
  $('#overdueCount').textContent = status.overdue_books.length;
}

function addMessage(text, kind) {
  const item = document.createElement('div');
  item.className = `message ${kind}-message`;
  item.innerHTML = `<span class="message-label">${kind === 'user' ? 'YOU' : 'LIBRARY AGENT'}</span><p></p>`;
  item.querySelector('p').textContent = text;
  $('#chatLog').appendChild(item);
  $('#chatLog').scrollTop = $('#chatLog').scrollHeight;
}

function renderCatalog(books) {
  $('#catalogGrid').innerHTML = books.map((book) => `
    <article class="book-card">
      <span class="book-code">${book.book_code}</span>
      <h3>${book.title}</h3>
      <div class="book-status ${book.status.toLowerCase()}"><span class="status-dot"></span>${book.status === 'AVAILABLE' ? `${book.available_copies} bản sẵn` : 'Đang được mượn'}</div>
    </article>
  `).join('');
}

async function loadCatalog() {
  const response = await fetch('/api/catalog');
  const data = await response.json();
  if (data.status === 'SUCCESS') renderCatalog(data.data);
}

async function checkStudent(event) {
  event.preventDefault();
  const studentId = $('#studentId').value.trim().toUpperCase();
  $('#studentError').textContent = '';
  const response = await fetch(`/api/status?student_id=${encodeURIComponent(studentId)}`);
  const data = await response.json();
  if (data.status !== 'SUCCESS') {
    $('#statusSummary').hidden = true;
    $('#studentError').textContent = data.message || 'Không tìm thấy sinh viên.';
    return;
  }
  setStudent(studentId, data);
  addMessage(data.message, 'agent');
}

async function sendMessage(message) {
  if (!message.trim()) return;
  addMessage(message, 'user');
  $('#chatInput').value = '';
  const response = await fetch('/api/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message, student_id: state.studentId }) });
  const data = await response.json();
  addMessage(data.answer || data.message || 'Không nhận được phản hồi.', 'agent');
}

$('#studentForm').addEventListener('submit', checkStudent);
$('#chatForm').addEventListener('submit', (event) => { event.preventDefault(); sendMessage($('#chatInput').value); });
$('#logoutBtn').addEventListener('click', () => {
  state.studentId = null;
  $('#studentBadge').textContent = '--';
  $('#sessionText').textContent = 'Chưa đăng nhập';
  $('#logoutBtn').hidden = true;
  $('#statusSummary').hidden = true;
  addMessage('Đã đăng xuất. Vui lòng nhập mã sinh viên mới.', 'agent');
});
document.querySelectorAll('.shortcut').forEach((button) => button.addEventListener('click', () => sendMessage(button.dataset.prompt)));
