"use strict";

// Navigation-only enhancement. Existing app.js remains unchanged.
(() => {
  const nav = document.querySelector('.sidebar .nav');
  const main = document.querySelector('main');
  const title = document.querySelector('header h1');
  const subtitle = document.querySelector('header .sub');
  const historyCard = document.querySelector('.lower .history');
  if (!nav || !main || !title || !historyCard) return;

  const items = [
    { view: 'overview', label: '▦  Overview', title: 'Waste Bin Overview', sub: 'Live telemetry and alerts from your smart waste bin.' },
    { view: 'history', label: '▤  Sensor History', title: 'Sensor History', sub: 'Recorded ultrasonic readings from your SQLite database.' },
    { view: 'alerts', label: '♢  Alerts', title: 'Full-Bin Alerts', sub: 'View open and resolved alerts, and acknowledge new alerts.' }
  ];

  nav.replaceChildren();
  for (const item of items) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'nav-link';
    button.dataset.view = item.view;
    button.textContent = item.label;
    button.addEventListener('click', () => setView(item.view));
    nav.append(button);
  }

  const tableWrap = document.createElement('div');
  tableWrap.className = 'history-table-wrap';
  tableWrap.innerHTML = '<h3>Recent Sensor Readings</h3><div class="history-table-scroll"><table class="history-table"><thead><tr><th>Reading</th><th>Recorded at</th><th>Distance (cm)</th><th>Fill (%)</th><th>Status</th></tr></thead><tbody id="historyTableBody"><tr><td colspan="5">Connect your API to load readings.</td></tr></tbody></table></div>';
  historyCard.append(tableWrap);

  let currentView = 'overview';
  function setView(view) {
    const item = items.find(x => x.view === view) || items[0];
    currentView = item.view;
    document.body.dataset.view = currentView;
    title.textContent = item.title;
    subtitle.textContent = item.sub;
    nav.querySelectorAll('.nav-link').forEach(button => {
      const selected = button.dataset.view === currentView;
      button.classList.toggle('active', selected);
      button.setAttribute('aria-current', selected ? 'page' : 'false');
    });
    if (currentView === 'history') {
      loadHistory();
      // Canvas may have been hidden; repaint at its new visible size.
      if (typeof refresh === 'function') refresh();
    }
    window.scrollTo({ top: 0, behavior: 'instant' });
  }

  function displayDate(value) {
    if (!value) return '—';
    const iso = value.includes('T') ? value : value.replace(' ', 'T') + 'Z';
    const date = new Date(iso);
    return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
  }

  async function loadHistory() {
    if (currentView !== 'history' || !apiKey) return;
    const tbody = document.getElementById('historyTableBody');
    try {
      const response = await fetch(`/api/readings/history?device_id=${encodeURIComponent(deviceId)}&limit=40`, {
        headers: { 'X-API-Key': apiKey }, cache: 'no-store'
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const readings = await response.json();
      if (!Array.isArray(readings)) throw new Error('Unexpected history response');
      tbody.replaceChildren();
      if (!readings.length) {
        const tr = document.createElement('tr');
        const td = document.createElement('td'); td.colSpan = 5; td.textContent = 'No readings yet.';
        tr.append(td); tbody.append(tr); return;
      }
      for (const reading of readings) {
        const tr = document.createElement('tr');
        const values = [
          reading.reading_id ?? '—',
          displayDate(reading.recorded_at),
          reading.clean_distance_cm == null ? '—' : Number(reading.clean_distance_cm).toFixed(2),
          reading.fill_percentage == null ? '—' : Number(reading.fill_percentage).toFixed(2),
          String(reading.fill_status ?? '—').toUpperCase()
        ];
        for (const value of values) {
          const td = document.createElement('td');
          td.textContent = String(value);
          tr.append(td);
        }
        tbody.append(tr);
      }
    } catch (error) {
      tbody.replaceChildren();
      const tr = document.createElement('tr');
      const td = document.createElement('td'); td.colSpan = 5;
      td.textContent = `Could not load sensor history: ${error.message}`;
      tr.append(td); tbody.append(tr);
    }
  }

  document.getElementById('authForm')?.addEventListener('submit', () => {
    if (currentView === 'history') setTimeout(loadHistory, 0);
  });
  setInterval(loadHistory, 5000);
  setView('overview');
})();
