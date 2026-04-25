const $ = (sel) => {
  const el = document.querySelector(sel);
  if (!el) throw new Error(`Missing element: ${sel}`);
  return el;
};

function setActiveTab(name) {
  for (const btn of document.querySelectorAll('.tab')) {
    btn.classList.toggle('active', btn.dataset.tab === name);
  }
  for (const panel of document.querySelectorAll('.panel')) {
    panel.hidden = panel.id !== `panel-${name}`;
  }
}

async function apiGet(path) {
  const res = await fetch(path, { headers: { 'Accept': 'application/json' } });
  const text = await res.text();
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}: ${text}`);
  return JSON.parse(text);
}

async function apiPost(path, body) {
  const res = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
    body: JSON.stringify(body),
  });
  const text = await res.text();
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}: ${text}`);
  return JSON.parse(text);
}

function renderJson(el, value) {
  el.textContent = JSON.stringify(value, null, 2);
}

async function runCommandTo(el, message) {
  el.textContent = 'Running…';
  try {
    const data = await apiPost('/api/command', { message });
    renderJson(el, data);
    return data;
  } catch (err) {
    el.textContent = String(err && err.stack ? err.stack : err);
    throw err;
  }
}

function escapeHtml(str) {
  return str
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

async function loadApprovals() {
  const root = $('#approvals');
  root.innerHTML = '<div class="muted">Loading…</div>';

  const data = await apiGet('/api/approvals');
  if (!data.approvals || data.approvals.length === 0) {
    root.innerHTML = '<div class="muted">No pending approvals.</div>';
    return;
  }

  root.innerHTML = '';

  for (const item of data.approvals) {
    const card = document.createElement('div');
    card.className = 'card';

    const executionId = item.execution_id || item.executionId || item.id || item.file;

    card.innerHTML = `
      <div class="cardHeader">
        <div class="title">${escapeHtml(String(executionId || 'approval'))}</div>
        <div class="pills">
          ${item.status ? `<span class="pill">${escapeHtml(String(item.status))}</span>` : ''}
          ${item.plan_hash ? `<span class="pill">plan ${escapeHtml(String(item.plan_hash).slice(0, 10))}</span>` : ''}
        </div>
      </div>
      <div class="row">
        <button class="approve">Approve</button>
        <button class="secondary copy">Copy /approve</button>
      </div>
      <pre class="code" style="margin-top:10px; min-height: 0">${escapeHtml(JSON.stringify(item, null, 2))}</pre>
    `;

    const approveBtn = card.querySelector('button.approve');
    const copyBtn = card.querySelector('button.copy');

    approveBtn.addEventListener('click', async () => {
      const cmd = `/approve ${executionId}`;
      await runCommand(cmd);
      await loadApprovals();
    });

    copyBtn.addEventListener('click', async () => {
      const cmd = `/approve ${executionId}`;
      await navigator.clipboard.writeText(cmd);
      $('#command-input').value = cmd;
      setActiveTab('command');
    });

    root.appendChild(card);
  }
}

async function loadReceipts() {
  const limit = Number($('#receipts-limit').value || '50');
  const data = await apiGet(`/api/receipts?limit=${encodeURIComponent(String(limit))}`);
  renderJson($('#receipts'), data);
}

async function loadArtifacts() {
  const prefix = String($('#artifacts-prefix').value || 'runs');
  const listEl = $('#artifacts-list');
  const viewer = $('#artifact-viewer');
  listEl.innerHTML = '<div class="item"><span class="muted">Loading…</span></div>';
  viewer.textContent = 'Select an artifact…';

  const data = await apiGet(`/api/artifacts?prefix=${encodeURIComponent(prefix)}`);
  listEl.innerHTML = '';

  if (!data.files || data.files.length === 0) {
    listEl.innerHTML = '<div class="item"><span class="muted">No files.</span></div>';
    return;
  }

  for (const file of data.files) {
    const row = document.createElement('div');
    row.className = 'item';
    row.innerHTML = `
      <code>${escapeHtml(String(file.path))}</code>
      <button class="secondary">Open</button>
    `;
    row.querySelector('button').addEventListener('click', async () => {
      const artifact = await apiGet(`/api/artifact?path=${encodeURIComponent(String(file.path))}`);
      if (artifact && typeof artifact === 'object' && 'content' in artifact) {
        viewer.textContent = String(artifact.content ?? '');
      } else {
        viewer.textContent = JSON.stringify(artifact, null, 2);
      }
    });
    listEl.appendChild(row);
  }
}

async function loadScheduler() {
  const jobId = String($('#scheduler-job').value || '').trim();
  const qs = jobId ? `?job_id=${encodeURIComponent(jobId)}` : '';
  const data = await apiGet(`/api/scheduler/history${qs}`);
  renderJson($('#scheduler'), data);
}

async function runSchedulerExplain() {
  const jobId = String($('#scheduler-explain-job').value || '').trim();
  const at = String($('#scheduler-explain-at').value || '').trim();
  if (!jobId) {
    $('#scheduler-explain').textContent = 'job_id is required.';
    return;
  }
  const cmd = at ? `/scheduler explain ${jobId} --at ${at}` : `/scheduler explain ${jobId}`;
  await runCommandTo($('#scheduler-explain'), cmd);
}

async function runAuditExport() {
  const since = String($('#audit-since').value || '').trim();
  if (!since) {
    $('#audit-output').textContent = 'since_iso is required.';
    return;
  }
  const redact = !!$('#audit-redact').checked;
  const includeArtifacts = !!$('#audit-include-artifacts').checked;
  const payload = {
    since_iso: since,
    redact,
    include_artifacts: includeArtifacts,
  };
  const cmd = `/audit export ${JSON.stringify(payload)}`;
  await runCommandTo($('#audit-output'), cmd);
}

async function runCommand(message) {
  return runCommandTo($('#command-output'), message);
}

function wireUi() {
  for (const btn of document.querySelectorAll('.tab')) {
    btn.addEventListener('click', () => setActiveTab(btn.dataset.tab));
  }

  $('#refresh-approvals').addEventListener('click', () => loadApprovals());
  $('#refresh-receipts').addEventListener('click', () => loadReceipts());
  $('#refresh-artifacts').addEventListener('click', () => loadArtifacts());
  $('#refresh-scheduler').addEventListener('click', () => loadScheduler());
  $('#run-scheduler-explain').addEventListener('click', () => runSchedulerExplain());
  $('#run-audit-export').addEventListener('click', () => runAuditExport());

  $('#send-command').addEventListener('click', async () => {
    const cmd = String($('#command-input').value || '').trim();
    if (!cmd.startsWith('/')) {
      $('#command-output').textContent = 'Command must start with /';
      return;
    }
    await runCommand(cmd);
  });

  $('#command-input').addEventListener('keydown', async (e) => {
    if (e.key === 'Enter') {
      const cmd = String($('#command-input').value || '').trim();
      if (cmd.startsWith('/')) await runCommand(cmd);
    }
  });
}

wireUi();
setActiveTab('approvals');

// Lazy-load current tab data
await loadApprovals();
