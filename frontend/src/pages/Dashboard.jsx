/*
  DevPulse — Dashboard (digest settings).
  Editorial/broadsheet language shared with the landing (serif + mono, hairlines,
  indigo scalpel accent, glass cards). Exposes exactly two controls — delivery
  frequency (+ a delivery/anchor time; 6h/12h anchor to the chosen hour and repeat
  across the day) and tracked repos — plus a read-only list of past issues.

  Grounded to real backend endpoints:
    GET  /api/users/me            → profile
    GET  /api/digest/settings     → { digest_frequency, tracked_repos, digest_hour, digest_day, digest_timezone }
    POST /api/digest/settings     → persist the above
    GET  /api/github/repos        → { repos: [{ name, language, private, ... }] }
    GET  /api/digest/history      → { digests: [{ period_end, ai_summary, email_sent_at }] }
  No send-now and no live preview (project direction) — the digest only truly arrives by email.
*/

import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { UserButton, useClerk } from "@clerk/clerk-react";
import { Lock } from "lucide-react";
import api from "@/lib/api";
import DigestSample from "@/components/DigestSample";

const PAGE = "max-w-[1200px] mx-auto px-6 md:px-20";

const FREQS = [
  { v: "off", label: "Off", hint: "Paused — DevPulse won't email you until you turn this back on." },
  { v: "6h", label: "6h", hint: "A fresh brief every six hours — for the busiest days." },
  { v: "12h", label: "12h", hint: "Twice a day — a morning and an evening read." },
  { v: "daily", label: "Daily", hint: "One composed brief each day. The classic cadence." },
  { v: "weekly", label: "Weekly", hint: "A single digest at the end of the week." },
];

const HOURS = Array.from({ length: 24 }, (_, h) => h);
const DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"];
const BROWSER_TZ = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
// Full IANA zone list when the browser supports it (all modern ones do); otherwise a small
// fallback that still includes the detected zone so the user is never stuck on a wrong guess.
const TZONES = (() => {
  const list = typeof Intl.supportedValuesOf === "function"
    ? Intl.supportedValuesOf("timeZone")
    : ["UTC", "Asia/Kolkata", "America/New_York", "America/Los_Angeles", "Europe/London"];
  return Array.from(new Set([BROWSER_TZ, ...list])).sort();
})();
const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);
const hourLabel = (h) => `${String(h).padStart(2, "0")}:00`;

// 6h/12h are anchored to the chosen hour, then repeat across the day (mirrors backend _is_due).
const INTERVAL = { "6h": 6, "12h": 12 };
const isInterval = (f) => f === "6h" || f === "12h";
function sendTimes(anchor, interval) {
  return Array.from({ length: 24 / interval }, (_, k) => (anchor + k * interval) % 24)
    .sort((a, b) => a - b)
    .map(hourLabel)
    .join(" · ");
}
const selectStyle = {
  textTransform: "none", fontSize: 14, padding: "6px 12px", borderRadius: 8,
  border: "1px solid var(--color-hairline)", background: "#fff", color: "var(--color-ink)",
  cursor: "pointer",
};

/* Searchable timezone combobox. A native <select> over the 400+ IANA zones renders an
   unstyled OS popup whose scrollbar jumps from a stub to full-height — so we roll our own
   fixed-height, searchable dropdown (same look as the tracked-repos list). */
function TzPicker({ value, onChange }) {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const ref = useRef(null);
  // Close on any click outside the widget.
  useEffect(() => {
    if (!open) return;
    const onDoc = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open]);
  const shown = useMemo(() => {
    const s = q.trim().toLowerCase();
    return s ? TZONES.filter((z) => z.toLowerCase().includes(s)) : TZONES;
  }, [q]);
  return (
    <div ref={ref} style={{ position: "relative" }}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="mono"
        style={{ ...selectStyle, textTransform: "none", maxWidth: 260 }}
        title="Delivery timezone"
      >
        {value} ▾
      </button>
      {open && (
        <div
          className="glass"
          style={{ position: "absolute", zIndex: 40, marginTop: 6, width: 280, borderRadius: 10, overflow: "hidden", boxShadow: "0 12px 32px rgba(0,0,0,0.18)" }}
        >
          <div className="px-4 py-3" style={{ borderBottom: "1px solid var(--color-hairline)" }}>
            <input
              autoFocus
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search timezone…"
              className="mono w-full"
              style={{ textTransform: "none", fontSize: 13, background: "transparent", border: "none", outline: "none", color: "var(--color-ink)" }}
            />
          </div>
          <div style={{ maxHeight: 260, overflowY: "auto" }}>
            {shown.length === 0 ? (
              <p className="mono px-4 py-4" style={{ color: "var(--color-muted)", textTransform: "none", fontSize: 13 }}>No matches.</p>
            ) : (
              shown.map((z) => (
                <button
                  key={z}
                  type="button"
                  onClick={() => { onChange(z); setOpen(false); setQ(""); }}
                  className="mono w-full text-left px-4 py-2"
                  style={{ textTransform: "none", fontSize: 13, background: z === value ? "var(--color-tint)" : "transparent", color: "var(--color-ink)", borderBottom: "1px solid var(--color-hairline)" }}
                >
                  {z}
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/* Fade + rise on scroll into view — same motion as the landing. */
function Reveal({ children, delay = 0, className = "" }) {
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y: 26 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: 0.6, delay, ease: [0.22, 1, 0.36, 1] }}
    >
      {children}
    </motion.div>
  );
}

/* A numbered editorial section: mono "0X — LABEL" rail + content, hairline top. */
function Section({ num, label, children }) {
  return (
    <section style={{ borderTop: "1px solid var(--color-hairline)" }}>
      <div className={`${PAGE} py-16 md:py-20`}>
        <Reveal className="grid grid-cols-1 md:grid-cols-12 gap-8">
          <div className="md:col-span-2">
            <p className="mono" style={{ color: "var(--color-muted)" }}>{num} — {label}</p>
          </div>
          <div className="md:col-start-3 md:col-span-9">{children}</div>
        </Reveal>
      </div>
    </section>
  );
}

const LANG_DOT = {
  JavaScript: "#f1e05a", TypeScript: "#3178c6", Python: "#3572A5", Go: "#00ADD8",
  Rust: "#dea584", Ruby: "#701516", Java: "#b07219", "C++": "#f34b7d", C: "#555555",
  Shell: "#89e051", HTML: "#e34c26", CSS: "#563d7c", Swift: "#F05138", Kotlin: "#A97BFF",
};

// Backend timestamps may be naive (no tz suffix). Treat those as UTC so they render in the
// viewer's local time; honor an explicit designator when present. Only the time part (after
// "T") is inspected, so the date's own dashes never read as a tz offset.
function parseIso(iso) {
  const timePart = iso.slice(iso.indexOf("T"));
  const hasTz = /Z$|[+-]\d\d:?\d\d$/.test(timePart);
  return new Date(hasTz ? iso : iso + "Z");
}

function fmtDate(iso) {
  if (!iso) return "";
  const d = parseIso(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleDateString("en-US", { month: "short", day: "2-digit", year: "numeric" }).toUpperCase();
}

function fmtTime(iso) {
  if (!iso) return "";
  const d = parseIso(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
}

function headlineOf(aiSummary) {
  if (!aiSummary) return "Digest delivered.";
  try {
    const parsed = typeof aiSummary === "string" ? JSON.parse(aiSummary) : aiSummary;
    return parsed.headline || "Digest delivered.";
  } catch {
    return typeof aiSummary === "string" ? aiSummary : "Digest delivered.";
  }
}

export default function Dashboard() {
  const { signOut } = useClerk();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [profile, setProfile] = useState(null);
  const [repos, setRepos] = useState([]);
  const [history, setHistory] = useState([]);

  // settings + saved baseline (to compute the dirty state)
  const [freq, setFreq] = useState("off");
  const [selected, setSelected] = useState(() => new Set());
  const [hour, setHour] = useState(8);
  const [day, setDay] = useState("monday");
  const [tz, setTz] = useState(BROWSER_TZ);
  const [saved, setSaved] = useState({ freq: "off", repos: [], hour: 8, day: "monday", tz: BROWSER_TZ });

  const [reposLoading, setReposLoading] = useState(true);
  const [repoQuery, setRepoQuery] = useState("");
  const [saveState, setSaveState] = useState("idle"); // idle | saving | ok | err

  useEffect(() => {
    let alive = true;

    // Critical path — profile + settings gate the page. Both are fast (DB reads),
    // so the page paints quickly instead of waiting on the slow GitHub repo fetch.
    (async () => {
      const [meRes, setRes] = await Promise.allSettled([
        api.get("/api/users/me"),
        api.get("/api/digest/settings"),
      ]);
      if (!alive) return;
      if (meRes.status === "fulfilled") setProfile(meRes.value.data);
      if (setRes.status === "fulfilled") {
        const s = setRes.value.data;
        const initFreq = s.digest_frequency || "off";
        const initRepos = s.tracked_repos || [];
        const initHour = s.digest_hour ?? 8;
        const initDay = s.digest_day || "monday";
        // Respect the user's stored timezone; only default to the browser's for a fresh
        // account that has never saved one. Display and baseline stay in sync so the page
        // doesn't open dirty.
        const initTz = s.digest_timezone || BROWSER_TZ;
        setFreq(initFreq);
        setSelected(new Set(initRepos));
        setHour(initHour);
        setDay(initDay);
        setTz(initTz);
        setSaved({ freq: initFreq, repos: initRepos, hour: initHour, day: initDay, tz: initTz });
      }
      if (meRes.status === "rejected" && setRes.status === "rejected") {
        setError("Couldn't load your settings. Refresh to try again.");
      }
      setLoading(false);
    })();

    // Non-blocking — the GitHub repo list is the slow call (live REST fetch); let it
    // stream in after first paint, with its own loading state in the repos card.
    api.get("/api/github/repos")
      .then((r) => { if (alive) setRepos(r.data.repos || []); })
      .catch(() => {})
      .finally(() => { if (alive) setReposLoading(false); });

    api.get("/api/digest/history")
      .then((r) => { if (alive) setHistory(r.data.digests || []); })
      .catch(() => {});

    return () => { alive = false; };
  }, []);

  const dirty = useMemo(() => {
    const a = [...selected].sort();
    const b = [...saved.repos].sort();
    const sameRepos = a.length === b.length && a.every((v, i) => v === b[i]);
    return freq !== saved.freq || !sameRepos
      || hour !== saved.hour || day !== saved.day || tz !== saved.tz;
  }, [freq, selected, hour, day, tz, saved]);

  const filteredRepos = useMemo(() => {
    const q = repoQuery.trim().toLowerCase();
    if (!q) return repos;
    return repos.filter((r) => r.name.toLowerCase().includes(q));
  }, [repos, repoQuery]);

  function toggleRepo(name) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  }

  async function save() {
    setSaveState("saving");
    try {
      const tracked = [...selected]; // empty array = all repos (backend convention)
      await api.post("/api/digest/settings", {
        digest_frequency: freq, tracked_repos: tracked,
        digest_hour: hour, digest_day: day, digest_timezone: tz,
      });
      setSaved({ freq, repos: tracked, hour, day, tz });
      setSaveState("ok");
      setTimeout(() => setSaveState("idle"), 2500);
    } catch {
      setSaveState("err");
    }
  }

  const activeHint = FREQS.find((f) => f.v === freq)?.hint;

  return (
    <div style={{ background: "var(--color-page)", minHeight: "100vh" }}>
      {/* nav */}
      <div className="glass-nav sticky top-0 z-50">
        <div className={`${PAGE} py-4 flex justify-between items-center`}>
          <Link to="/" className="serif" style={{ fontSize: 24, fontWeight: 700, letterSpacing: "-0.02em" }}>
            DEVPULSE
          </Link>
          <div className="flex items-center gap-4">
            <button onClick={() => signOut({ redirectUrl: "/" })} className="btn-dark px-6 py-3">
              Log out
            </button>
            <UserButton afterSignOutUrl="/" />
          </div>
        </div>
      </div>

      {/* header + read-only profile */}
      <div className={`${PAGE} pt-16 md:pt-20 pb-10`}>
        <Reveal>
          <p className="mono rule pt-6" style={{ color: "var(--color-muted)" }}>
            {profile?.github_username || "—"}
            {profile?.email ? ` · ${profile.email}` : ""}
            {profile?.created_at ? ` · MEMBER SINCE ${fmtDate(profile.created_at)}` : ""}
          </p>
          <h1 className="serif" style={{ fontSize: "clamp(34px, 8vw, 56px)", fontWeight: 700, lineHeight: 1.1, letterSpacing: "-0.02em", margin: "12px 0 0" }}>
            Your daily <span className="italic" style={{ color: "var(--color-accent)" }}>brief.</span>
          </h1>
        </Reveal>
      </div>

      {error && (
        <div className={`${PAGE} mt-8`}>
          <p className="mono" style={{ color: "var(--color-bad)", textTransform: "none" }}>{error}</p>
        </div>
      )}

      {loading ? (
        <div className={`${PAGE} py-24`}>
          <p className="mono" style={{ color: "var(--color-muted)" }}>Loading your brief…</p>
        </div>
      ) : (
        <>
          {/* 01 — DELIVERY */}
          <Section num="01" label="DELIVERY">
            <div className="flex flex-wrap gap-2">
              {FREQS.map((f) => {
                const on = f.v === freq;
                return (
                  <button
                    key={f.v}
                    onClick={() => setFreq(f.v)}
                    className="mono"
                    style={{
                      textTransform: "none", fontSize: 14, padding: "8px 18px", borderRadius: 9999,
                      border: `1px solid ${on ? "var(--color-accent)" : "var(--color-hairline)"}`,
                      color: on ? "#fff" : "var(--color-ink)",
                      background: on ? "var(--color-accent)" : "transparent",
                      fontWeight: on ? 700 : 400, transition: "all 0.15s",
                    }}
                  >
                    {f.label}
                  </button>
                );
              })}
            </div>
            <p className="mt-5" style={{ fontSize: 17, lineHeight: 1.6, color: "var(--color-muted)", maxWidth: "55ch" }}>
              {activeHint}
            </p>

            {freq !== "off" && (
              <div className="mt-6">
                <div className="flex flex-wrap items-center gap-3">
                  <span className="mono" style={{ color: "var(--color-muted)", fontSize: 12 }}>
                    {isInterval(freq) ? "Anchor" : "Deliver"}
                  </span>
                  {freq === "weekly" && (
                    <select
                      value={day}
                      onChange={(e) => setDay(e.target.value)}
                      className="mono"
                      style={selectStyle}
                    >
                      {DAYS.map((d) => <option key={d} value={d}>{cap(d)}</option>)}
                    </select>
                  )}
                  <span className="mono" style={{ color: "var(--color-muted)", fontSize: 12 }}>at</span>
                  <select
                    value={hour}
                    onChange={(e) => setHour(Number(e.target.value))}
                    className="mono"
                    style={selectStyle}
                  >
                    {HOURS.map((h) => <option key={h} value={h}>{hourLabel(h)}</option>)}
                  </select>
                  <TzPicker value={tz} onChange={setTz} />
                </div>
                {isInterval(freq) && (
                  <p className="mono mt-3" style={{ color: "var(--color-muted)", fontSize: 12, textTransform: "none" }}>
                    Sends at {sendTimes(hour, INTERVAL[freq])}
                  </p>
                )}
              </div>
            )}

            {/* actions — same handler/state as the repos card; either button saves all settings */}
            <div className="mt-8 flex flex-wrap items-center gap-4">
              <button
                onClick={save}
                disabled={!dirty || saveState === "saving"}
                className="btn-dark px-6 py-3"
                style={{ opacity: !dirty || saveState === "saving" ? 0.4 : 1, cursor: !dirty ? "default" : "pointer" }}
              >
                {saveState === "saving" ? "Saving…" : "Save changes"}
              </button>

              {saveState === "ok" && <span className="mono" style={{ color: "var(--color-ok)", textTransform: "none" }}>Saved.</span>}
              {saveState === "err" && <span className="mono" style={{ color: "var(--color-bad)", textTransform: "none" }}>Couldn't save — try again.</span>}
            </div>
          </Section>

          {/* 02 — TRACKED REPOS */}
          <Section num="02" label="TRACKED REPOS">
            <div className="glass" style={{ borderRadius: 12, overflow: "hidden" }}>
              <div className="px-5 py-4" style={{ borderBottom: "1px solid var(--color-hairline)" }}>
                <input
                  value={repoQuery}
                  onChange={(e) => setRepoQuery(e.target.value)}
                  placeholder="Search repositories…"
                  className="mono w-full"
                  style={{
                    textTransform: "none", fontSize: 14, background: "transparent",
                    border: "none", outline: "none", color: "var(--color-ink)",
                  }}
                />
              </div>
              <div style={{ maxHeight: 340, overflowY: "auto" }}>
                {filteredRepos.length === 0 ? (
                  <p className="mono px-5 py-6" style={{ color: "var(--color-muted)", textTransform: "none" }}>
                    {reposLoading ? "Loading your repositories…" : repos.length === 0 ? "No repositories found on your account." : "No matches."}
                  </p>
                ) : (
                  filteredRepos.map((r) => {
                    const on = selected.has(r.name);
                    return (
                      <button
                        key={r.name}
                        onClick={() => toggleRepo(r.name)}
                        className="w-full flex items-center gap-3 px-5 py-3 text-left"
                        style={{ borderBottom: "1px solid var(--color-hairline)", background: on ? "var(--color-tint)" : "transparent" }}
                      >
                        <span
                          className="shrink-0 flex items-center justify-center"
                          style={{
                            width: 18, height: 18, borderRadius: 4,
                            border: `1px solid ${on ? "var(--color-accent)" : "var(--color-hairline)"}`,
                            background: on ? "var(--color-accent)" : "transparent", color: "#fff", fontSize: 12,
                          }}
                        >
                          {on ? "✓" : ""}
                        </span>
                        <span className="flex-1 min-w-0">
                          <span className="mono block truncate" style={{ textTransform: "none", fontSize: 14, color: "var(--color-ink)" }}>
                            {r.name}
                          </span>
                          {r.language && (
                            <span className="mono flex items-center gap-1 mt-0.5" style={{ textTransform: "none", fontSize: 11, color: "var(--color-muted)" }}>
                              <span style={{ width: 8, height: 8, borderRadius: 9999, background: LANG_DOT[r.language] || "#9ca3af", display: "inline-block" }} />
                              {r.language}
                            </span>
                          )}
                        </span>
                        <span className="mono shrink-0" style={{ fontSize: 10, padding: "2px 8px", borderRadius: 9999, border: "1px solid var(--color-hairline)", color: "var(--color-muted)" }}>
                          {r.private ? "PRIVATE" : "PUBLIC"}
                        </span>
                      </button>
                    );
                  })
                )}
              </div>
            </div>
            <p className="mono mt-3 italic" style={{ textTransform: "none", fontSize: 12, color: "var(--color-muted)" }}>
              {selected.size === 0
                ? "Nothing selected — your brief covers all repositories."
                : `${selected.size} repositor${selected.size === 1 ? "y" : "ies"} tracked.`}
            </p>

            {/* actions */}
            <div className="mt-8 flex flex-wrap items-center gap-4">
              <button
                onClick={save}
                disabled={!dirty || saveState === "saving"}
                className="btn-dark px-6 py-3"
                style={{ opacity: !dirty || saveState === "saving" ? 0.4 : 1, cursor: !dirty ? "default" : "pointer" }}
              >
                {saveState === "saving" ? "Saving…" : "Save changes"}
              </button>

              {saveState === "ok" && <span className="mono" style={{ color: "var(--color-ok)", textTransform: "none" }}>Saved.</span>}
              {saveState === "err" && <span className="mono" style={{ color: "var(--color-bad)", textTransform: "none" }}>Couldn't save — try again.</span>}
            </div>
          </Section>

          {/* 03 — YOUR DIGEST (static sample, no live preview) */}
          <Section num="03" label="YOUR DIGEST">
            <div style={{ maxWidth: 560 }}>
              <DigestSample />
            </div>
            <p className="mono mt-4 italic" style={{ textTransform: "none", fontSize: 12, color: "var(--color-muted)" }}>
              A sample of the format — your real digest arrives by email.
            </p>
          </Section>

          {/* 04 — PAST ISSUES */}
          {history.length > 0 && (
            <Section num="04" label="PAST ISSUES">
              <div className="flex flex-col">
                {history.map((h) => (
                  <div
                    key={h.id}
                    className="flex flex-col md:flex-row md:items-baseline md:justify-between gap-1 md:gap-6 py-4"
                    style={{ borderTop: "1px solid var(--color-hairline)" }}
                  >
                    <span className="mono shrink-0" style={{ color: "var(--color-muted)", minWidth: 120 }}>
                      {fmtDate(h.email_sent_at || h.period_end || h.created_at)}
                    </span>
                    <span className="serif flex-1" style={{ fontSize: 18, lineHeight: 1.4 }}>
                      {headlineOf(h.ai_summary)}
                    </span>
                    <span className="mono shrink-0" style={{ color: "var(--color-muted)", textTransform: "none", fontSize: 12 }}>
                      {h.email_sent_at ? `Sent ${fmtTime(h.email_sent_at)}` : "Not sent"}
                    </span>
                  </div>
                ))}
              </div>
            </Section>
          )}

          {/* footer */}
          <footer className={`${PAGE} py-12`} style={{ borderTop: "1px solid var(--color-hairline)" }}>
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
              <div>
                <p className="serif italic flex items-center gap-2" style={{ fontSize: 15, fontWeight: 700, color: "var(--color-accent)", margin: 0 }}>
                  <Lock size={14} strokeWidth={2.4} aria-hidden="true" />
                  Private by design.
                </p>
                <p className="mt-1" style={{ fontSize: 13, color: "var(--color-muted)", maxWidth: "40ch" }}>
                  We read only the GitHub you approve. Your code never leaves your repos.
                </p>
              </div>
              <div className="serif" style={{ fontSize: 20, fontWeight: 700 }}>DEVPULSE</div>
            </div>
          </footer>
        </>
      )}
    </div>
  );
}
