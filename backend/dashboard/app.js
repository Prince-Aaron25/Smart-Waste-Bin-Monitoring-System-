
"use strict";

const $ = id => document.getElementById(id);

let apiKey = "",
    deviceId = 1,
    refreshInProgress = false;

const dialog = $("authDialog");

$("settings").addEventListener("click", () => {
  $("deviceInput").value = deviceId;
  dialog.showModal();
});

$("cancel").addEventListener("click", () => {
  dialog.close();
});

$("authForm").addEventListener("submit", event => {
  event.preventDefault();

  apiKey = $("keyInput").value.trim();
  deviceId = Number($("deviceInput").value);

  $("keyInput").value = "";
  $("footerDevice").textContent = deviceId;

  dialog.close();
  refresh();
});

async function getJSON(path) {
  const response = await fetch(path, {
    headers: {
      "X-API-Key": apiKey
    },
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error(
      `${response.status} ${response.statusText} at ${path}`
    );
  }

  return response.json();
}

function stamp(value) {
  if (!value) {
    return "Unknown";
  }

  // SQLite CURRENT_TIMESTAMP values are UTC.
  const iso = value.includes("T")
    ? value
    : value.replace(" ", "T") + "Z";

  const d = new Date(iso);

  return Number.isNaN(d.getTime())
    ? value
    : d.toLocaleString();
}

function setConnection(online) {
  $("connection").className =
    "connection " + (online ? "online" : "offline");

  $("connection").textContent = online
    ? "● Device online"
    : "● Device offline";
}

function showReading(reading) {
  const percent = Number(reading.fill_percentage || 0),
        status = String(
          reading.fill_status || "low"
        ).toLowerCase();

  $("percentage").textContent = `${Math.round(percent)}%`;

  $("distance").textContent = Number(
    reading.clean_distance_cm
  ).toFixed(2);

  $("fillLabel").textContent = ({
    full: "Bin is full",
    half: "Half filled",
    low: "Low fill level"
  })[status] || status;

  $("lastUpdated").textContent =
    "Recorded: " + stamp(reading.recorded_at);

  $("fillTag").textContent = status.toUpperCase();

  $("fillTag").className = "tag " + status;

  $("gauge").style.setProperty(
    "--percent",
    Math.min(100, Math.max(0, percent))
  );

  $("gauge").style.setProperty(
    "--gauge-color",
    status === "full"
      ? "#e6795d"
      : status === "half"
        ? "#e8b349"
        : "#26b98e"
  );
}

async function resolveAlert(alertId, button) {
  if (
    !apiKey ||
    !window.confirm(
      `Mark alert #${alertId} as resolved?`
    )
  ) {
    return;
  }

  button.disabled = true;
  button.textContent = "Saving...";

  try {
    const response = await fetch(
      `/api/alerts/${encodeURIComponent(alertId)}/resolve?device_id=${encodeURIComponent(deviceId)}`,
      {
        method: "PATCH",
        headers: {
          "X-API-Key": apiKey
        },
        cache: "no-store"
      }
    );

    if (!response.ok) {
      let detail = response.statusText;

      try {
        detail = (await response.json()).detail || detail;
      } catch (_) {}

      throw new Error(
        `${response.status}: ${detail}`
      );
    }

    await refresh();

  } catch (error) {
    $("notice").hidden = false;

    $("notice").textContent =
      `Unable to resolve alert #${alertId}: ${error.message}`;

    button.disabled = false;
    button.textContent = "Resolve";
  }
}

function showAlerts(alerts) {
  const unresolved = alerts.filter(
    a => a.alert_type === "FULL_BIN" && !a.is_resolved
  );

  $("alertCount").textContent = unresolved.length;

  $("alertsLabel").textContent =
    `${alerts.length} TOTAL`;

  const list = $("alertList");

  list.replaceChildren();

  if (!alerts.length) {
    const p = document.createElement("p");

    p.className = "empty";
    p.textContent = "No alerts recorded.";

    list.append(p);
    return;
  }

  for (const a of alerts.slice(0, 12)) {
    const row = document.createElement("div");

    row.className = "alert-item";

    const ico = document.createElement("span");

    ico.className = "alert-icon";
    ico.textContent = "⚑";

    const desc = document.createElement("div");

    desc.className = "alert-text";

    const title = document.createElement("strong");

    title.textContent = a.message || a.alert_type;

    const meta = document.createElement("small");

    meta.textContent =
      `Alert #${a.alert_id} · ${stamp(a.created_at)}`;

    desc.append(title, meta);

    const state = document.createElement("span");

    state.className =
      "alert-status" + (a.is_resolved ? " resolved" : "");

    state.textContent = a.is_resolved
      ? "Resolved"
      : "Open";

    row.append(ico, desc, state);

    if (!a.is_resolved) {
      const button = document.createElement("button");

      button.type = "button";
      button.className = "resolve-btn";
      button.textContent = "Resolve";

      button.setAttribute(
        "aria-label",
        `Resolve alert ${a.alert_id}`
      );

      button.addEventListener(
        "click",
        () => resolveAlert(a.alert_id, button)
      );

      row.append(button);
    }

    list.append(row);
  }
}

function showChart(readings) {
  const canvas = $("historyChart"),
        ctx = canvas.getContext("2d");

  const w = canvas.clientWidth || 500,
        h = canvas.clientHeight || 245;

  const scale = window.devicePixelRatio || 1;

  canvas.width = Math.round(w * scale);
  canvas.height = Math.round(h * scale);

  ctx.setTransform(
    scale,
    0,
    0,
    scale,
    0,
    0
  );

  ctx.clearRect(0, 0, w, h);

  const pad = 12,
        plotH = h - 24;

  for (let i = 0; i <= 4; i++) {
    const y = pad + i * plotH / 4;

    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(w, y);

    ctx.strokeStyle = "#e8efeb";
    ctx.lineWidth = 1;

    ctx.stroke();
  }

  const data = [...readings].reverse();

  $("sampleCount").textContent =
    `${data.length} readings`;

  if (!data.length) {
    return;
  }

  const x = i =>
    data.length === 1
      ? w / 2
      : i * (w - 12) / (data.length - 1) + 6;

  const y = v =>
    pad +
    (100 - Math.max(0, Math.min(100, Number(v)))) *
    plotH / 100;

  ctx.beginPath();

  data.forEach((r, i) =>
    i
      ? ctx.lineTo(x(i), y(r.fill_percentage))
      : ctx.moveTo(x(i), y(r.fill_percentage))
  );

  ctx.strokeStyle = "#1ca681";
  ctx.lineWidth = 2.5;
  ctx.lineJoin = "round";

  ctx.stroke();

  data.forEach((r, i) => {
    ctx.beginPath();

    ctx.arc(
      x(i),
      y(r.fill_percentage),
      2.8,
      0,
      Math.PI * 2
    );

    ctx.fillStyle = "#1ca681";
    ctx.fill();
  });
}

async function refresh() {
  if (!apiKey || refreshInProgress) {
    return;
  }

  refreshInProgress = true;

  try {
    const suffix =
      `device_id=${encodeURIComponent(deviceId)}`;

    const [
      latest,
      history,
      alerts,
      device
    ] = await Promise.all([
      getJSON(`/api/readings/latest?${suffix}`),
      getJSON(`/api/readings/history?${suffix}&limit=40`),
      getJSON(`/api/alerts?${suffix}`),
      getJSON(`/api/devices/status?${suffix}`)
    ]);

    showReading(latest);
    showChart(history);
    showAlerts(alerts);

    setConnection(Boolean(device.online));

    $("deviceStatus").textContent = device.online
      ? "ONLINE"
      : "OFFLINE";

    $("deviceName").textContent =
      device.device_name || `Device #${deviceId}`;

    $("lastSeen").textContent =
      "Last seen: " + stamp(device.last_seen);

    $("notice").hidden = true;

  } catch (error) {
    $("notice").hidden = false;

    $("notice").textContent =
      `Unable to load dashboard: ${error.message}. Check your API key, device ID, and FastAPI server.`;

    setConnection(false);

  } finally {
    refreshInProgress = false;
  }
}

window.addEventListener("resize", () => {
  if (apiKey) {
    refresh();
  }
});

setInterval(refresh, 1000);

dialog.showModal();
