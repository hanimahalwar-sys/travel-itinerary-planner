import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, CATEGORY_ICON, fmtDate, money } from "../api.js";

const CATEGORIES = Object.keys(CATEGORY_ICON);

const sum = (xs) => xs.reduce((n, x) => n + (Number(x) || 0), 0);

// Mirrors the backend's recompute so totals update instantly while editing.
function recompute(itin) {
  const days = itin.days.map((d) => ({
    ...d,
    day_cost: sum(d.activities.map((a) => a.cost)) + (Number(d.stay_cost) || 0) + (Number(d.transport_cost) || 0),
  }));
  return { ...itin, days, total_cost: sum(days.map((d) => d.day_cost)) };
}

function fmtDuration(min) {
  if (!min) return "";
  const h = Math.floor(min / 60);
  const m = min % 60;
  return h ? (m ? `${h}h ${m}m` : `${h}h`) : `${m}m`;
}

function ActivityRow({ a, currency, editing, onEdit, onChange, onDone, onRemove }) {
  if (editing) {
    return (
      <li className="activity editing">
        <div className="edit-grid">
          <label className="field">
            <span>Time</span>
            <input type="time" value={a.time} onChange={(e) => onChange({ time: e.target.value })} />
          </label>
          <label className="field grow">
            <span>Title</span>
            <input value={a.title} maxLength={160} onChange={(e) => onChange({ title: e.target.value })} />
          </label>
          <label className="field">
            <span>Category</span>
            <select value={a.category} onChange={(e) => onChange({ category: e.target.value })}>
              {CATEGORIES.map((c) => (
                <option key={c}>{c}</option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Cost ({currency})</span>
            <input type="number" min={0} value={a.cost} onChange={(e) => onChange({ cost: Math.max(0, Number(e.target.value) || 0) })} />
          </label>
          <label className="field">
            <span>Minutes</span>
            <input
              type="number"
              min={0}
              max={1440}
              value={a.duration_min}
              onChange={(e) => onChange({ duration_min: Math.min(1440, Math.max(0, Number(e.target.value) || 0)) })}
            />
          </label>
        </div>
        <label className="field">
          <span>Notes</span>
          <textarea rows={2} value={a.description} onChange={(e) => onChange({ description: e.target.value })} />
        </label>
        <div className="row-actions">
          <button className="btn primary small" onClick={onDone}>
            Done
          </button>
          <button className="btn ghost danger small" onClick={onRemove}>
            Remove
          </button>
        </div>
      </li>
    );
  }
  return (
    <li className="activity">
      <div className="act-time">{a.time}</div>
      <div className="act-icon" title={a.category}>
        {CATEGORY_ICON[a.category] || "📍"}
      </div>
      <div className="act-body">
        <div className="act-title">{a.title}</div>
        {a.description && <div className="act-desc">{a.description}</div>}
        <div className="act-meta">
          {fmtDuration(a.duration_min)} · <span className="cat">{a.category}</span>
        </div>
      </div>
      <div className="act-cost">{money(currency, a.cost)}</div>
      <button className="btn ghost small no-print" onClick={onEdit}>
        Edit
      </button>
    </li>
  );
}

export default function ItineraryView() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [trip, setTrip] = useState(null);
  const [itin, setItin] = useState(null);
  const [title, setTitle] = useState("");
  const [dirty, setDirty] = useState(false);
  const [dayNo, setDayNo] = useState(1);
  const [editingId, setEditingId] = useState(null);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [instruction, setInstruction] = useState("");
  const [aiMode, setAiMode] = useState("builtin");

  useEffect(() => {
    api
      .getTrip(id)
      .then((t) => {
        setTrip(t);
        setItin(t.itinerary);
        setTitle(t.title);
      })
      .catch((e) => setError(e.message));
    api.health().then((h) => setAiMode(h.ai_mode)).catch(() => {});
  }, [id]);

  // Warn before closing the tab with unsaved edits
  useEffect(() => {
    if (!dirty) return undefined;
    const handler = (e) => {
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [dirty]);

  const day = useMemo(() => itin?.days.find((d) => d.day === dayNo) || itin?.days[0], [itin, dayNo]);

  if (error && !trip) {
    return (
      <div>
        <div className="banner error">{error}</div>
        <Link to="/" className="btn">
          ← Back to dashboard
        </Link>
      </div>
    );
  }
  if (!trip || !itin || !day) return <p className="muted">Loading itinerary…</p>;

  const { request } = trip;
  const cur = request.currency;
  const pct = Math.min(100, Math.round((itin.total_cost / request.budget) * 100));
  const over = itin.total_cost > request.budget;

  function edit(mutator) {
    setItin((prev) => recompute(mutator(prev)));
    setDirty(true);
    setNotice("");
  }

  const patchDay = (patch) =>
    edit((p) => ({ ...p, days: p.days.map((d) => (d.day === day.day ? { ...d, ...patch } : d)) }));

  const patchActivity = (actId, patch) =>
    edit((p) => ({
      ...p,
      days: p.days.map((d) =>
        d.day === day.day ? { ...d, activities: d.activities.map((a) => (a.id === actId ? { ...a, ...patch } : a)) } : d
      ),
    }));

  const removeActivity = (actId) => {
    edit((p) => ({
      ...p,
      days: p.days.map((d) => (d.day === day.day ? { ...d, activities: d.activities.filter((a) => a.id !== actId) } : d)),
    }));
    setEditingId(null);
  };

  const sortDay = () => {
    setEditingId(null);
    setItin((p) => ({
      ...p,
      days: p.days.map((d) =>
        d.day === day.day ? { ...d, activities: [...d.activities].sort((a, b) => a.time.localeCompare(b.time)) } : d
      ),
    }));
  };

  const addActivity = () => {
    const newId = Math.random().toString(16).slice(2, 10);
    edit((p) => ({
      ...p,
      days: p.days.map((d) =>
        d.day === day.day
          ? {
              ...d,
              activities: [
                ...d.activities,
                { id: newId, time: "12:00", title: "New activity", category: "sightseeing", description: "", cost: 0, duration_min: 60 },
              ],
            }
          : d
      ),
    }));
    setEditingId(newId);
  };

  async function save() {
    setBusy("save");
    setError("");
    try {
      const t = await api.updateTrip(id, { title: title.trim() || trip.title, itinerary: itin });
      setTrip(t);
      setItin(t.itinerary);
      setTitle(t.title);
      setDirty(false);
      setNotice("Saved.");
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy("");
    }
  }

  async function regenerate(kind) {
    const what = kind === "day" ? `Day ${day.day}` : "the whole trip";
    if (dirty && !window.confirm(`You have unsaved edits. Regenerating ${what} will discard them. Continue?`)) return;
    if (kind === "trip" && !window.confirm("Replace every day with a freshly generated plan?")) return;
    setBusy(kind);
    setError("");
    try {
      const t =
        kind === "day" ? await api.regenerateDay(id, day.day, instruction.trim()) : await api.regenerateTrip(id);
      setTrip(t);
      setItin(t.itinerary);
      setDirty(false);
      setEditingId(null);
      setNotice(kind === "day" ? `Day ${day.day} regenerated.` : "Trip regenerated.");
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy("");
    }
  }

  async function remove() {
    if (!window.confirm("Delete this trip permanently?")) return;
    try {
      await api.deleteTrip(id);
      navigate("/");
    } catch (e) {
      setError(e.message);
    }
  }

  return (
    <div>
      <header className="page-head">
        <div className="grow">
          <Link to="/" className="back no-print">
            ← All trips
          </Link>
          <input
            className="title-input"
            value={title}
            aria-label="Trip title"
            onChange={(e) => {
              setTitle(e.target.value);
              setDirty(true);
            }}
          />
          <p className="muted">
            {fmtDate(request.start_date)} → {fmtDate(request.end_date)} · {request.travelers} traveler
            {request.travelers > 1 ? "s" : ""} · {request.travel_style} pace ·{" "}
            <span className="chip small">{itin.generated_by === "llm" ? "AI generated" : "Built-in planner"}</span>
          </p>
        </div>
        <div className="head-actions no-print">
          <button className="btn" onClick={() => window.print()}>
            Print
          </button>
          <button className="btn" disabled={!!busy} onClick={() => regenerate("trip")}>
            {busy === "trip" ? "Regenerating…" : "Regenerate trip"}
          </button>
          <button className="btn primary" disabled={!dirty || !!busy} onClick={save}>
            {busy === "save" ? "Saving…" : dirty ? "Save changes" : "Saved"}
          </button>
        </div>
      </header>

      {error && <div className="banner error">{error}</div>}
      {notice && <div className="banner ok">{notice}</div>}

      <section className="card summary">
        <p>{itin.summary}</p>
        <div className="budget">
          <div className="budget-top">
            <span>
              Estimated cost <strong className={over ? "over" : ""}>{money(cur, itin.total_cost)}</strong>
            </span>
            <span className="muted">Budget {money(cur, request.budget)}</span>
          </div>
          <div className="bar" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
            <div className={`bar-fill ${over ? "over" : ""}`} style={{ width: `${pct}%` }} />
          </div>
          {over && <div className="over-note">Over budget by {money(cur, itin.total_cost - request.budget)}</div>}
        </div>
      </section>

      <div className="tabs no-print" role="tablist">
        {itin.days.map((d) => (
          <button
            key={d.day}
            role="tab"
            aria-selected={d.day === day.day}
            className={d.day === day.day ? "active" : ""}
            onClick={() => {
              setDayNo(d.day);
              setEditingId(null);
            }}
          >
            <strong>Day {d.day}</strong>
            <small>{fmtDate(d.date, { day: "numeric", month: "short" })}</small>
          </button>
        ))}
      </div>

      <section className="card day">
        <div className="day-head">
          <div>
            <h2>
              Day {day.day}: {day.theme}
            </h2>
            <p className="muted">
              {fmtDate(day.date, { weekday: "long", day: "numeric", month: "long" })} · {money(cur, day.day_cost)} for the day
            </p>
          </div>
          <div className="day-regen no-print">
            {aiMode === "llm" && (
              <input
                placeholder="Optional: e.g. more outdoors"
                value={instruction}
                maxLength={300}
                onChange={(e) => setInstruction(e.target.value)}
              />
            )}
            <button className="btn" disabled={!!busy} onClick={() => regenerate("day")}>
              {busy === "day" ? "Regenerating…" : `Regenerate Day ${day.day}`}
            </button>
          </div>
        </div>

        <ul className="activities">
          {day.activities.map((a) => (
            <ActivityRow
              key={a.id}
              a={a}
              currency={cur}
              editing={editingId === a.id}
              onEdit={() => setEditingId(a.id)}
              onChange={(patch) => patchActivity(a.id, patch)}
              onDone={sortDay}
              onRemove={() => removeActivity(a.id)}
            />
          ))}
        </ul>
        <button className="btn ghost no-print" onClick={addActivity}>
          ＋ Add activity
        </button>

        <div className="logistics">
          <div className="logi">
            <div className="logi-label">🛏️ Stay</div>
            <div>{day.stay_name || "No overnight stay (departure day)"}</div>
            {day.stay_name && (
              <label className="inline-cost no-print">
                {cur}
                <input
                  type="number"
                  min={0}
                  value={day.stay_cost}
                  aria-label="Stay cost"
                  onChange={(e) => patchDay({ stay_cost: Math.max(0, Number(e.target.value) || 0) })}
                />
              </label>
            )}
          </div>
          <div className="logi">
            <div className="logi-label">🚕 Getting around</div>
            <div>{day.transport_tip}</div>
            <label className="inline-cost no-print">
              {cur}
              <input
                type="number"
                min={0}
                value={day.transport_cost}
                aria-label="Transport cost"
                onChange={(e) => patchDay({ transport_cost: Math.max(0, Number(e.target.value) || 0) })}
              />
            </label>
          </div>
        </div>
      </section>

      {itin.tips.length > 0 && (
        <section className="card tips">
          <h3>Good to know</h3>
          <ul>
            {itin.tips.map((t, i) => (
              <li key={i}>{t}</li>
            ))}
          </ul>
        </section>
      )}

      <div className="danger-zone no-print">
        <button className="btn ghost danger" onClick={remove}>
          Delete trip
        </button>
      </div>
    </div>
  );
}
