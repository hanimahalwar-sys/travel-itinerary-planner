import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, CATEGORY_ICON } from "../api.js";

const INTERESTS = ["sightseeing", "food", "culture", "nature", "adventure", "shopping", "nightlife", "relaxation"];
const STYLES = [
  { id: "relaxed", label: "Relaxed", hint: "~4 stops a day" },
  { id: "balanced", label: "Balanced", hint: "~5 stops a day" },
  { id: "packed", label: "Packed", hint: "~6 stops a day" },
];
const TIERS = [
  { id: "budget", label: "Budget" },
  { id: "mid", label: "Mid-range" },
  { id: "premium", label: "Premium" },
];
const CURRENCIES = ["INR", "USD", "EUR", "GBP", "AED", "SGD", "JPY", "AUD"];

function isoDate(offsetDays) {
  const d = new Date();
  d.setDate(d.getDate() + offsetDays);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export default function TripBuilder() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    destination: "",
    start_date: isoDate(14),
    end_date: isoDate(17),
    budget: 40000,
    currency: "INR",
    travelers: 2,
    travel_style: "balanced",
    accommodation_tier: "mid",
    interests: ["sightseeing", "food"],
    notes: "",
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  const toggleInterest = (i) =>
    set("interests", form.interests.includes(i) ? form.interests.filter((x) => x !== i) : [...form.interests, i]);

  const days = Math.max(0, Math.round((new Date(form.end_date) - new Date(form.start_date)) / 86400000) + 1);

  async function submit(e) {
    e.preventDefault();
    setError("");
    if (days < 1) return setError("End date must be on or after the start date.");
    if (days > 14) return setError("Trips are limited to 14 days.");
    setBusy(true);
    try {
      const trip = await api.createTrip({
        ...form,
        destination: form.destination.trim(),
        budget: Number(form.budget),
        travelers: Number(form.travelers),
      });
      navigate(`/trips/${trip.id}`);
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }

  return (
    <div>
      <header className="page-head">
        <div>
          <h1>Plan a new trip</h1>
          <p className="muted">The more you tell us, the more personal the plan. You can edit everything afterwards.</p>
        </div>
      </header>

      <form className="card form" onSubmit={submit}>
        <div className="field-row">
          <label className="field wide">
            <span>Destination</span>
            <input
              required
              minLength={2}
              maxLength={80}
              placeholder="e.g. Jaipur, Goa, Paris, Kyoto"
              value={form.destination}
              onChange={(e) => set("destination", e.target.value)}
            />
          </label>
          <label className="field">
            <span>Travelers</span>
            <input type="number" min={1} max={20} value={form.travelers} onChange={(e) => set("travelers", e.target.value)} />
          </label>
        </div>

        <div className="field-row">
          <label className="field">
            <span>Start date</span>
            <input type="date" required value={form.start_date} onChange={(e) => set("start_date", e.target.value)} />
          </label>
          <label className="field">
            <span>End date</span>
            <input type="date" required min={form.start_date} value={form.end_date} onChange={(e) => set("end_date", e.target.value)} />
          </label>
          <div className="field days-pill">
            <span>Length</span>
            <strong>{days > 0 ? `${days} day${days > 1 ? "s" : ""}` : "—"}</strong>
          </div>
        </div>

        <div className="field-row">
          <label className="field wide">
            <span>Total budget (whole group)</span>
            <input type="number" min={1} required value={form.budget} onChange={(e) => set("budget", e.target.value)} />
          </label>
          <label className="field">
            <span>Currency</span>
            <select value={form.currency} onChange={(e) => set("currency", e.target.value)}>
              {CURRENCIES.map((c) => (
                <option key={c}>{c}</option>
              ))}
            </select>
          </label>
        </div>

        <fieldset className="field">
          <legend>Pace</legend>
          <div className="segmented">
            {STYLES.map((s) => (
              <button
                type="button"
                key={s.id}
                className={form.travel_style === s.id ? "active" : ""}
                onClick={() => set("travel_style", s.id)}
              >
                <strong>{s.label}</strong>
                <small>{s.hint}</small>
              </button>
            ))}
          </div>
        </fieldset>

        <fieldset className="field">
          <legend>Stay</legend>
          <div className="segmented">
            {TIERS.map((t) => (
              <button
                type="button"
                key={t.id}
                className={form.accommodation_tier === t.id ? "active" : ""}
                onClick={() => set("accommodation_tier", t.id)}
              >
                <strong>{t.label}</strong>
              </button>
            ))}
          </div>
        </fieldset>

        <fieldset className="field">
          <legend>Interests</legend>
          <div className="chips">
            {INTERESTS.map((i) => (
              <button
                type="button"
                key={i}
                className={`chip ${form.interests.includes(i) ? "on" : ""}`}
                aria-pressed={form.interests.includes(i)}
                onClick={() => toggleInterest(i)}
              >
                {CATEGORY_ICON[i]} {i}
              </button>
            ))}
          </div>
        </fieldset>

        <label className="field">
          <span>Anything else? (optional)</span>
          <textarea
            rows={3}
            maxLength={500}
            placeholder="Vegetarian food, travelling with a toddler, want a sunrise spot…"
            value={form.notes}
            onChange={(e) => set("notes", e.target.value)}
          />
        </label>

        {error && <div className="banner error">{error}</div>}

        <div className="form-actions">
          <button className="btn primary large" disabled={busy}>
            {busy ? "Crafting your itinerary…" : "Generate itinerary"}
          </button>
        </div>
      </form>
    </div>
  );
}
