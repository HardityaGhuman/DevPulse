/*
  DigestSample — a static, in-browser recreation of the DevPulse digest email,
  framed in a macOS window. Used on the landing hero and the dashboard.

  Grounded to REAL data the backend produces (services/email.py + DigestContext):
  commits, prs_opened, prs_merged, issues, reviews, streak, momentum, and the
  "waiting on you" PR rows with size / files / Conflict / Review-requested flags.
  NO CI/build-success metric — the backend does not fetch that.
*/

const SAMPLE = {
  masthead: "DevPulse · Issue 001 · Daily Brief",
  headline: "Steady progress on aria — a strong day of shipping.",
  momentum: "RISING",
  stats: [
    { label: "Commits", value: 24, delta: "+6" },
    { label: "PRs opened", value: 3, delta: "+1" },
    { label: "PRs merged", value: 5, delta: "+2" },
    { label: "Issues", value: 2, delta: null },
    { label: "Reviews", value: 9, delta: "+3" },
  ],
  streak: 7,
  waiting: [
    {
      repo: "me/aria", number: 124, title: "Refactor auth flow",
      add: 254, del: 120, files: 14, flags: ["Conflict", "Review requested"],
    },
    {
      repo: "acme/api-services", number: 88, title: "Add rate limiting",
      add: 96, del: 12, files: 4, flags: ["Review requested"],
    },
  ],
};

function Flag({ label }) {
  const conflict = label === "Conflict";
  return (
    <span
      className="mono"
      style={{
        fontSize: 10,
        padding: "2px 8px",
        borderRadius: 9999,
        ...(conflict
          ? { background: "var(--color-conflict-bg)", color: "var(--color-conflict-fg)" }
          : { border: "1px solid var(--color-accent)", color: "var(--color-accent)" }),
      }}
    >
      {label}
    </span>
  );
}

export default function DigestSample() {
  return (
    <div
      className="overflow-hidden bg-white"
      style={{
        borderRadius: 14,
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
          <span className="block w-3 h-3 rounded-full" style={{ background: "#e11d48" }} />
          <span className="block w-3 h-3 rounded-full" style={{ background: "#e5e2e1" }} />
          <span className="block w-3 h-3 rounded-full" style={{ background: "#e5e2e1" }} />
        </div>
        <span className="mono" style={{ color: "var(--color-muted)", fontSize: 11 }}>
          Inbox · 8:00 AM
        </span>
      </div>

      {/* body */}
      <div className="px-7 py-7">
        <p className="mono" style={{ color: "var(--color-muted)", fontSize: 11 }}>
          {SAMPLE.masthead}
        </p>
        <div className="mt-4 flex items-start justify-between gap-4">
          <h3 className="serif" style={{ fontSize: 24, fontWeight: 700, lineHeight: 1.2, margin: 0 }}>
            {SAMPLE.headline}
          </h3>
          <span
            className="mono shrink-0"
            style={{
              fontSize: 10, padding: "3px 9px", borderRadius: 9999,
              background: "#dcfce7", color: "#166534",
            }}
          >
            {SAMPLE.momentum}
          </span>
        </div>

        {/* waiting on you */}
        <div className="rule mt-7 pt-4">
          <p className="mono" style={{ color: "var(--color-muted)", fontSize: 11 }}>⚡ Waiting on you</p>
          <div className="mt-3 flex flex-col">
            {SAMPLE.waiting.map((pr) => (
              <div
                key={pr.number}
                className="flex items-start justify-between gap-3 py-3"
                style={{ borderTop: "1px solid var(--color-hairline)" }}
              >
                <div>
                  <div style={{ fontSize: 14 }}>
                    <span className="mono" style={{ color: "var(--color-muted)", fontSize: 11 }}>
                      {pr.repo} #{pr.number}
                    </span>{" "}
                    <span style={{ fontWeight: 600 }}>{pr.title}</span>
                  </div>
                  <div className="mono mt-1" style={{ fontSize: 11, textTransform: "none", color: "var(--color-muted)" }}>
                    <span style={{ color: "var(--color-ok)" }}>+{pr.add}</span>{" "}
                    <span style={{ color: "var(--color-bad)" }}>−{pr.del}</span>{" "}
                    · {pr.files} files
                  </div>
                </div>
                <div className="flex flex-wrap gap-1 justify-end shrink-0">
                  {pr.flags.map((f) => <Flag key={f} label={f} />)}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* activity stats */}
        <div className="rule mt-6 pt-4">
          <p className="mono" style={{ color: "var(--color-muted)", fontSize: 11 }}>📊 Your activity</p>
          <div className="mt-3 grid grid-cols-5 gap-2">
            {SAMPLE.stats.map((s) => (
              <div key={s.label}>
                <div className="flex items-baseline gap-1">
                  <span className="serif" style={{ fontSize: 26, fontWeight: 500, fontVariantNumeric: "tabular-nums" }}>
                    {String(s.value).padStart(2, "0")}
                  </span>
                  {s.delta && (
                    <span className="mono" style={{ fontSize: 10, color: "var(--color-ok)", textTransform: "none" }}>
                      ↑{s.delta.replace("+", "")}
                    </span>
                  )}
                </div>
                <div className="mono" style={{ fontSize: 10, color: "var(--color-muted)" }}>{s.label}</div>
              </div>
            ))}
          </div>
          <span
            className="mono mt-4 inline-block"
            style={{
              fontSize: 11, textTransform: "none", padding: "4px 12px", borderRadius: 9999,
              background: "#fff7ed", border: "1px solid #ffedd5", color: "#9a3412", fontWeight: 700,
            }}
          >
            🔥 {SAMPLE.streak}-day streak
          </span>
        </div>
      </div>
    </div>
  );
}
