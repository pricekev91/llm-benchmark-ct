// ── LLM Benchmark CT — Single Page Application ──

const API = {
  base: '', // same origin
  key: '',
  // Detect key from localStorage or prompt
  init() {
    this.key = localStorage.getItem('api_key') || '';
    if (!this.key) {
      const input = prompt('Enter API Key (from deploy config):') || '';
      if (input) { localStorage.setItem('api_key', input); this.key = input; }
    }
  },
  headers() {
    const h = { 'Content-Type': 'application/json' };
    if (this.key) h['X-API-KEY'] = this.key;
    return h;
  },
  async get(path) {
    const res = await fetch(path, { headers: this.headers() });
    if (res.status === 401) {
      const newKey = prompt('API Key expired or invalid. Enter new key:');
      if (newKey) { localStorage.setItem('api_key', newKey); this.key = newKey; }
      return this.get(path);
    }
    return res.json();
  },
  async post(path, body) {
    const res = await fetch(path, { method: 'POST', headers: this.headers(), body: JSON.stringify(body) });
    return res.json();
  },
  async del(path) {
    const res = await fetch(path, { method: 'DELETE', headers: this.headers() });
    return res.json();
  },
  async health() {
    try { const r = await fetch('/health'); return r.ok; } catch { return false; }
  }
};

API.init();

// ── State ──
const state = {
  endpoints: [],
  models: [],
  presets: [],
  recentRuns: [],
  loading: false,
};

// ── Navigation ──
document.querySelectorAll('.nav-links button').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.nav-links button').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    navigateTo(btn.dataset.page);
  });
});

function navigateTo(page) {
  document.querySelectorAll('.nav-links button').forEach(b => {
    b.classList.toggle('active', b.dataset.page === page);
  });
  const router = {
    dashboard: renderDashboard,
    endpoints: renderEndpoints,
    runner: renderRunner,
    history: renderHistory,
    comparison: renderComparison,
  };
  (router[page] || renderDashboard)();
}

// ── Toast ──
function toast(msg, type = 'success') {
  const t = document.createElement('div');
  t.className = `toast toast-${type}`;
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 3000);
}

// ── Data Loading ──
async function loadAllData() {
  try {
    [state.endpoints, state.presets, state.recentRuns] = await Promise.all([
      API.get('/endpoints/list').then(d => d.endpoints || []),
      API.get('/presets/list').then(d => d.presets || []),
      API.get('/analytics/history/filter?limit=20').then(d => d.runs || []),
    ]);
    state.models = await API.get('/endpoints/models/list').then(d => d.models || []);
  } catch (e) {
    console.error('Failed to load data:', e);
  }
}

// ── Status Check ──
async function checkStatus() {
  const ok = await API.health();
  document.getElementById('statusDot').className = `dot ${ok ? 'connected' : 'disconnected'}`;
  document.getElementById('statusText').textContent = ok ? 'Connected' : 'Disconnected';
}
setInterval(checkStatus, 10000);
checkStatus();

// ── Pages ──

// ═══ DASHBOARD ═══
async function renderDashboard() {
  await loadAllData();

  const totalRuns = state.recentRuns.length;
  const avgLatency = totalRuns ? Math.round(state.recentRuns.reduce((s, r) => s + (r.latency_ms || 0), 0) / totalRuns) : 0;
  const bestLatency = totalRuns ? Math.round(Math.min(...state.recentRuns.map(r => r.latency_ms || Infinity))) : 0;
  const avgTokens = totalRuns ? Math.round(state.recentRuns.reduce((s, r) => s + (r.tokens_generated || 0), 0) / totalRuns) : 0;

  document.getElementById('app').innerHTML = `
    <h1 class="page-title">Dashboard</h1>
    <p class="subtitle">Overview of your benchmarking activity</p>

    <div class="metric-grid">
      <div class="card">
        <h3>Total Runs</h3>
        <div class="value">${totalRuns}</div>
        <div class="unit">benchmark executions</div>
      </div>
      <div class="card">
        <h3>Avg Latency</h3>
        <div class="value">${avgLatency}</div>
        <div class="unit">milliseconds</div>
      </div>
      <div class="card">
        <h3>Best Latency</h3>
        <div class="value">${bestLatency}</div>
        <div class="unit">milliseconds</div>
      </div>
      <div class="card">
        <h3>Avg Tokens</h3>
        <div class="value">${avgTokens}</div>
        <div class="unit">tokens / run</div>
      </div>
      <div class="card">
        <h3>Endpoints</h3>
        <div class="value">${state.endpoints.length}</div>
        <div class="unit">configured</div>
      </div>
      <div class="card">
        <h3>Models</h3>
        <div class="value">${state.models.length}</div>
        <div class="unit">available</div>
      </div>
    </div>

    <h2 class="section-title">Recent Runs</h2>
    ${state.recentRuns.length === 0 ? `
      <div class="card empty-state">
        <div class="icon">📊</div>
        <p>No benchmark runs yet. Go to the <a href="#" onclick="navigateTo('runner')">Runner</a> to get started.</p>
      </div>
    ` : `
      <div class="table-wrap">
        <table>
          <thead><tr><th>Model</th><th>Endpoint</th><th>Latency</th><th>Tokens</th><th>Throughput</th><th>Time</th></tr></thead>
          <tbody>
            ${state.recentRuns.slice(0, 10).map(r => `
              <tr>
                <td><span class="badge badge-blue">${esc(r.model_name)}</span></td>
                <td>${esc(r.endpoint_id)}</td>
                <td>${r.latency_ms ? r.latency_ms.toFixed(0) + ' ms' : '—'}</td>
                <td>${r.tokens_generated || '—'}</td>
                <td>${r.throughput_tps ? r.throughput_tps.toFixed(1) + '/s' : '—'}</td>
                <td>${r.timestamp ? new Date(r.timestamp).toLocaleString() : '—'}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `}
  `;
}

// ═══ ENDPOINTS ═══
async function renderEndpoints() {
  await loadAllData();

  document.getElementById('app').innerHTML = `
    <h1 class="page-title">Endpoints</h1>
    <p class="subtitle">Configure LLM API endpoints for benchmarking</p>

    <div class="card">
      <h3>Add / Update Endpoint</h3>
      <div class="form-group">
        <label>Name</label>
        <input type="text" id="epName" placeholder="My OpenAI Endpoint">
      </div>
      <div class="form-group">
        <label>Base URL</label>
        <input type="text" id="epUrl" placeholder="https://api.openai.com/v1">
      </div>
      <div class="form-group">
        <label>Provider</label>
        <select id="epProvider">
          <option value="OpenAI">OpenAI</option>
          <option value="llama.cpp">llama.cpp</option>
          <option value="vLLM">vLLM</option>
          <option value="LiteLLM">LiteLLM</option>
          <option value="llama-swap">llama-swap</option>
        </select>
      </div>
      <div class="form-group">
        <label>API Key (optional)</label>
        <input type="text" id="epKey" placeholder="sk-...">
      </div>
      <div class="btn-group">
        <button class="btn btn-primary" onclick="saveEndpoint()">Save Endpoint</button>
        <button class="btn" onclick="clearEndpointForm()">Clear</button>
      </div>
    </div>

    <h2 class="section-title">Configured Endpoints</h2>
    ${state.endpoints.length === 0 ? `
      <div class="card empty-state">
        <div class="icon">🔗</div>
        <p>No endpoints configured yet. Add one above to get started.</p>
      </div>
    ` : `
      <div class="table-wrap">
        <table>
          <thead><tr><th>ID</th><th>Name</th><th>URL</th><th>Provider</th><th>Actions</th></tr></thead>
          <tbody>
            ${state.endpoints.map(e => `
              <tr>
                <td><code>${esc(e.id)}</code></td>
                <td>${esc(e.name)}</td>
                <td><code>${esc(e.base_url)}</code></td>
                <td><span class="badge badge-green">${esc(e.provider)}</span></td>
                <td>
                  <button class="btn btn-sm btn-danger" onclick="deleteEndpoint('${esc(e.id)}')">Delete</button>
                </td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `}

    <h2 class="section-title" style="margin-top:24px">Available Models</h2>
    ${state.models.length === 0 ? `<p style="color:#8b949e">No models available. Configure an endpoint first.</p>` : `
      <div class="table-wrap">
        <table>
          <thead><tr><th>Model</th><th>Provider</th><th>Endpoint</th></tr></thead>
          <tbody>
            ${state.models.map(m => `
              <tr>
                <td><span class="badge badge-blue">${esc(m.name)}</span></td>
                <td>${esc(m.provider)}</td>
                <td>${esc(m.endpoint_id || '—')}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `}
  `;
}

async function saveEndpoint() {
  const name = document.getElementById('epName').value.trim();
  const url = document.getElementById('epUrl').value.trim();
  const provider = document.getElementById('epProvider').value;
  const key = document.getElementById('epKey').value.trim();
  if (!name || !url) { toast('Name and URL are required.', 'error'); return; }
  const id = name.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/_+/, '_');
  const res = await API.post('/endpoints/save', { id, name, base_url: url, provider, api_key: key });
  if (res.status === 'success') {
    toast(`Endpoint "${name}" saved.`);
    await loadAllData();
    renderEndpoints();
  } else {
    toast(res.message || 'Failed to save.', 'error');
  }
}

async function deleteEndpoint(id) {
  if (!confirm(`Delete endpoint "${id}"?`)) return;
  await API.del(`/endpoints/${id}`);
  toast('Endpoint deleted.');
  await loadAllData();
  renderEndpoints();
}

function clearEndpointForm() {
  document.getElementById('epName').value = '';
  document.getElementById('epUrl').value = '';
  document.getElementById('epKey').value = '';
}

// ═══ BENCHMARK RUNNER ═══
async function renderRunner() {
  await loadAllData();

  const endpointOptions = state.endpoints.length === 0
    ? '<option value="">No endpoints — configure one first</option>'
    : state.endpoints.map(e => `<option value="${esc(e.id)}">${esc(e.name)} (${esc(e.base_url)})</option>`).join('');

  const presetOptions = state.presets.map(p => `<option value="${esc(p.id)}" data-template="${esc(p.template)}">${esc(p.name)} [${esc(p.category)}]</option>`).join('');

  document.getElementById('app').innerHTML = `
    <h1 class="page-title">Benchmark Runner</h1>
    <p class="subtitle">Configure inputs and run benchmarks against LLM endpoints</p>

    <div class="card">
      <h3>Configuration</h3>
      <div class="form-group">
        <label>Endpoint</label>
        <select id="runEndpoint">${endpointOptions}</select>
      </div>
      <div class="form-group">
        <label>Model</label>
        <input type="text" id="runModel" placeholder="e.g. gpt-4o, Llama-3-8B-Instruct">
      </div>
      <div class="form-group">
        <label>Max Tokens</label>
        <input type="number" id="runMaxTokens" value="1024" min="1" max="128000">
      </div>
      <div class="form-group">
        <label>Prompt</label>
        <textarea id="runPrompt" rows="6" placeholder="Enter your prompt here..."></textarea>
      </div>
      <div class="form-group">
        <label>Or load a preset</label>
        <select id="runPreset" onchange="loadPreset()">
          <option value="">-- Select Preset --</option>
          ${presetOptions}
        </select>
      </div>
      <button class="btn btn-primary" id="runBtn" onclick="runBenchmark()">▶ Run Benchmark</button>
    </div>

    <div id="runResults" class="hidden"></div>
  `;
}

function loadPreset() {
  const sel = document.getElementById('runPreset');
  const opt = sel.options[sel.selectedIndex];
  if (opt && opt.dataset.template) {
    document.getElementById('runPrompt').value = opt.dataset.template;
  }
}

async function runBenchmark() {
  const endpointId = document.getElementById('runEndpoint').value;
  const modelName = document.getElementById('runModel').value.trim();
  const prompt = document.getElementById('runPrompt').value.trim();
  const maxTokens = parseInt(document.getElementById('runMaxTokens').value) || 1024;

  if (!endpointId) { toast('Select an endpoint.', 'error'); return; }
  if (!modelName) { toast('Enter a model name.', 'error'); return; }
  if (!prompt) { toast('Enter a prompt.', 'error'); return; }

  const btn = document.getElementById('runBtn');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Running...';

  const resultsDiv = document.getElementById('runResults');
  resultsDiv.classList.remove('hidden');
  resultsDiv.innerHTML = `<div class="card"><p>Running benchmark... This may take a moment.</p><br><pre id="runOutput" style="min-height:60px;color:#8b949e">Starting...</pre></div>`;

  try {
    const res = await API.post('/benchmark/run', {
      endpoint_id: endpointId,
      model_id: modelName,
      model_name: modelName,
      prompt_text: prompt,
      max_tokens: maxTokens,
    });

    if (res.status === 'success') {
      const d = res.run_data;
      const m = res.metrics || {};
      resultsDiv.innerHTML = `
        <div class="card">
          <h3>✅ Benchmark Complete</h3>
          <div class="metric-grid">
            <div class="card">
              <h3>Latency</h3>
              <div class="value">${(d.latency_ms || 0).toFixed(0)}</div>
              <div class="unit">milliseconds</div>
            </div>
            <div class="card">
              <h3>Tokens</h3>
              <div class="value">${d.tokens_generated || '—'}</div>
              <div class="unit">generated</div>
            </div>
            <div class="card">
              <h3>Output Length</h3>
              <div class="value">${d.output_length || 0}</div>
              <div class="unit">characters</div>
            </div>
            <div class="card">
              <h3>Throughput</h3>
              <div class="value">${(d.throughput_tps || 0).toFixed(1)}</div>
              <div class="unit">tokens/sec</div>
            </div>
          </div>
          <h3 style="margin-top:16px">Response</h3>
          <pre>${esc(d.response_text || 'No response')}</pre>
        </div>
      `;
      toast('Benchmark completed.');
    } else {
      resultsDiv.innerHTML = `<div class="card"><h3 style="color:#f85149">❌ Benchmark Failed</h3><pre>${esc(JSON.stringify(res, null, 2))}</pre></div>`;
      toast('Benchmark failed.', 'error');
    }
  } catch (e) {
    resultsDiv.innerHTML = `<div class="card"><h3 style="color:#f85149">❌ Error</h3><pre>${esc(e.message)}</pre></div>`;
    toast('Request failed.', 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '▶ Run Benchmark';
  }

  // Refresh dashboard data
  await loadAllData();
}

// ═══ HISTORY ═══
async function renderHistory() {
  await loadAllData();

  const runs = state.recentRuns;

  document.getElementById('app').innerHTML = `
    <h1 class="page-title">History</h1>
    <p class="subtitle">Browse and filter past benchmark runs</p>

    <div class="card">
      <div class="filter-bar">
        <div class="form-group">
          <label>Model</label>
          <input type="text" id="filterModel" placeholder="Filter by model name...">
        </div>
        <div class="form-group">
          <label>Endpoint</label>
          <input type="text" id="filterEndpoint" placeholder="Filter by endpoint ID...">
        </div>
        <div class="form-group">
          <label>Limit</label>
          <input type="number" id="filterLimit" value="50" min="1" max="500">
        </div>
        <button class="btn btn-primary" onclick="applyFilters()">Apply</button>
      </div>
    </div>

    <div id="historyTable"></div>
  `;

  renderHistoryTable(runs);
}

function renderHistoryTable(runs) {
  const el = document.getElementById('historyTable');
  if (!el) return;

  if (runs.length === 0) {
    el.innerHTML = `<div class="card empty-state"><div class="icon">📊</div><p>No runs found.</p></div>`;
    return;
  }

  const avgLat = runs.reduce((s, r) => s + (r.latency_ms || 0), 0) / runs.length;
  const avgTok = runs.reduce((s, r) => s + (r.tokens_generated || 0), 0) / runs.length;

  el.innerHTML = `
    <div class="metric-grid">
      <div class="card"><h3>Runs Shown</h3><div class="value">${runs.length}</div></div>
      <div class="card"><h3>Avg Latency</h3><div class="value">${avgLat.toFixed(0)}</div><div class="unit">ms</div></div>
      <div class="card"><h3>Avg Tokens</h3><div class="value">${avgTok.toFixed(0)}</div></div>
    </div>
    <div class="table-wrap">
      <table>
        <thead><tr><th>Run ID</th><th>Model</th><th>Endpoint</th><th>Latency</th><th>Tokens</th><th>Throughput</th><th>Timestamp</th></tr></thead>
        <tbody>
          ${runs.map(r => `
            <tr>
              <td><code title="${esc(r.run_id)}">${esc(r.run_id).substring(0, 8)}...</code></td>
              <td><span class="badge badge-blue">${esc(r.model_name)}</span></td>
              <td>${esc(r.endpoint_id)}</td>
              <td>${r.latency_ms ? r.latency_ms.toFixed(0) + ' ms' : '—'}</td>
              <td>${r.tokens_generated || '—'}</td>
              <td>${r.throughput_tps ? r.throughput_tps.toFixed(1) + '/s' : '—'}</td>
              <td>${r.timestamp ? new Date(r.timestamp).toLocaleString() : '—'}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
  `;
}

async function applyFilters() {
  const model = document.getElementById('filterModel').value.trim();
  const endpoint = document.getElementById('filterEndpoint').value.trim();
  const limit = document.getElementById('filterLimit').value || '50';
  const params = new URLSearchParams();
  if (model) params.set('model_name', model);
  if (endpoint) params.set('endpoint_id', endpoint);
  params.set('limit', limit);

  const data = await API.get(`/analytics/history/filter?${params}`);
  renderHistoryTable(data.runs || []);
}

// ═══ COMPARISON ═══
async function renderComparison() {
  await loadAllData();

  // Get unique model names from recent runs
  const modelNames = [...new Set(state.recentRuns.map(r => r.model_name).filter(Boolean))];
  if (modelNames.length === 0) modelNames.push('');

  document.getElementById('app').innerHTML = `
    <h1 class="page-title">Comparison & Trends</h1>
    <p class="subtitle">Compare model performance and track trends over time</p>

    <div class="card">
      <h3>Select Model</h3>
      <div class="form-group">
        <select id="compareModel">
          <option value="">-- Pick a model --</option>
          ${modelNames.map(m => `<option value="${esc(m)}">${esc(m)}</option>`).join('')}
        </select>
      </div>
      <button class="btn btn-primary" onclick="loadComparison()">Load Comparison</button>
    </div>

    <div id="compareResults" class="hidden"></div>
  `;
}

async function loadComparison() {
  const modelName = document.getElementById('compareModel').value.trim();
  if (!modelName) { toast('Select a model.', 'error'); return; }

  const el = document.getElementById('compareResults');
  el.classList.remove('hidden');
  el.innerHTML = '<p>Loading...</p>';

  try {
    const [stats, trends] = await Promise.all([
      API.get(`/analytics/compare/run?model_name=${encodeURIComponent(modelName)}`),
      API.get(`/analytics/compare/trends?model_name=${encodeURIComponent(modelName)}`),
    ]);

    const s = stats.comparison || stats;

    el.innerHTML = `
      <div class="metric-grid">
        <div class="card"><h3>Total Runs</h3><div class="value">${s.total_runs || 0}</div></div>
        <div class="card"><h3>Avg Latency</h3><div class="value">${(s.avg_latency_ms || 0).toFixed(0)}</div><div class="unit">ms</div></div>
        <div class="card"><h3>Best Latency</h3><div class="value">${(s.best_latency_ms || 0).toFixed(0)}</div><div class="unit">ms</div></div>
        <div class="card"><h3>Worst Latency</h3><div class="value">${(s.worst_latency_ms || 0).toFixed(0)}</div><div class="unit">ms</div></div>
        <div class="card"><h3>Avg Throughput</h3><div class="value">${(s.avg_throughput_tps || 0).toFixed(1)}</div><div class="unit">tokens/s</div></div>
        <div class="card"><h3>Avg Tokens</h3><div class="value">${(s.avg_tokens || 0).toFixed(0)}</div></div>
      </div>

      ${trends.trends && trends.trends.length > 1 ? `
        <div class="card">
          <h3>Latency Trend (ms)</h3>
          <div class="chart-bar-wrap">
            ${(() => {
              const data = trends.trends;
              const maxVal = Math.max(...data.map(d => d.avg_latency || 1), 1);
              return data.map(d => {
                const h = Math.max(4, ((d.avg_latency || 0) / maxVal) * 160);
                return `<div class="chart-bar" style="height:${h}px" title="${d.date}: ${d.avg_latency} ms (${d.runs} runs)">
                  <span class="chart-bar-value">${(d.avg_latency || 0).toFixed(0)}</span>
                  <span class="chart-bar-label">${d.date ? d.date.substring(5) : ''}</span>
                </div>`;
              }).join('');
            })()}
          </div>
          <div style="height:24px"></div>
        </div>
      ` : `<p style="color:#8b949e;margin-top:16px">Not enough data for trends. Run more benchmarks.</p>`}
    `;
  } catch (e) {
    el.innerHTML = `<div class="card"><h3 style="color:#f85149">Error</h3><pre>${esc(e.message)}</pre></div>`;
  }
}

// ── Utility ──
function esc(str) {
  if (!str) return '';
  const d = document.createElement('div');
  d.textContent = String(str);
  return d.innerHTML;
}

// ── Init ──
navigateTo('dashboard');
