// Data layer: talks to the FastAPI backend (PostgreSQL). Same small interface the UI already uses:
//   collection(name).onSnapshot(cb, onError), collection(name).doc(id).set(value) / .delete(), refresh()
const NAMES = ["projects", "packages", "suppliers", "notes"];
const listeners = {};
const errorHandlers = [];
let cache = null, started = false, running = null, dirty = false;

async function api(method, url, body) {
  const r = await fetch(url, { method, headers: { "Content-Type": "application/json" },
                               body: body === undefined ? undefined : JSON.stringify(body) });
  if (!r.ok) {
    let msg = r.statusText;
    try { const j = await r.json(); msg = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail); } catch (e) {}
    throw new Error(msg || "HTTP " + r.status);
  }
  return r.json();
}
const snapshot = (n) => ({ docs: (cache[n] || []).map((d) => ({ id: d.id, data: () => d })) });
const notify = (n) => cache && (listeners[n] || []).forEach((cb) => cb(snapshot(n)));
let lastJson = null;
async function load() {
  const data = await api("GET", "/api/all"), j = JSON.stringify(data);
  if (j === lastJson) return;            // nothing changed: skip the redraw (keeps typing intact)
  lastJson = j; cache = data; NAMES.forEach(notify);
}

function refresh() {            // coalesces bursts of writes into as few reloads as possible
  if (running) { dirty = true; return running; }
  running = (async () => { do { dirty = false; await load(); } while (dirty); })().finally(() => (running = null));
  return running;
}
async function ensureStarted() {
  if (started) return;
  started = true;
  try { await load(); } catch (e) { started = false; errorHandlers.forEach((f) => f(e)); }
}
const uuid = () => (crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).slice(2) + Date.now().toString(36));

export function createStore() {
  setInterval(() => { if (!document.hidden && cache) refresh().catch(() => {}); }, 30000);   // pick up other users' edits
  return {
    refresh,
    collection(name) {
      return {
        onSnapshot(cb, onError) {
          (listeners[name] ||= []).push(cb);
          if (onError) errorHandlers.push(onError);
          if (cache) cb(snapshot(name)); else ensureStarted();
        },
        doc(id = uuid()) {
          return {
            id,
            async set(value) { await api("PUT", `/api/${name}/${id}`, value); await refresh(); },
            async delete() { await api("DELETE", `/api/${name}/${id}`); await refresh(); },
          };
        },
      };
    },
  };
}

export function downloadFile(filename, text) {
  const url = URL.createObjectURL(new Blob([text], { type: "text/csv" }));
  const a = Object.assign(document.createElement("a"), { href: url, download: filename });
  document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
}
