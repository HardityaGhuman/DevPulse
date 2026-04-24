import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { motion } from "framer-motion";
import { Activity, Code2, GitPullRequest, Bug, Shield, Lightbulb, ThumbsUp, FileCode, BarChart3 } from "lucide-react";
import { getScoreColor, getSeverityColor, formatDate } from "@/lib/utils";

export default function SharedReview() {
  const { token } = useParams();
  const [review, setReview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    const baseUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
    fetch(`${baseUrl}/api/review/share/${token}`)
      .then((res) => {
        if (!res.ok) throw new Error("Not found");
        return res.json();
      })
      .then(setReview)
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, [token]);

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="animate-pulse text-muted">Loading review...</div>
      </div>
    );
  }

  if (error || !review) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="card p-12 text-center">
          <p className="text-muted text-lg">Review not found</p>
          <p className="text-sm text-muted mt-2">This link may be invalid or expired.</p>
        </div>
      </div>
    );
  }

  const r = review.review_result || {};
  const isCode = review.type === "code";

  return (
    <div className="min-h-screen bg-background">
      {/* Nav */}
      <nav className="border-b border-border bg-background/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-accent flex items-center justify-center">
            <Activity className="w-3.5 h-3.5 text-white" />
          </div>
          <span className="text-base font-bold text-primary">DevPulse</span>
          <span className="text-xs text-muted ml-2 bg-surface px-2 py-0.5 rounded">Shared Review</span>
        </div>
      </nav>

      <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
          <h1 className="text-2xl font-bold text-primary flex items-center gap-2">
            {isCode ? <Code2 className="w-6 h-6 text-accent" /> : <GitPullRequest className="w-6 h-6 text-success" />}
            {isCode ? `${review.language || "Code"} Review` : review.repo_name || "PR Review"}
          </h1>
          <p className="text-sm text-muted mt-1">{formatDate(review.created_at)}</p>
        </motion.div>

        {/* Summary */}
        <motion.div className="card p-6" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
          <div className="flex items-start justify-between mb-4">
            <div className="flex-1">
              <h2 className="text-lg font-semibold text-primary mb-2">Summary</h2>
              <p className="text-sm text-muted leading-relaxed">{r.summary}</p>
            </div>
            <div className="text-center ml-6">
              <div className={`text-4xl font-bold ${getScoreColor(r.score)}`}>{r.score}</div>
              <p className="text-xs text-muted mt-1">/ 10</p>
            </div>
          </div>
          {(r.complexity || r.risk_level) && (
            <div className="flex items-center gap-3 pt-4 border-t border-border">
              {r.complexity && <span className="text-xs text-muted flex items-center gap-1"><BarChart3 className="w-3 h-3" /> Complexity: <span className="text-primary">{r.complexity.rating}</span></span>}
              {r.risk_level && <span className="text-xs text-muted">Risk: <span className="text-primary">{r.risk_level}</span></span>}
            </div>
          )}
        </motion.div>

        {r.files_reviewed?.length > 0 && (
          <div className="card p-6">
            <h3 className="text-base font-semibold text-primary flex items-center gap-2 mb-4"><FileCode className="w-4 h-4 text-accent" /> Files</h3>
            <div className="space-y-3">
              {r.files_reviewed.map((f, i) => (
                <div key={i} className="bg-surface-alt rounded-lg p-3">
                  <div className="flex items-center justify-between"><span className="text-sm font-mono text-primary">{f.filename}</span><span className={`text-xs ${f.verdict === "approve" ? "text-success" : "text-amber-400"}`}>{f.verdict}</span></div>
                  {f.comments?.map((c, j) => <p key={j} className="text-xs text-muted mt-1">• {c}</p>)}
                </div>
              ))}
            </div>
          </div>
        )}

        {r.bugs?.length > 0 && (
          <div className="card p-6">
            <h3 className="text-base font-semibold text-primary flex items-center gap-2 mb-4"><Bug className="w-4 h-4 text-destructive" /> Bugs</h3>
            <div className="space-y-3">
              {r.bugs.map((b, i) => (
                <div key={i} className="bg-surface-alt rounded-lg p-3">
                  <span className={`text-xs font-medium ${getSeverityColor(b.severity)}`}>{b.severity?.toUpperCase()}</span>
                  <p className="text-sm text-primary mt-1">{b.description}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {r.suggestions?.length > 0 && (
          <div className="card p-6">
            <h3 className="text-base font-semibold text-primary flex items-center gap-2 mb-4"><Lightbulb className="w-4 h-4 text-accent" /> Suggestions</h3>
            <div className="space-y-3">
              {r.suggestions.map((s, i) => (
                <div key={i} className="bg-surface-alt rounded-lg p-3">
                  <span className="inline-block text-xs bg-accent/10 text-accent px-2 py-0.5 rounded mb-1">{s.category}</span>
                  <p className="text-sm text-primary">{s.description}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {r.positive?.length > 0 && (
          <div className="card p-6">
            <h3 className="text-base font-semibold text-primary flex items-center gap-2 mb-4"><ThumbsUp className="w-4 h-4 text-success" /> Positives</h3>
            <ul className="space-y-2">
              {r.positive.map((p, i) => <li key={i} className="flex items-start gap-2 text-sm text-muted"><span className="text-success">✓</span>{p}</li>)}
            </ul>
          </div>
        )}

        <footer className="text-center py-8">
          <p className="text-xs text-muted">Reviewed with DevPulse — AI-powered developer intelligence</p>
        </footer>
      </div>
    </div>
  );
}
