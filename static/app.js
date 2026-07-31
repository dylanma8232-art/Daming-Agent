(() => {
  const storageKey = 'daming-agent-web-conversation-id';
  const newId = () => crypto.randomUUID().replaceAll('-', '');
  const getConversationId = () => sessionStorage.getItem(storageKey) || (() => {
    const id = newId(); sessionStorage.setItem(storageKey, id); return id;
  })();
  const messages = document.getElementById('chat-messages');
  const input = document.getElementById('prompt-input');
  const send = document.getElementById('send-btn');
  const addMessage = (author, text, user) => {
    const node = document.createElement('div');
    node.className = `message ${user ? 'user-message' : 'system-message'}`;
    node.innerHTML = `<div class="msg-avatar">${user ? '👤' : '🤖'}</div><div class="msg-body"><div class="msg-author">${author}</div><div class="msg-text"></div></div>`;
    node.querySelector('.msg-text').textContent = text;
    messages.appendChild(node); messages.scrollTop = messages.scrollHeight;
    return node.querySelector('.msg-text');
  };
  const submit = async () => {
    const prompt = input.value.trim(); if (!prompt || send.disabled) return;
    addMessage('你', prompt, true); input.value = ''; send.disabled = true;
    const answer = addMessage('Daming Agent', '', false);
    try {
      const response = await fetch('/api/chat/stream', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({prompt, conversation_id: getConversationId()}),
      });
      if (!response.ok || !response.body) throw new Error('请求失败');
      const reader = response.body.getReader(); const decoder = new TextDecoder(); let buffer = '';
      while (true) {
        const {done, value} = await reader.read(); if (done) break;
        buffer += decoder.decode(value, {stream: true});
        const events = buffer.split('\n\n'); buffer = events.pop();
        for (const event of events) {
          const data = event.split('\n').find(line => line.startsWith('data: '))?.slice(6);
          if (data && data !== '[DONE]') answer.textContent += JSON.parse(data).chunk || '';
        }
        messages.scrollTop = messages.scrollHeight;
      }
    } catch (error) { answer.textContent = `请求失败：${error.message}`; }
    finally { send.disabled = false; input.focus(); }
  };
  send.addEventListener('click', submit);
  input.addEventListener('keydown', event => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); submit(); } });
  document.getElementById('new-conversation-btn').addEventListener('click', () => {
    sessionStorage.setItem(storageKey, newId());
    messages.replaceChildren(); addMessage('Daming Agent', '已新建独立会话。', false); input.focus();
  });
  const switchTab = tab => {
    document.querySelectorAll('.nav-item').forEach(node => node.classList.toggle('active', node.dataset.tab === tab));
    document.querySelectorAll('.tab-content').forEach(node => node.classList.toggle('active', node.id === tab));
    document.getElementById('page-title').textContent = document.querySelector(`.nav-item[data-tab="${tab}"] .nav-text`).textContent;
    if (tab === 'runtime-tab') loadRuntime();
  };
  document.querySelectorAll('.nav-item').forEach(node => node.addEventListener('click', () => switchTab(node.dataset.tab)));
  const esc = text => String(text ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const showRows = (id, rows, formatter) => {
    document.getElementById(id).innerHTML = rows.length ? rows.map(formatter).join('') : '<div class="runtime-empty">暂无记录</div>';
  };
  async function decideApproval(id, approved) {
    await fetch(`/api/approvals/${encodeURIComponent(id)}`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({approved})});
    loadRuntime();
  }
  async function loadRuntime() {
    try {
      const result = await fetch('/api/runtime?limit=50').then(r => r.json());
      showRows('runtime-approvals', result.approvals || [], row => `<div class="runtime-row"><code>${esc(row.id)}</code><span>${esc(row.risk)} · ${esc(row.tool_name)}</span><span>${esc(row.status)}</span>${row.status === 'pending' ? `<button data-approval="${esc(row.id)}" data-ok="1">批准</button><button data-approval="${esc(row.id)}" data-ok="0">拒绝</button>` : ''}</div>`);
      showRows('runtime-tasks', result.tasks || [], row => `<div class="runtime-row"><code>${esc(row.id)}</code><span>${esc(row.status)} · PID ${esc(row.pid || '-')}</span><span>${esc(row.progress || '')}</span></div>`);
      const [subagents, crons] = await Promise.all([fetch('/api/runtime/subagents?limit=50').then(r => r.json()), fetch('/api/runtime/crons?limit=50').then(r => r.json())]);
      showRows('runtime-subagents', subagents.items || [], row => `<div class="runtime-row"><code>${esc(row.id)}</code><span>${esc(row.role)} · ${esc(row.status)}</span><span>${esc(row.progress || '')}</span></div>`);
      showRows('runtime-crons', crons.items || [], row => `<div class="runtime-row"><code>${esc(row.id)}</code><span>${esc(row.name)} · ${esc(row.expression)}</span><span>${esc(row.status)}</span></div>`);
      showRows('runtime-audit', result.audit || [], row => `<div class="runtime-row"><span>${esc(row.event_type)}</span><span>${esc(row.tool_name || row.approval_id || '')}</span><span>${esc(row.outcome?.status || '')}</span></div>`);
      document.querySelectorAll('[data-approval]').forEach(button => button.addEventListener('click', () => decideApproval(button.dataset.approval, button.dataset.ok === '1')));
    } catch (error) { document.getElementById('runtime-audit').textContent = `加载失败：${error.message}`; }
  }
  document.getElementById('runtime-refresh').addEventListener('click', loadRuntime);
})();
