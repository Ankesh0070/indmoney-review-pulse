/* ===========================================================
   INDmoney MF FAQ Assistant — UI wiring
   -----------------------------------------------------------
   DOM rendering, chat composer, theme toggle, scroll handling.
   Reads answers from window.MFFAQ (js/engine.js).
   =========================================================== */

const LAST_UPDATED = window.MFFAQ.LAST_UPDATED;

const chat = document.getElementById('chat');
const input = document.getElementById('q');
const suggestions = document.getElementById('suggestions');
const scrollBtn = document.getElementById('scrollBtn');
scrollBtn.addEventListener('click', () => { chat.scrollTo({ top: chat.scrollHeight, behavior: 'smooth' }); scrollBtn.classList.remove('show'); });
chat.addEventListener('scroll', () => { scrollBtn.classList.toggle('show', !nearBottom()); });

function hostFromUrl(u){ try { return new URL(u).hostname.replace(/^www\./,''); } catch(e){ return u; } }
function nearBottom(){ return chat.scrollHeight - chat.scrollTop - chat.clientHeight < 120; }
function scrollDown(){ chat.scrollTop = chat.scrollHeight; scrollBtn.classList.remove('show'); }
function timeLabel(){ return new Date().toLocaleTimeString([], { hour:'2-digit', minute:'2-digit' }); }

function addUser(text){
  const row = document.createElement('div'); row.className = 'msg user';
  const col = document.createElement('div'); col.className = 'bubble-col';
  const b = document.createElement('div'); b.className = 'bubble'; b.textContent = text;
  const t = document.createElement('div'); t.className = 'time'; t.textContent = timeLabel();
  col.appendChild(b); col.appendChild(t);
  row.appendChild(col); chat.appendChild(row); scrollDown();
}

function sourcePill(src, label){
  const a = document.createElement('a'); a.className = 'src'; a.href = src;
  a.target = '_blank'; a.rel = 'noopener noreferrer';
  a.innerHTML = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.5 1.5"/><path d="M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7L12 19"/></svg>';
  const span = document.createElement('span'); span.textContent = (label || 'Official source') + ' · ' + hostFromUrl(src);
  a.appendChild(span);
  return a;
}

function botAvatar(){
  const av = document.createElement('div'); av.className = 'avatar'; av.setAttribute('aria-hidden', 'true');
  av.textContent = 'IND';
  return av;
}

function addBot(res){
  const row = document.createElement('div');
  row.className = 'msg bot' + (res.refuse ? ' refuse' : '');
  const col = document.createElement('div'); col.className = 'bubble-col';
  const b = document.createElement('div'); b.className = 'bubble';

  const paras = res.multi ? res.multi.map(p => p.a) : [res.a];
  paras.forEach(text => {
    const p = document.createElement('p'); p.className = 'answer'; p.textContent = text; b.appendChild(p);
  });

  const meta = document.createElement('div'); meta.className = 'meta';
  let hasSrc = false;
  if (res.multi){
    const seen = new Set();
    res.multi.forEach(p => { if (p.src && !seen.has(p.src)) { seen.add(p.src); meta.appendChild(sourcePill(p.src, p.srcLabel)); hasSrc = true; } });
  } else if (res.src){
    meta.appendChild(sourcePill(res.src, res.srcLabel)); hasSrc = true;
  }
  if (hasSrc){
    const u = document.createElement('div'); u.className = 'updated';
    u.textContent = 'Last updated from sources: ' + LAST_UPDATED;
    meta.appendChild(u); b.appendChild(meta);
  }

  const t = document.createElement('div'); t.className = 'time'; t.textContent = timeLabel();
  col.appendChild(b); col.appendChild(t);
  row.appendChild(botAvatar()); row.appendChild(col);
  chat.appendChild(row);
  scrollDown();
}

/* Typing indicator */
function showTyping(){
  const row = document.createElement('div'); row.className = 'msg bot typing'; row.id = 'typing';
  const b = document.createElement('div'); b.className = 'bubble';
  b.innerHTML = '<span class="dot"></span><span class="dot"></span><span class="dot"></span>';
  row.appendChild(botAvatar()); row.appendChild(b); chat.appendChild(row); scrollDown();
}
function hideTyping(){ const t = document.getElementById('typing'); if (t) t.remove(); }

/* debounce guard */
let sending = false;
function ask(text){
  if (!text.trim() || sending) return;
  sending = true;
  setTimeout(() => { sending = false; }, 300);

  if (suggestions) suggestions.classList.add('hidden');  /* hide chips after first message */

  addUser(text);
  input.value = '';
  showTyping();
  setTimeout(() => { hideTyping(); addBot(window.MFFAQ.answer(text)); }, 450);
}

document.getElementById('sendBtn').addEventListener('click', () => ask(input.value));
input.addEventListener('keydown', e => { if (e.key === 'Enter') ask(input.value); });
document.querySelectorAll('.chip').forEach(c => c.addEventListener('click', () => ask(c.dataset.q)));

/* ---- Theme toggle (single icon button) ---- */
const root = document.documentElement;
const tIcon = document.getElementById('themeIcon');
function setTheme(mode){
  root.setAttribute('data-theme', mode);
  tIcon.textContent = mode === 'dark' ? '☀️' : '🌙';
  try { localStorage.setItem('ind_theme', mode); } catch(e){}
}
let saved = 'light';
try { saved = localStorage.getItem('ind_theme') || 'light'; } catch(e){}
setTheme(saved);
document.getElementById('themeBtn').addEventListener('click',
  () => setTheme(root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark'));

/* ---- Opening message + disclaimer pill (milestone brief requires this exact note) ---- */
addBot({ a:'Hi! I answer factual questions about HDFC Large Cap, Flexi Cap, Mid Cap and ELSS Tax Saver — expense ratio, exit load, minimum SIP, lock-in, riskometer, benchmark and statements. Every answer cites one official source. No investment advice.', src:null });

(function addDisclaimerPill(){
  const row = document.createElement('div'); row.className = 'disclaimer-row';
  const pill = document.createElement('span'); pill.className = 'disclaimer-pill';
  pill.textContent = 'Facts-only. No investment advice.';
  row.appendChild(pill); chat.appendChild(row); scrollDown();
})();
