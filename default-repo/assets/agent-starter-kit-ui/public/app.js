// Chat UI client — SAP A2A protocol v0.3.0
// Decorative elements (+, @, nav, bell) are visual-only by design.
// Functional: chat input, send, message rendering, streaming, retry, session
// continuity, and the Prompt Library (Joule-style clickable prompt starters).

const AGENT_PATH = '/agent/';          // proxied by server.js to AGENT_URL
const INPUT_CAP = 8000;                 // soft character cap (fix #7)
const WARN_AT = 7500;

const input = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');
const messages = document.getElementById('messages');
const welcome = document.getElementById('welcome');
const chatArea = document.getElementById('chatArea');
const conversation = document.getElementById('conversation');
const charWarning = document.getElementById('charWarning');
const rail = document.getElementById('rail');
const sidebarToggle = document.getElementById('sidebarToggle');
const topbarTitle = document.getElementById('topbarTitle');

// Session continuity (fix #6): a stable contextId threaded across turns (A2A 0.3.0).
let contextId = null;
let lastUserText = null;   // for retry (fix #5)
let agentName = null;      // resolved from the agent card, shown after first turn

// Resolve the agent's display name from its card (never hardcoded).
(async function loadAgentName() {
  try {
    // Fetched through the /agent proxy so it reaches the agent, not the SPA fallback.
    const res = await fetch(AGENT_PATH + '.well-known/agent.json');
    if (!res.ok) return;
    const card = await res.json();
    if (card?.name) agentName = titleCase(card.name);
  } catch {}
})();

// "hello-world-agent" -> "Hello World Agent"
function titleCase(slug) {
  return String(slug)
    .replace(/[-_]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

// ---------- Input handling ----------
input.addEventListener('input', () => {
  input.style.height = 'auto';
  input.style.height = Math.min(input.scrollHeight, 140) + 'px';

  const len = input.value.length;
  sendBtn.disabled = input.value.trim() === '';

  // Fix #7: soft cap warning
  if (len >= WARN_AT) {
    charWarning.textContent = `${len} / ${INPUT_CAP}`;
    charWarning.classList.toggle('warn', len >= INPUT_CAP);
  } else {
    charWarning.textContent = '';
    charWarning.classList.remove('warn');
  }
});

input.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    if (!sendBtn.disabled) sendMessage();
  }
});

sendBtn.addEventListener('click', () => sendMessage());

// Fix #3: rail toggle on mobile
if (sidebarToggle && rail) {
  sidebarToggle.addEventListener('click', () => rail.classList.toggle('open'));
}

// ---------- Prompt Library (Joule-style prompt starters) ----------
// Clicking "View Prompt Library" opens a popover of ready-made prompts; clicking
// one fills the input and sends it — the same affordance Joule 1.0 offers.
const PROMPT_STARTERS = [
  'What can you help me with?',
  'Show me a summary of the available data.',
  'What are the current risks or issues?',
  'Give me an analysis of the current situation.',
  'What actions do you recommend?',
];
(function buildPromptLibrary() {
  const link = document.querySelector('.prompt-library-link');
  if (!link) return;
  const pop = document.createElement('div');
  pop.className = 'prompt-pop hidden';
  const title = document.createElement('div');
  title.className = 'prompt-pop-title';
  title.textContent = 'Prompt Library';
  pop.appendChild(title);
  PROMPT_STARTERS.forEach((text) => {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'prompt-pop-item';
    btn.textContent = text;              // textContent — no HTML injection
    btn.addEventListener('click', () => {
      pop.classList.add('hidden');
      input.value = text;
      input.dispatchEvent(new Event('input'));   // enable send + resize
      sendMessage();
    });
    pop.appendChild(btn);
  });
  link.parentElement.appendChild(pop);
  link.addEventListener('click', (e) => {
    e.stopPropagation();
    pop.classList.toggle('hidden');
  });
  document.addEventListener('click', (e) => {
    if (e.target !== link && !pop.contains(e.target)) pop.classList.add('hidden');
  });
})();

// ---------- Rendering ----------
const AGENT_ACTIONS = `
  <button title="Copy" tabindex="-1"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg></button>
  <button title="Good response" tabindex="-1"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M7 10v12"/><path d="M15 5.88 14 10h5.83a2 2 0 0 1 1.92 2.56l-2.33 8A2 2 0 0 1 17.5 22H4a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2h2.76a2 2 0 0 0 1.79-1.11L12 2a3.13 3.13 0 0 1 3 3.88z"/></svg></button>
  <button title="Bad response" tabindex="-1"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M17 14V2"/><path d="M9 18.12 10 14H4.17a2 2 0 0 1-1.92-2.56l2.33-8A2 2 0 0 1 6.5 2H20a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-2.76a2 2 0 0 0-1.79 1.11L12 22a3.13 3.13 0 0 1-3-3.88z"/></svg></button>
  <button title="Regenerate" tabindex="-1"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 12a9 9 0 0 1 15-6.7L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-15 6.7L3 16"/><path d="M3 21v-5h5"/></svg></button>
  <button title="Suggestions" tabindex="-1"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M9 18h6"/><path d="M10 22h4"/><path d="M15.09 14c.18-.98.65-1.74 1.41-2.5A4.65 4.65 0 0 0 18 8 6 6 0 0 0 6 8c0 1 .23 2.23 1.5 3.5A4.61 4.61 0 0 1 8.91 14"/></svg></button>`;

function ensureDateDivider() {
  if (messages.querySelector('.msg-divider')) return;
  const now = new Date();
  const time = now.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
  const div = document.createElement('div');
  div.className = 'msg-divider';
  div.innerHTML = `<strong>Today</strong> ${time}`;
  messages.appendChild(div);
}

function appendMessage(role, text, { isThinking = false, isError = false } = {}) {
  const div = document.createElement('div');
  div.className = `msg ${role}` + (isThinking ? ' thinking' : '') + (isError ? ' error' : '');

  const bubble = document.createElement('div');
  bubble.className = 'msg-bubble';

  if (isThinking) {
    bubble.innerHTML = '<div class="typing-dots"><span></span><span></span><span></span></div>';
  } else if (role === 'agent' && !isError) {
    bubble.innerHTML = renderMarkdown(text);   // fix #1
  } else {
    bubble.textContent = text;
  }

  div.appendChild(bubble);

  // Agent replies get a visual-only action row (copy / feedback / regenerate)
  if (role === 'agent' && !isThinking && !isError) {
    const actions = document.createElement('div');
    actions.className = 'msg-actions';
    actions.innerHTML = AGENT_ACTIONS;
    div.appendChild(actions);
  }

  messages.appendChild(div);
  scrollToEnd();
  return { div, bubble };
}

function scrollToEnd() { chatArea.scrollTop = chatArea.scrollHeight; }

// SAP Fiori semantic status icons — inline SVG, no icon-font dependency (matches this
// UI's all-inline-SVG idiom and stays fully offline). Generic emojis in the agent's reply
// are swapped for these. Colors are SAP Horizon semantic: negative #D20A0A, critical
// #E76500, caution #E9A200, positive #188918, information #0070F2.
function statusDot(color, label) {
  return `<span class="sap-status" role="img" aria-label="${label}"><svg width="14" height="14" viewBox="0 0 16 16" fill="${color}"><circle cx="8" cy="8" r="6"/></svg></span>`;
}
const ICONS = {
  '🔴': statusDot('#D20A0A', 'error'),
  '🟠': statusDot('#E76500', 'warning'),
  '🟡': statusDot('#E9A200', 'caution'),
  '🟢': statusDot('#188918', 'success'),
  '✅': `<span class="sap-status" role="img" aria-label="done"><svg width="15" height="15" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="8" r="7" fill="#188918"/><path d="M4.5 8.3l2.2 2.2 4.8-4.8" stroke="#fff" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg></span>`,
  '🚨': `<span class="sap-status" role="img" aria-label="alert"><svg width="15" height="15" viewBox="0 0 16 16" fill="none"><path d="M8 2.2l6 10.4H2z" fill="#D20A0A"/><rect x="7.25" y="6" width="1.5" height="3.4" rx=".75" fill="#fff"/><circle cx="8" cy="10.9" r=".85" fill="#fff"/></svg></span>`,
  '⚡': `<span class="sap-status" role="img" aria-label="urgent"><svg width="15" height="15" viewBox="0 0 16 16" fill="#E76500"><path d="M9 1.5 3.5 9H7l-1 5.5L12.5 6.5H9z"/></svg></span>`,
  '📊': `<span class="sap-status" role="img" aria-label="report"><svg width="15" height="15" viewBox="0 0 16 16" fill="#0070F2"><rect x="2" y="8" width="3" height="6" rx=".5"/><rect x="6.5" y="4.5" width="3" height="9.5" rx=".5"/><rect x="11" y="6.5" width="3" height="7.5" rx=".5"/></svg></span>`,
};
const ICON_RE = new RegExp(Object.keys(ICONS).join('|'), 'g');
function replaceIcons(str) {
  return str.replace(ICON_RE, (m) => ICONS[m] || m);
}

// Fix #1: minimal, XSS-safe markdown — escape first, then apply a safe subset.
// Supports headings, GFM tables, lists, bold/italic, inline+fenced code, links.
function renderMarkdown(src) {
  let s = escapeHtml(src || '');
  s = replaceIcons(s);   // emojis survive escaping; inject SVG after, so it isn't re-escaped

  // fenced code blocks
  s = s.replace(/```([\s\S]*?)```/g, (_, code) => `<pre><code>${code.replace(/^\n/, '')}</code></pre>`);
  // inline code
  s = s.replace(/`([^`]+)`/g, '<code>$1</code>');
  // bold / italic
  s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  s = s.replace(/(^|[^*])\*([^*]+)\*/g, '$1<em>$2</em>');
  // links [text](url) — only http(s)
  s = s.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
    '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');

  const lines = s.split('\n');
  let html = '', inList = false;
  const closeList = () => { if (inList) { html += '</ul>'; inList = false; } };

  // A GFM delimiter row: pipes, dashes, optional colons — and at least one dash + pipe.
  const isDelim = (l) => /^\s*\|?[\s:|-]+\|?\s*$/.test(l) && l.includes('-') && l.includes('|');
  // Split a table row into trimmed cells, dropping the empty edges left by surrounding pipes.
  const splitRow = (l) => {
    const cells = l.trim().split('|');
    if (cells.length && cells[0].trim() === '') cells.shift();
    if (cells.length && cells[cells.length - 1].trim() === '') cells.pop();
    return cells.map((c) => c.trim());
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trimEnd();

    // GFM table: header row, then a delimiter row, then contiguous body rows.
    if (line.includes('|') && i + 1 < lines.length && isDelim(lines[i + 1])) {
      closeList();
      const headers = splitRow(line);
      const aligns = splitRow(lines[i + 1]).map((d) => {
        const l = d.startsWith(':'), r = d.endsWith(':');
        return l && r ? 'center' : r ? 'right' : l ? 'left' : '';
      });
      i += 1;   // consume the delimiter row
      const cell = (tag, c, j) => {
        const a = aligns[j] ? ` style="text-align:${aligns[j]}"` : '';
        return `<${tag}${a}>${c}</${tag}>`;
      };
      const head = '<tr>' + headers.map((c, j) => cell('th', c, j)).join('') + '</tr>';
      let body = '';
      while (i + 1 < lines.length && lines[i + 1].includes('|') && lines[i + 1].trim() !== '') {
        i += 1;
        const cells = splitRow(lines[i]);
        body += '<tr>' + cells.map((c, j) => cell('td', c, j)).join('') + '</tr>';
      }
      html += `<div class="md-table-wrap"><table class="md-table"><thead>${head}</thead><tbody>${body}</tbody></table></div>`;
      continue;
    }

    // thematic break (---, ***, ___): drop it — headings/tables already give section spacing
    if (/^\s*([-*_])\1{2,}\s*$/.test(line)) {
      closeList();
      continue;
    }

    // headings (# … ######)
    const h = line.match(/^(#{1,6})\s+(.*)$/);
    if (h) {
      closeList();
      const level = h[1].length;
      html += `<h${level}>${h[2].trim()}</h${level}>`;
      continue;
    }

    // list items
    const li = line.match(/^\s*[-*]\s+(.*)$/);
    if (li) {
      if (!inList) { html += '<ul>'; inList = true; }
      html += `<li>${li[1]}</li>`;
      continue;
    }

    closeList();
    if (line.trim() === '') { /* blank line */ }
    else if (/^<pre>/.test(line) || /<\/pre>$/.test(line)) { html += line; }
    else html += `<p>${line}</p>`;
  }
  closeList();
  return html || '<p></p>';
}

function escapeHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

// ---------- Send ----------
async function sendMessage(retryText = null) {
  const text = retryText ?? input.value.trim();
  if (!text) return;
  lastUserText = text;

  welcome.classList.add('hidden');
  conversation.classList.add('has-messages');   // dock input to bottom, scroll messages above
  if (topbarTitle && agentName) topbarTitle.textContent = agentName;  // show the agent's name after chat starts

  if (!retryText) {
    ensureDateDivider();
    appendMessage('user', text);
    input.value = '';
    input.style.height = 'auto';
    charWarning.textContent = '';
    sendBtn.disabled = true;
  }

  const thinking = appendMessage('agent', '', { isThinking: true });
  let started = false;   // fix #2: drop dots on first token

  try {
    const msgId = crypto.randomUUID();
    const message = {
      role: 'user',
      messageId: msgId,
      parts: [{ kind: 'text', text }]
    };
    if (contextId) message.contextId = contextId;   // fix #6

    const payload = {
      jsonrpc: '2.0',
      id: msgId,
      method: 'message/send',
      params: { message }
    };

    const res = await fetch(AGENT_PATH, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      throw new HttpError(res.status);
    }

    const contentType = res.headers.get('content-type') || '';
    let agentText = '';

    if (contentType.includes('text/event-stream') || contentType.includes('application/x-ndjson')) {
      // Fix #2: progressive streaming — append to the live bubble as chunks arrive.
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop();

        for (const line of lines) {
          const trimmed = line.replace(/^data:\s*/, '').trim();
          if (!trimmed || trimmed === '[DONE]') continue;
          try {
            const chunk = JSON.parse(trimmed);
            captureContextId(chunk);
            const content = extractContent(chunk);
            if (content) {
              agentText = content;   // A2A sends cumulative text
              if (!started) { thinking.bubble.innerHTML = ''; started = true; }
              thinking.bubble.innerHTML = renderMarkdown(agentText);
              scrollToEnd();
            }
          } catch {}
        }
      }
    } else {
      const data = await res.json();
      captureContextId(data);
      agentText = extractContent(data);
    }

    if (!agentText) {
      thinking.bubble.textContent = '(no response)';
    } else {
      thinking.div.classList.remove('thinking');
      thinking.bubble.innerHTML = renderMarkdown(agentText);
    }
    scrollToEnd();

  } catch (err) {
    // Fix #5: distinguish error classes + offer retry.
    thinking.div.remove();
    const msg = describeError(err);
    const { bubble } = appendMessage('agent', msg, { isError: true });
    const retry = document.createElement('button');
    retry.className = 'retry-btn';
    retry.textContent = 'Retry';
    retry.addEventListener('click', () => {
      bubble.parentElement.remove();
      sendMessage(lastUserText);
    });
    bubble.parentElement.appendChild(retry);
    scrollToEnd();
  }
}

class HttpError extends Error {
  constructor(status) { super(`HTTP ${status}`); this.status = status; }
}

function describeError(err) {
  if (err instanceof HttpError) {
    if (err.status >= 500) return `The agent had a server error (${err.status}). Try again in a moment.`;
    if (err.status === 404) return 'Agent endpoint not found (404). Check that the agent is running.';
    return `The agent returned an error (${err.status}).`;
  }
  if (err instanceof TypeError) return 'Network error — could not reach the agent. Check your connection.';
  return `Error: ${err.message}`;
}

function captureContextId(data) {
  const id = data?.result?.contextId ?? data?.result?.status?.message?.contextId;
  if (id) contextId = id;
}

function extractContent(data) {
  try {
    // A2A 0.3.0: result.artifacts[].parts[].text (kind: 'text')
    const artifacts = data?.result?.artifacts;
    if (artifacts?.length) {
      for (const artifact of artifacts) {
        for (const part of artifact?.parts ?? []) {
          if (part?.text) return part.text;
        }
      }
    }
    // streaming chunk: result.status.message.parts[].text
    const parts = data?.result?.status?.message?.parts;
    if (parts?.length) {
      for (const part of parts) {
        if (part?.text) return part.text;
      }
    }
    if (data?.result?.content) return data.result.content;
    if (typeof data?.result === 'string') return data.result;
  } catch {}
  return '';
}
