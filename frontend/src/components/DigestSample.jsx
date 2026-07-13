/*
  DigestSample — a static, in-browser recreation of the DevPulse digest email,
  framed in a macOS window. Used on the landing hero and the dashboard.

  Mirrors the SHIPPED email (services/email.py): light editorial card, serif
  masthead + PR titles, mono labels/metadata, a "Waiting on you" row with a
  Conflict pill, and a six-stat strip ending in an orange DAY STREAK. Layout
  follows the Stitch "Settings & Preferences" screen; data conventions follow
  the real backend (DigestContext) — ISSUES OPENED (not closed), no invented
  CI/analytics, no RISING badge.
*/

const STREAK = "#EA580C";

const SAMPLE = {
  dateline: "ISSUE 001 · DAILY BRIEF",
  facts: ["You merged 5 pull requests today.", "2 items need your attention."],
  waiting: { repo: "acme/webapp", number: 124, title: "Refactor auth flow", add: 254, del: 120, files: 14 },
  stats: [
    { label: "PRS OPENED", value: 8, delta: "+1" },
    { label: "PRS MERGED", value: 6, delta: "-1" },
    { label: "REVIEWS GIVEN", value: 14, delta: "+3" },
    { label: "ISSUES OPENED", value: 3, delta: null },
    { label: "REPOS ACTIVE", value: 4, delta: null },
    { label: "DAY STREAK", value: 8, delta: null, accent: STREAK },
  ],
};

function Delta({ delta }) {
  if (!delta) return null;
  const up = delta.startsWith("+");
  return (
    <span className="mono" style={{ fontSize: 10, textTransform: "none", color: up ? "var(--color-ok)" : "var(--color-bad)" }}>
      {up ? "↑" : "↓"} {delta.replace(/[+-]/, "")}
    </span>
  );
}

export default function DigestSample() {
  const s = SAMPLE.waiting;
  return (
    <div
      className="overflow-hidden bg-white"
      style={{
        borderRadius: 16,
        border: "1px solid var(--color-hairline)",
        boxShadow: "0 24px 60px -20px rgba(91,91,214,0.18), 0 8px 24px rgba(0,0,0,0.05)",
      }}
    >
      {/* window chrome */}
      <div
        className="flex items-center justify-between px-4 py-3"
        style={{ borderBottom: "1px solid var(--color-hairline)", background: "var(--color-tint)" }}
      >
        <div className="flex items-center gap-2">
          <span className="block w-3 h-3 rounded-full" style={{ background: "#FF5F56" }} />
          <span className="block w-3 h-3 rounded-full" style={{ background: "#FFBD2E" }} />
          <span className="block w-3 h-3 rounded-full" style={{ background: "#27C93F" }} />
        </div>
        <span className="mono" style={{ color: "var(--color-muted)", fontSize: 11 }}>Inbox · 8:32 AM</span>
      </div>

      {/* body */}
      <div className="px-7 py-7">
        {/* masthead */}
        <div className="flex items-baseline justify-between gap-3">
          <span className="serif" style={{ fontSize: 22, fontWeight: 700, letterSpacing: "-0.02em" }}>DEVPULSE</span>
          <span className="mono" style={{ color: "var(--color-muted)", fontSize: 10 }}>{SAMPLE.dateline}</span>
        </div>

        {/* ai summary */}
        <p className="mono mt-6" style={{ color: "var(--color-accent)", fontSize: 11 }}>✦ AI Summary</p>
        <h3 className="serif mt-3" style={{ fontSize: 22, fontWeight: 700, lineHeight: 1.25, margin: 0 }}>
          A strong day of shipping on{" "}
          <span className="italic" style={{ color: "var(--color-accent)" }}>webapp.</span>
        </h3>
        <div className="mt-3 flex flex-col gap-1">
          {SAMPLE.facts.map((f) => (
            <p key={f} style={{ fontSize: 13, lineHeight: 1.5, color: "var(--color-muted)", margin: 0 }}>{f}</p>
          ))}
        </div>

        {/* waiting on you */}
        <div className="rule mt-7 pt-4">
          <p className="mono" style={{ color: "var(--color-muted)", fontSize: 11 }}>⚡ Waiting on you</p>
          <div className="flex items-start justify-between gap-3 mt-3">
            <div className="min-w-0">
              <p className="serif" style={{ fontSize: 15, fontWeight: 700, margin: 0 }}>
                <span className="mono" style={{ color: "var(--color-muted)", fontSize: 11 }}>{s.repo} #{s.number}</span>{" "}
                {s.title}
              </p>
              <p className="mono mt-1" style={{ fontSize: 11, textTransform: "none", color: "var(--color-muted)", margin: "4px 0 0" }}>
                <span style={{ color: "var(--color-ok)" }}>+{s.add}</span>{" "}
                <span style={{ color: "var(--color-bad)" }}>−{s.del}</span>{" "}
                · {s.files} files
              </p>
            </div>
            <span
              className="mono shrink-0"
              style={{
                fontSize: 10, textTransform: "none", padding: "2px 8px", borderRadius: 4,
                background: "var(--color-conflict-bg)", color: "var(--color-conflict-fg)",
              }}
            >
              Conflict
            </span>
          </div>
        </div>

        {/* last 7 days — six-stat strip */}
        <div className="rule mt-6 pt-5">
          <div className="grid grid-cols-6 gap-2">
            {SAMPLE.stats.map((st) => (
              <div key={st.label} className="text-center">
                <div className="serif" style={{ fontSize: 26, fontWeight: 700, lineHeight: 1.1, color: st.accent || "var(--color-ink)", fontVariantNumeric: "tabular-nums" }}>
                  {st.value}
                </div>
                <div className="mono mt-1" style={{ fontSize: 8, letterSpacing: "0.04em", color: st.accent || "var(--color-muted)" }}>
                  {st.label}
                </div>
                <div className="mt-1"><Delta delta={st.delta} /></div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
