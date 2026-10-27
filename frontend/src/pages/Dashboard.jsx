import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api, fmtDate, money } from "../api.js";

function Stat({ label, value, hint }) {
  return (
    <div className="stat">
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
      {hint && <div className="stat-hint">{hint}</div>}
    </div>
  );
}

export default function Dashboard() {
  const [trips, setTrips] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.listTrips().then(setTrips).catch((e) => setError(e.message));
  }, []);

  const stats = useMemo(() => {
    if (!trips) return null;
    const today = new Date().toISOString().slice(0, 10);
    const upcoming = trips.filter((t) => t.request.end_date >= today).length;
    const destinations = new Set(trips.map((t) => t.request.destination.trim().toLowerCase())).size;
    const days = trips.reduce((n, t) => n + t.itinerary.days.length, 0);
    return { total: trips.length, upcoming, destinations, days };
  }, [trips]);

  async function remove(id) {
    if (!window.confirm("Delete this trip? This can't be undone.")) return;
    try {
      await api.deleteTrip(id);
      setTrips((ts) => ts.filter((t) => t.id !== id));
    } catch (e) {
      setError(e.message);
    }
  }

  return (
    <div>
      <header className="page-head">
        <div>
          <h1>Your trips</h1>
          <p className="muted">Generate, refine and keep every itinerary in one place.</p>
        </div>
        <Link className="btn primary" to="/new">
          ＋ Plan a new trip
        </Link>
      </header>

      {error && <div className="banner error">{error}</div>}

      {stats && (
        <section className="stats">
          <Stat label="Trips planned" value={stats.total} />
          <Stat label="Upcoming" value={stats.upcoming} hint="not yet finished" />
          <Stat label="Destinations" value={stats.destinations} />
          <Stat label="Days mapped out" value={stats.days} />
        </section>
      )}

      {!trips && !error && <p className="muted">Loading trips…</p>}

      {trips && trips.length === 0 && (
        <div className="empty">
          <div className="empty-icon">🧭</div>
          <h3>No trips yet</h3>
          <p className="muted">Tell us where, when and what you love; we'll draft a day-by-day plan in seconds.</p>
          <Link className="btn primary" to="/new">
            Create your first trip
          </Link>
        </div>
      )}

      {trips && trips.length > 0 && (
        <section className="grid">
          {trips.map((t) => (
            <article key={t.id} className="card trip-card">
              <Link to={`/trips/${t.id}`} className="trip-link">
                <div className="trip-dest">{t.request.destination}</div>
                <div className="trip-dates">
                  {fmtDate(t.request.start_date, { day: "numeric", month: "short" })} →{" "}
                  {fmtDate(t.request.end_date)} · {t.itinerary.days.length} days
                </div>
                <div className="chips">
                  {t.request.interests.slice(0, 4).map((i) => (
                    <span key={i} className="chip small">
                      {i}
                    </span>
                  ))}
                </div>
                <div className="trip-cost">
                  <span>{money(t.request.currency, t.itinerary.total_cost)}</span>
                  <span className="muted"> of {money(t.request.currency, t.request.budget)}</span>
                </div>
              </Link>
              <button className="btn ghost danger small" onClick={() => remove(t.id)} aria-label={`Delete ${t.title}`}>
                Delete
              </button>
            </article>
          ))}
        </section>
      )}
    </div>
  );
}
