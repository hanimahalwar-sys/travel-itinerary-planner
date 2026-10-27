import { useEffect, useState } from "react";
import { NavLink, Route, Routes } from "react-router-dom";
import { api } from "./api.js";
import Dashboard from "./pages/Dashboard.jsx";
import TripBuilder from "./pages/TripBuilder.jsx";
import ItineraryView from "./pages/ItineraryView.jsx";

export default function App() {
  const [health, setHealth] = useState(null);

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth({ status: "down" }));
  }, []);

  const down = health?.status === "down";

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">W</span>
          <span className="brand-name">Wayfarer</span>
        </div>
        <nav>
          <NavLink to="/" end>
            <span>▦</span> Dashboard
          </NavLink>
          <NavLink to="/new">
            <span>＋</span> New trip
          </NavLink>
        </nav>
        <div className="sidebar-foot">
          {health && !down && (
            <>
              <div className="pill-row">
                <span className={`dot ${health.ai_mode === "llm" ? "dot-green" : "dot-amber"}`} />
                {health.ai_mode === "llm" ? `AI: ${health.llm_model}` : "AI: built-in planner"}
              </div>
              <div className="pill-row">
                <span className="dot dot-green" /> Storage: {health.storage}
              </div>
            </>
          )}
          {down && (
            <div className="pill-row">
              <span className="dot dot-red" /> API offline
            </div>
          )}
        </div>
      </aside>
      <main className="content">
        {down && (
          <div className="banner error">
            Can't reach the backend. Start it with <code>uvicorn app.main:app --reload</code> from the
            <code>backend</code> folder.
          </div>
        )}
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/new" element={<TripBuilder />} />
          <Route path="/trips/:id" element={<ItineraryView />} />
          <Route path="*" element={<p className="muted">Page not found.</p>} />
        </Routes>
      </main>
    </div>
  );
}
