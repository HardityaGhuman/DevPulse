/*
  DevPulse — Landing page. Gridded editorial / broadsheet aesthetic.
  Serif display + mono labels, hairline rules, asymmetric 12-col grid.
  All feature copy is grounded in what the backend actually produces.
*/

import { Link, useNavigate, Navigate } from "react-router-dom";
import { useAuth, SignInButton, SignUpButton } from "@clerk/clerk-react";
import { motion } from "framer-motion";
import DigestSample from "@/components/DigestSample";

const PAGE = "max-w-[1200px] mx-auto px-6 md:px-20";

/* Fade + rise as the element scrolls into view. */
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

function SignInPill({ className = "", label = "Sign in with GitHub" }) {
  const { isSignedIn } = useAuth();
  const navigate = useNavigate();
  if (isSignedIn) {
    return (
      <button onClick={() => navigate("/dashboard")} className={`btn-dark px-6 py-3 ${className}`}>
        Open dashboard
      </button>
    );
  }
  return (
    <SignInButton mode="modal" forceRedirectUrl="/dashboard">
      <button className={`btn-dark px-6 py-3 ${className}`}>{label}</button>
    </SignInButton>
  );
}

/* Nav auth: explicit Log in + Sign up for returning vs new users. */
function NavAuth() {
  const { isSignedIn } = useAuth();
  const navigate = useNavigate();
  if (isSignedIn) {
    return (
      <button onClick={() => navigate("/dashboard")} className="btn-dark px-6 py-3">
        Open dashboard
      </button>
    );
  }
  return (
    <div className="flex items-center gap-5">
      <SignInButton mode="modal" forceRedirectUrl="/dashboard">
        <button className="mono" style={{ color: "var(--color-ink)" }}>Log in</button>
      </SignInButton>
      <SignUpButton mode="modal" forceRedirectUrl="/dashboard">
        <button className="btn-dark px-6 py-3">Sign up</button>
      </SignUpButton>
    </div>
  );
}

/* One feature row on the 12-col grid. `flip` puts the card on the left. */
function Feature({ num, label, heading, accent, tail, lede, card, flip }) {
  return (
    <section style={{ borderTop: "1px solid var(--color-hairline)" }}>
      <div className={`${PAGE} py-24 md:py-32`}>
        <Reveal className="grid grid-cols-1 md:grid-cols-12 gap-8">
          <div className="md:col-span-2">
            <p className="mono" style={{ color: "var(--color-muted)" }}>{num} — {label}</p>
          </div>

          {flip ? (
            <>
              <div className="md:col-start-3 md:col-span-3">{card}</div>
              <div className="md:col-start-6 md:col-span-5">
                <h2 className="serif" style={{ fontSize: 44, fontWeight: 700, lineHeight: 1.15, margin: 0 }}>
                  {heading} <span className="italic" style={{ color: "var(--color-accent)" }}>{accent}</span> {tail}
                </h2>
                <p className="mt-6" style={{ fontSize: 20, lineHeight: 1.6, color: "var(--color-ink)", maxWidth: "55ch" }}>
                  {lede}
                </p>
              </div>
            </>
          ) : (
            <>
              <div className="md:col-start-3 md:col-span-5">
                <h2 className="serif" style={{ fontSize: 44, fontWeight: 700, lineHeight: 1.15, margin: 0 }}>
                  {heading} <span className="italic" style={{ color: "var(--color-accent)" }}>{accent}</span> {tail}
                </h2>
                <p className="mt-6" style={{ fontSize: 20, lineHeight: 1.6, color: "var(--color-ink)", maxWidth: "55ch" }}>
                  {lede}
                </p>
              </div>
              <div className="md:col-start-8 md:col-span-4">{card}</div>
            </>
          )}
        </Reveal>
      </div>
    </section>
  );
}

function MiniCard({ children }) {
  return (
    <div className="glass p-6 flex flex-col gap-4" style={{ borderRadius: 10 }}>
      {children}
    </div>
  );
}

export default function LandingPage() {
  const { isLoaded, isSignedIn } = useAuth();

  // Signed-in users skip the marketing page and land straight on their dashboard.
  // Wait for Clerk to load first so we don't flash the landing then redirect.
  if (isLoaded && isSignedIn) return <Navigate to="/dashboard" replace />;

  return (
    <div style={{ background: "var(--color-page)" }}>
      {/* masthead */}
      <div className="glass-nav sticky top-0 z-50">
        <div className={`${PAGE} py-4 flex justify-between items-center`}>
          <Link to="/" className="serif" style={{ fontSize: 24, fontWeight: 700, letterSpacing: "-0.02em" }}>DEVPULSE</Link>
          <NavAuth />
        </div>
      </div>
      <div className={`${PAGE} pt-4`}>
        <p className="mono pb-8" style={{ color: "var(--color-muted)" }}>
          A developer&apos;s daily brief · built on your GitHub
        </p>
      </div>

      {/* hero */}
      <section style={{ borderTop: "1px solid var(--color-hairline)" }}>
        <div className={`${PAGE} py-24 md:py-32 flex flex-col md:flex-row gap-16 md:gap-8 items-center`}>
          <motion.div
            className="w-full md:w-3/5"
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
          >
            <h1 className="serif" style={{ fontSize: 68, fontWeight: 700, lineHeight: 1.08, letterSpacing: "-0.02em", margin: 0 }}>
              The developer&apos;s<br />daily brief,<br />
              <span className="italic" style={{ color: "var(--color-accent)" }}>filed automatically.</span>
            </h1>
            <p className="mt-8" style={{ fontSize: 20, lineHeight: 1.6, color: "var(--color-ink)", maxWidth: "36rem" }}>
              DevPulse reads your GitHub activity and emails you a composed digest — commits,
              reviews, streaks, and the pull requests waiting for you, on your schedule.
            </p>
            <div className="mt-12 flex items-center gap-6">
              <SignInPill className="px-8 py-4" />
            </div>
          </motion.div>
          <motion.div
            className="w-full md:w-2/5"
            id="sample"
            initial={{ opacity: 0, y: 30, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ duration: 0.8, delay: 0.15, ease: [0.22, 1, 0.36, 1] }}
          >
            <DigestSample />
          </motion.div>
        </div>
      </section>

      {/* 01 — ACCURATE */}
      <Feature
        num="01" label="ACCURATE"
        heading="Every contribution," accent="counted." tail=""
        lede="Real GitHub activity via GraphQL — commits, PRs, issues, reviews — across private and public repos, nothing missed."
        card={
          <MiniCard>
            <div className="flex items-center gap-3 pb-4" style={{ borderBottom: "1px solid var(--color-hairline)" }}>
              <span className="mono" style={{ color: "var(--color-accent)" }}>{"{ }"}</span>
              <span className="mono">GraphQL · synced 2 min ago</span>
            </div>
            <div className="flex flex-col gap-2">
              {["me/aria", "acme/api-services", "me/dotfiles"].map((r) => (
                <span key={r} className="mono" style={{ textTransform: "none", fontSize: 13 }}>{r}</span>
              ))}
            </div>
          </MiniCard>
        }
      />

      {/* 02 — ACTION (card left) */}
      <Feature
        num="02" label="ACTION" flip
        heading="The PRs" accent="waiting" tail="on you."
        lede="Review-requested and your own open PRs, oldest first, with size and status flags so you know exactly what to touch."
        card={
          <MiniCard>
            <p className="mono" style={{ color: "var(--color-muted)" }}>me/aria #124</p>
            <p style={{ fontWeight: 600 }}>Refactor auth</p>
            <div className="mono flex gap-3" style={{ fontSize: 12, textTransform: "none" }}>
              <span style={{ color: "var(--color-ok)" }}>+254</span>
              <span style={{ color: "var(--color-bad)" }}>−120</span>
              <span style={{ color: "var(--color-muted)" }}>14 files</span>
            </div>
            <div className="flex flex-wrap gap-2 mt-1">
              <span className="mono" style={{ fontSize: 11, padding: "3px 8px", borderRadius: 6, background: "var(--color-conflict-bg)", color: "var(--color-conflict-fg)", textTransform: "none" }}>Conflict</span>
              <span className="mono" style={{ fontSize: 11, padding: "3px 8px", borderRadius: 6, border: "1px solid var(--color-accent)", color: "var(--color-accent)", textTransform: "none" }}>Review requested</span>
            </div>
          </MiniCard>
        }
      />

      {/* 03 — CADENCE */}
      <Feature
        num="03" label="CADENCE"
        heading="Your" accent="pace," tail="not the overload."
        lede="Choose delivery — off, every 6h, 12h, daily, or weekly. One composed email, delivered on your cadence."
        card={
          <MiniCard>
            {["6h", "12h", "Daily", "Weekly"].map((o) => {
              const on = o === "Daily";
              return (
                <div
                  key={o}
                  className="flex justify-between items-center px-3 py-2"
                  style={on ? { background: "#fff", border: "1px solid var(--color-hairline)", borderRadius: 8 } : {}}
                >
                  <span className="mono" style={{ textTransform: "none", color: on ? "var(--color-accent)" : "var(--color-muted)", fontWeight: on ? 700 : 400 }}>
                    {o}{on ? " ✓" : ""}
                  </span>
                </div>
              );
            })}
          </MiniCard>
        }
      />

      {/* 04 — SCOPE (card left) */}
      <Feature
        num="04" label="SCOPE" flip
        heading="Only the repos you" accent="care" tail="about."
        lede="Track specific repositories, or leave it empty to cover everything. Mute the noise from legacy projects and monorepos."
        card={
          <MiniCard>
            <p className="mono">Tracked</p>
            <div className="flex flex-col gap-2">
              {["me/aria", "core-libs"].map((r) => (
                <span key={r} className="mono" style={{ textTransform: "none", fontSize: 13, padding: "4px 8px", background: "#fff", border: "1px solid var(--color-hairline)", borderRadius: 6 }}>{r}</span>
              ))}
            </div>
            <p className="mono italic" style={{ textTransform: "none", fontSize: 11, color: "var(--color-muted)" }}>empty = all repos</p>
          </MiniCard>
        }
      />

      {/* closing */}
      <section style={{ borderTop: "1px solid var(--color-hairline)" }}>
        <div className={`${PAGE} py-24 md:py-32`}>
          <Reveal>
            <h2 className="serif italic" style={{ fontSize: 64, fontWeight: 700, color: "var(--color-accent)", margin: "0 0 32px" }}>
              Start your brief.
            </h2>
            <SignInPill className="px-8 py-4" label="Get started" />
          </Reveal>
        </div>
      </section>

      {/* footer */}
      <footer className={`${PAGE} pb-10`}>
        <div className="rule pt-8 flex flex-col md:flex-row justify-between items-center gap-4">
          <div className="serif" style={{ fontSize: 24, fontWeight: 700 }}>DEVPULSE</div>
          <div className="flex gap-6">
            <a className="mono" href="https://github.com/HardityaGhuman/DevPulse" target="_blank" rel="noreferrer">GitHub</a>
          </div>
          <div className="mono" style={{ color: "var(--color-muted)" }}>2026 · built for developers</div>
        </div>
      </footer>
    </div>
  );
}
