/*
  DevPulse — Privacy note. A small trigger that opens a compact modal with the
  plain-language privacy summary. Not a full page — intentionally a lightweight
  overlay. Closes on X, click-outside, or Escape.

  The trigger is whatever `children` the caller passes (defaults to "Privacy"),
  wrapped in a reset button so any element can act as the opener.
*/

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X } from "lucide-react";

const CONTACT = "ghumanharditya@gmail.com";

export default function PrivacyNote({ children, className = "", style = {} }) {
  const [open, setOpen] = useState(false);

  // Close on Escape while open.
  useEffect(() => {
    if (!open) return;
    const onKey = (e) => e.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className={`dp-linkreset ${className}`}
        style={style}
      >
        {children ?? <span className="mono">Privacy</span>}
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            // Backdrop — click-outside closes.
            onClick={() => setOpen(false)}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.18 }}
            style={{
              position: "fixed",
              inset: 0,
              zIndex: 100,
              background: "rgba(26,26,26,0.32)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              padding: 16,
            }}
          >
            <motion.div
              role="dialog"
              aria-modal="true"
              aria-label="Privacy"
              onClick={(e) => e.stopPropagation()}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 12 }}
              transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
              style={{
                position: "relative",
                width: "100%",
                maxWidth: 440,
                maxHeight: "85vh",
                overflowY: "auto",
                background: "var(--color-page)",
                border: "1px solid var(--color-hairline)",
                borderRadius: 14,
                boxShadow: "0 24px 60px rgba(26,26,26,0.18)",
                padding: "28px 26px",
              }}
            >
              <button
                type="button"
                onClick={() => setOpen(false)}
                aria-label="Close"
                style={{
                  position: "absolute",
                  top: 16,
                  right: 16,
                  background: "none",
                  border: 0,
                  cursor: "pointer",
                  color: "var(--color-muted)",
                  lineHeight: 0,
                }}
              >
                <X size={18} strokeWidth={2.2} />
              </button>

              <div className="mono" style={{ color: "var(--color-accent)", fontSize: 12, letterSpacing: "0.08em" }}>
                PRIVACY
              </div>
              <h2 className="serif" style={{ fontSize: 26, fontWeight: 700, margin: "6px 0 0" }}>
                The short version
              </h2>

              <div className="rule" style={{ marginTop: 18, paddingTop: 18 }}>
                <ul style={{ margin: 0, padding: 0, listStyle: "none", display: "grid", gap: 12 }}>
                  <li style={{ fontSize: 14, lineHeight: 1.55 }}>
                    I store your email, GitHub username, and the activity summarized
                    (commits, PRs, streaks) plus the repos you choose to track.
                  </li>
                  <li style={{ fontSize: 14, lineHeight: 1.55 }}>
                    I <strong>never store your GitHub token</strong> — it's fetched live per
                    request and discarded.
                  </li>
                  <li style={{ fontSize: 14, lineHeight: 1.55 }}>
                    Your activity is sent to an LLM (Google Gemini / Groq) to write the summary,
                    and to Resend to send the email.
                  </li>
                  <li style={{ fontSize: 14, lineHeight: 1.55 }}>
                    New accounts default to <strong>off</strong>. You're only emailed if you opt
                    in, and every email has one-click unsubscribe.
                  </li>
                  <li style={{ fontSize: 14, lineHeight: 1.55 }}>
                    Want your data deleted? Email me and it's gone.
                  </li>
                </ul>
              </div>

              <div className="rule mono" style={{ marginTop: 18, paddingTop: 14, fontSize: 12, color: "var(--color-muted)" }}>
                Questions?{" "}
                <a href={`mailto:${CONTACT}`} style={{ color: "var(--color-accent)" }}>
                  {CONTACT}
                </a>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
