/* ─── State ─── */
let pin = '';
let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;

/* ─── Elements ─── */
const loginScreen   = document.getElementById('login-screen');
const chatScreen    = document.getElementById('chat-screen');
const pinDots       = document.getElementById('pin-dots');
const loginError    = document.getElementById('login-error');
const messages      = document.getElementById('messages');
const typingIndicator = document.getElementById('typing-indicator');
const msgInput      = document.getElementById('msg-input');
const btnSend       = document.getElementById('btn-send');
const btnMic        = document.getElementById('btn-mic');
const hudMic        = document.getElementById('hud-mic');
const btnPhoto      = document.getElementById('btn-photo');
const btnLogout     = document.getElementById('btn-logout');
const fileInput     = document.getElementById('file-input');

/* ─── Service Worker ─── */
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/sw.js').catch(() => {});
}

/* ─── Boot: check if already logged in ─── */
(async () => {
  try {
    const r = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: '__ping__' }),
    });
    if (r.status !== 401) showChat();
  } catch {}
})();

/* ─── PIN Login ─── */
function updateDots() {
  pinDots.querySelectorAll('span').forEach((s, i) => {
    s.classList.toggle('filled', i < pin.length);
  });
}

document.querySelectorAll('.pin-key').forEach(btn => {
  btn.addEventListener('click', () => {
    const d = btn.dataset.d;
    if (d === 'clear') {
      pin = pin.slice(0, -1);
      updateDots();
      return;
    }
    if (pin.length >= 4) return;
    pin += d;
    updateDots();
    if (pin.length === 4) submitPin();
  });
});

async function submitPin() {
  loginError.textContent = '';
  const r = await fetch('/api/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ pin }),
  });
  if (r.ok) {
    showChat();
  } else {
    pinDots.classList.add('error');
    loginError.textContent = 'Wrong PIN';
    setTimeout(() => {
      pinDots.classList.remove('error');
      pin = '';
      updateDots();
      loginError.textContent = '';
    }, 800);
  }
}

/* ─── Screen switching ─── */
function showChat() {
  loginScreen.classList.add('hidden');
  chatScreen.classList.remove('hidden');
  msgInput.focus();
  if (!messages.children.length) {
    addBubble('bot', 'ICARUS online. How can I help?');
  }
}

/* ─── Logout ─── */
btnLogout.addEventListener('click', async () => {
  await fetch('/api/logout', { method: 'POST' });
  chatScreen.classList.add('hidden');
  loginScreen.classList.remove('hidden');
  pin = '';
  updateDots();
  messages.innerHTML = '';
});

/* ─── Chat ─── */
function addBubble(type, text) {
  const div = document.createElement('div');
  div.className = `bubble ${type}`;
  div.textContent = text;
  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
  return div;
}

function showTyping() { typingIndicator.classList.remove('hidden'); messages.scrollTop = messages.scrollHeight; }
function hideTyping() { typingIndicator.classList.add('hidden'); }

function addLinkedInActions(draft) {
  const card = document.createElement('div');
  card.className = 'linkedin-card';
  card.id = 'linkedin-actions';

  const header = document.createElement('div');
  header.className = 'linkedin-card-header';
  header.innerHTML = `
    <svg class="li-logo" viewBox="0 0 24 24" fill="#0a66c2"><path d="M20.447 20.452H16.89v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a1.98 1.98 0 1 1 0-3.96 1.98 1.98 0 0 1 0 3.96zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg>
    <div class="li-header-info">
      <span class="li-name">Eugen Müller</span>
      <span class="li-meta">Preview · Not yet posted</span>
    </div>`;
  card.appendChild(header);

  const body = document.createElement('div');
  body.className = 'linkedin-card-body';
  body.textContent = draft || '';
  card.appendChild(body);

  const actions = document.createElement('div');
  actions.className = 'linkedin-card-actions';
  [['post', 'Publish'], ['cancel', 'Discard']].forEach(([cmd, label]) => {
    const btn = document.createElement('button');
    btn.textContent = label;
    btn.className = `li-btn li-btn-${cmd}`;
    btn.onclick = () => { card.remove(); sendMessage(cmd); };
    actions.appendChild(btn);
  });
  const editBtn = document.createElement('button');
  editBtn.textContent = 'Edit';
  editBtn.className = 'li-btn li-btn-edit';
  editBtn.onclick = () => { msgInput.focus(); msgInput.placeholder = 'Describe your changes…'; };
  actions.appendChild(editBtn);
  card.appendChild(actions);

  messages.appendChild(card);
  messages.scrollTop = messages.scrollHeight;
}

function clearLinkedInActions() {
  document.getElementById('linkedin-actions')?.remove();
}

async function sendMessage(text) {
  if (!text.trim()) return;
  clearLinkedInActions();
  addBubble('user', text);
  msgInput.value = '';
  msgInput.placeholder = 'Message ICARUS…';
  showTyping();
  try {
    const r = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text }),
    });
    if (r.status === 401) { location.reload(); return; }
    const data = await r.json();
    hideTyping();
    addBubble('bot', data.reply);
    if (data.linkedin?.pending) addLinkedInActions(data.linkedin.draft);
  } catch (e) {
    hideTyping();
    addBubble('bot', 'Connection error. Try again.');
  }
}

btnSend.addEventListener('click', () => sendMessage(msgInput.value));
msgInput.addEventListener('keydown', e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(msgInput.value); } });

/* ─── Voice ─── */
btnMic.addEventListener('click', async () => {
  if (isRecording) {
    stopRecording();
  } else {
    startRecording();
  }
});

async function startRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    audioChunks = [];
    mediaRecorder = new MediaRecorder(stream);
    mediaRecorder.ondataavailable = e => { if (e.data.size > 0) audioChunks.push(e.data); };
    mediaRecorder.onstop = sendVoice;
    mediaRecorder.start();
    isRecording = true;
    btnMic.classList.add('recording');
    hudMic.classList.add('recording');
    btnMic.title = 'Stop recording';
  } catch {
    addBubble('bot', 'Microphone access denied.');
  }
}

function stopRecording() {
  if (mediaRecorder && isRecording) {
    mediaRecorder.stop();
    mediaRecorder.stream.getTracks().forEach(t => t.stop());
    isRecording = false;
    btnMic.classList.remove('recording');
    hudMic.classList.remove('recording');
    btnMic.title = 'Voice message';
  }
}

async function sendVoice() {
  const mimeType = audioChunks[0]?.type || 'audio/webm';
  const blob = new Blob(audioChunks, { type: mimeType });
  const form = new FormData();
  form.append('file', blob, 'voice.webm');
  showTyping();
  try {
    const r = await fetch('/api/voice', { method: 'POST', body: form });
    if (r.status === 401) { location.reload(); return; }
    const data = await r.json();
    hideTyping();
    if (data.transcript) addBubble('transcript', `"${data.transcript}"`);
    addBubble('bot', data.reply);
    if (data.linkedin?.pending) addLinkedInActions(data.linkedin.draft);
  } catch {
    hideTyping();
    addBubble('bot', 'Voice error. Try again.');
  }
}

/* ─── Photo ─── */
btnPhoto.addEventListener('click', () => fileInput.click());

fileInput.addEventListener('change', async () => {
  const file = fileInput.files[0];
  if (!file) return;
  fileInput.value = '';
  addBubble('user', `📷 ${file.name}`);
  const form = new FormData();
  form.append('file', file);
  showTyping();
  try {
    const r = await fetch('/api/photo', { method: 'POST', body: form });
    if (r.status === 401) { location.reload(); return; }
    const data = await r.json();
    hideTyping();
    addBubble('bot', data.reply);
  } catch {
    hideTyping();
    addBubble('bot', 'Photo error. Try again.');
  }
});
