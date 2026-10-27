const BASE = import.meta.env.VITE_API_URL || "/api";

// Anonymous per-browser identity; the backend scopes every trip to this id.
function userId() {
  try {
    let id = localStorage.getItem("wayfarer_uid");
    if (!id) {
      id = (crypto.randomUUID?.() || String(Date.now()) + Math.random().toString(36).slice(2)).replace(/[^A-Za-z0-9_-]/g, "");
      localStorage.setItem("wayfarer_uid", id);
    }
    return id;
  } catch {
    return "anonymous-session";
  }
}

async function request(path, options = {}) {
  const res = await fetch(BASE + path, {
    ...options,
    headers: { "Content-Type": "application/json", "X-User-Id": userId(), ...(options.headers || {}) },
  });
  if (!res.ok) {
    let message = res.statusText || "Request failed";
    try {
      const body = await res.json();
      if (typeof body.detail === "string") message = body.detail;
      else if (Array.isArray(body.detail)) message = body.detail.map((d) => d.msg).join("; ");
    } catch {
      /* non-JSON error body */
    }
    throw new Error(message);
  }
  return res.status === 204 ? null : res.json();
}

export const api = {
  health: () => request("/health"),
  listTrips: () => request("/trips"),
  getTrip: (id) => request(`/trips/${id}`),
  createTrip: (payload) => request("/trips", { method: "POST", body: JSON.stringify(payload) }),
  updateTrip: (id, payload) => request(`/trips/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  deleteTrip: (id) => request(`/trips/${id}`, { method: "DELETE" }),
  regenerateTrip: (id) => request(`/trips/${id}/regenerate`, { method: "POST" }),
  regenerateDay: (id, day, instruction = "") =>
    request(`/trips/${id}/days/${day}/regenerate`, { method: "POST", body: JSON.stringify({ instruction }) }),
};

export function money(currency, amount) {
  try {
    return new Intl.NumberFormat(undefined, { style: "currency", currency, maximumFractionDigits: 0 }).format(amount || 0);
  } catch {
    return `${currency} ${Math.round(amount || 0).toLocaleString()}`;
  }
}

export function fmtDate(iso, opts = { day: "numeric", month: "short", year: "numeric" }) {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString(undefined, opts);
}

export const CATEGORY_ICON = {
  sightseeing: "🏛️",
  culture: "🎭",
  food: "🍽️",
  adventure: "🧗",
  nature: "🌿",
  shopping: "🛍️",
  nightlife: "🌙",
  relaxation: "🧖",
};
