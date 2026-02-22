const API = '';

// --- API helpers ---
async function api(method, path, body) {
  const opts = { method, headers: { 'Content-Type': 'application/json' } };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(API + path, opts);
  return res.json();
}

// --- Toast ---
function toast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  const el = document.createElement('div');
  el.className = `toast toast-${type}`;
  el.textContent = message;
  container.appendChild(el);
  setTimeout(() => el.remove(), 4000);
}

// --- Modal ---
function showModal(html) {
  document.getElementById('modal-content').innerHTML = html;
  document.getElementById('modal-overlay').classList.remove('hidden');
}

function hideModal() {
  document.getElementById('modal-overlay').classList.add('hidden');
}

document.getElementById('modal-overlay').addEventListener('click', (e) => {
  if (e.target === e.currentTarget) hideModal();
});

// --- Time formatting ---
function formatAge(ms) {
  const s = Math.floor(ms / 1000);
  if (s < 60) return s + 's ago';
  const m = Math.floor(s / 60);
  if (m < 60) return m + 'm ago';
  const h = Math.floor(m / 60);
  if (h < 24) return h + 'h ago';
  return Math.floor(h / 24) + 'd ago';
}

function formatTime(ts) {
  return new Date(ts).toLocaleString();
}

// --- Render ---
async function loadSessions() {
  const filter = document.getElementById('status-filter').value;
  const qs = filter ? `?status=${filter}` : '';
  const data = await api('GET', '/api/sessions' + qs);
  renderSessionsList(data.sessions || []);
}

async function loadCurrentSession() {
  const data = await api('GET', '/api/sessions/current');
  renderCurrentSession(data.session);
}

function renderCurrentSession(session) {
  const panel = document.getElementById('current-session-panel');
  const info = document.getElementById('current-session-info');

  if (!session) {
    panel.classList.add('hidden');
    return;
  }

  panel.classList.remove('hidden');
  const m = session.metadata;

  let checkpointsHtml = '';
  if (m.checkpoints.length > 0) {
    checkpointsHtml = `
      <div class="checkpoints-list">
        <strong>Checkpoints (${m.checkpoints.length})</strong>
        ${m.checkpoints.map(c => `
          <div class="checkpoint-item">
            <span><code>${c.id}</code></span>
            <span>${formatTime(c.timestamp)}</span>
          </div>
        `).join('')}
      </div>`;
  }

  let opsHtml = '';
  if (session.pendingOperations.length > 0) {
    opsHtml = `
      <div class="operations-list">
        <strong>Pending Operations (${session.pendingOperations.length})</strong>
        ${session.pendingOperations.map(op => `
          <div class="operation-item">
            <span class="operation-type">[${op.type}]</span>
            <span>${op.description}</span>
            <button class="btn btn-sm btn-success operation-complete-btn" onclick="completeOperation('${op.id}')">Done</button>
          </div>
        `).join('')}
      </div>`;
  }

  let tagsHtml = '';
  if (m.tags.length > 0) {
    tagsHtml = m.tags.map(t => `<span class="tag">${t}</span>`).join(' ');
  }

  info.innerHTML = `
    <dl class="session-detail">
      <dt>Session ID</dt><dd>${m.id}</dd>
      <dt>Status</dt><dd><span class="badge badge-${m.status}">${m.status}</span></dd>
      <dt>Working Dir</dt><dd>${m.workingDirectory}</dd>
      <dt>PID</dt><dd>${m.pid || 'N/A'}</dd>
      <dt>Created</dt><dd>${formatTime(m.createdAt)}</dd>
      <dt>Updated</dt><dd>${formatTime(m.updatedAt)}</dd>
      ${m.tags.length ? `<dt>Tags</dt><dd>${tagsHtml}</dd>` : ''}
    </dl>
    ${checkpointsHtml}
    ${opsHtml}
  `;
}

function renderSessionsList(sessions) {
  const list = document.getElementById('sessions-list');

  if (sessions.length === 0) {
    list.innerHTML = '<p class="empty-state">No sessions found. Create one to get started.</p>';
    return;
  }

  list.innerHTML = sessions.map(s => {
    const age = formatAge(Date.now() - s.updatedAt);
    const tags = (s.tags || []).map(t => `<span class="tag">${t}</span>`).join(' ');

    return `
      <div class="session-card">
        <span class="session-id" title="${s.id}">${s.id}</span>
        <span class="badge badge-${s.status}">${s.status}</span>
        <div class="session-meta">
          <span>${s.checkpoints.length} checkpoint(s)</span>
          <span>${age}</span>
          ${tags}
        </div>
        <div class="session-card-actions">
          ${s.status !== 'active' ? `<button class="btn btn-sm btn-primary" onclick="teleportTo('${s.id}')">Teleport</button>` : ''}
          <button class="btn btn-sm btn-danger" onclick="deleteSession('${s.id}')">Delete</button>
        </div>
      </div>
    `;
  }).join('');
}

// --- Actions ---
async function refresh() {
  await Promise.all([loadSessions(), loadCurrentSession()]);
}

document.getElementById('btn-refresh').addEventListener('click', refresh);
document.getElementById('status-filter').addEventListener('change', loadSessions);

// New Session
document.getElementById('btn-new-session').addEventListener('click', () => {
  showModal(`
    <h3>New Session</h3>
    <div class="form-group">
      <label>Working Directory</label>
      <input id="input-dir" type="text" placeholder="${window.location.hostname}" value="">
    </div>
    <div class="form-group">
      <label>Tags (comma-separated)</label>
      <input id="input-tags" type="text" placeholder="e.g. feature, debug">
    </div>
    <div class="modal-actions">
      <button class="btn" onclick="hideModal()">Cancel</button>
      <button class="btn btn-primary" onclick="createSession()">Create</button>
    </div>
  `);
});

async function createSession() {
  const dir = document.getElementById('input-dir').value || process.cwd;
  const tags = document.getElementById('input-tags').value
    .split(',').map(t => t.trim()).filter(Boolean);
  hideModal();
  const data = await api('POST', '/api/sessions', { workingDirectory: dir || '.', tags });
  if (data.session) {
    toast('Session created', 'success');
  } else {
    toast(data.error || 'Failed to create session', 'error');
  }
  refresh();
}

// Checkpoint
document.getElementById('btn-checkpoint').addEventListener('click', () => {
  showModal(`
    <h3>Create Checkpoint</h3>
    <div class="form-group">
      <label>Context Notes</label>
      <textarea id="input-context" placeholder="What's the current state?"></textarea>
    </div>
    <div class="modal-actions">
      <button class="btn" onclick="hideModal()">Cancel</button>
      <button class="btn btn-primary" onclick="createCheckpoint()">Save Checkpoint</button>
    </div>
  `);
});

async function createCheckpoint() {
  const context = document.getElementById('input-context').value
    .split('\n').filter(Boolean);
  hideModal();
  const data = await api('POST', '/api/sessions/checkpoint', { state: { manual: true }, context });
  if (data.checkpoint) {
    toast('Checkpoint created: ' + data.checkpoint.id, 'success');
  } else {
    toast(data.error || 'Failed', 'error');
  }
  refresh();
}

// Add Operation
document.getElementById('btn-add-operation').addEventListener('click', () => {
  showModal(`
    <h3>Add Pending Operation</h3>
    <div class="form-group">
      <label>Type</label>
      <input id="input-op-type" type="text" placeholder="e.g. build, deploy, test">
    </div>
    <div class="form-group">
      <label>Description</label>
      <input id="input-op-desc" type="text" placeholder="What needs to be done?">
    </div>
    <div class="modal-actions">
      <button class="btn" onclick="hideModal()">Cancel</button>
      <button class="btn btn-primary" onclick="addOperation()">Add</button>
    </div>
  `);
});

async function addOperation() {
  const type = document.getElementById('input-op-type').value || 'task';
  const description = document.getElementById('input-op-desc').value;
  hideModal();
  const data = await api('POST', '/api/sessions/operations', { type, description, state: {} });
  if (data.operation) {
    toast('Operation added', 'success');
  } else {
    toast(data.error || 'Failed', 'error');
  }
  refresh();
}

async function completeOperation(opId) {
  const data = await api('DELETE', '/api/sessions/operations/' + opId);
  if (data.success) {
    toast('Operation completed', 'success');
  } else {
    toast(data.error || 'Failed', 'error');
  }
  refresh();
}

// Suspend / Recoverable / Terminate
document.getElementById('btn-suspend').addEventListener('click', async () => {
  const data = await api('POST', '/api/sessions/suspend');
  toast(data.message || data.error, data.success ? 'success' : 'error');
  refresh();
});

document.getElementById('btn-recoverable').addEventListener('click', async () => {
  const data = await api('POST', '/api/sessions/recoverable');
  toast(data.message || data.error, data.success ? 'success' : 'error');
  refresh();
});

document.getElementById('btn-terminate').addEventListener('click', async () => {
  const data = await api('POST', '/api/sessions/terminate');
  toast(data.message || data.error, data.success ? 'success' : 'error');
  refresh();
});

// Teleport
async function teleportTo(sessionId) {
  showModal(`
    <h3>Teleport to Session</h3>
    <p style="color: var(--text-muted); font-size: 13px; margin-bottom: 14px;">
      Recover and resume session <code>${sessionId}</code>
    </p>
    <div class="form-group">
      <label>Target Checkpoint (optional)</label>
      <input id="input-checkpoint" type="text" placeholder="Leave empty for latest">
    </div>
    <div class="form-group">
      <div class="checkbox-row">
        <input id="input-force" type="checkbox">
        <label for="input-force">Force (override active/terminated status)</label>
      </div>
    </div>
    <div class="modal-actions">
      <button class="btn" onclick="hideModal()">Cancel</button>
      <button class="btn btn-primary" onclick="executeTeleport('${sessionId}')">Teleport</button>
    </div>
  `);
}

async function executeTeleport(sessionId) {
  const targetCheckpoint = document.getElementById('input-checkpoint').value || undefined;
  const force = document.getElementById('input-force').checked;
  hideModal();
  const data = await api('POST', '/api/teleport', { sessionId, targetCheckpoint, force });
  if (data.success) {
    toast('Teleported to ' + sessionId, 'success');
    if (data.warnings && data.warnings.length) {
      data.warnings.forEach(w => toast(w, 'info'));
    }
  } else {
    toast(data.error || 'Teleport failed', 'error');
  }
  refresh();
}

// Delete session
async function deleteSession(sessionId) {
  if (!confirm('Delete session ' + sessionId + '?')) return;
  const data = await api('DELETE', '/api/sessions/' + sessionId);
  if (data.success) {
    toast('Session deleted', 'success');
  } else {
    toast(data.error || 'Failed', 'error');
  }
  refresh();
}

// --- Init ---
refresh();
// Auto-refresh every 5 seconds
setInterval(refresh, 5000);
