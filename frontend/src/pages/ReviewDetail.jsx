import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft, Code2, GitPullRequest, Bug, Shield, Lightbulb, ThumbsUp, FileCode, Copy, Check, BarChart3 } from "lucide-react";
import api from "@/lib/api";
import { getScoreColor, getSeverityColor, formatDate } from "@/lib/utils";

export default function ReviewDetail() {
  const { id } = useParams();
  const [review, setReview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    api.get(`/api/review/${id}`)
      .then((res) => setReview(res.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [id]);

  const handleCopy = () => {
    if (review?.share_token) {
      navigator.clipboard.writeText(`${window.location.origin}/share/${review.share_token}`);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="h-8 w-48 bg-surface rounded animate-pulse" />
        <div className="card p-6 h-48 animate-pulse" />
      </div>
    );
  }

  if (!review) {
    return (
      <div className="card p-12 text-center">
        <p className="text-muted">Review not found</p>
        <Link to="/history" className="text-accent text-sm mt-2 inline-block no-underline">Back to history</Link>
      </div>
    );
  }

  const r = review.review_result || {};
  const isCode = review.type === "code";

  return (
    <div className="space-y-6">
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="flex items-center gap-3">
        <Link to="/history" className="p-2 rounded-lg hover:bg-surface transition-colors text-muted hover:text-primary no-underline">
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-primary flex items-center gap-2">
            {isCode ? <Code2 className="w-6 h-6 text-accent" /> : <GitPullRequest className="w-6 h-6 text-success" />}
            {isCode ? `${review.language || "Code"} Review` : review.repo_name || "PR Review"}
          </h1>
          <p className="text-sm text-muted">{formatDate(review.created_at)}</p>
        </div>
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
        <div className="flex items-center gap-3 pt-4 border-t border-border">
          {r.complexity && (
            <span className="text-xs text-muted flex items-center gap-1">
              <BarChart3 className="w-3 h-3" /> Complexity: <span className="text-primary">{r.complexity.rating}</span>
            </span>
          )}
          {r.risk_level && (
            <span className="text-xs text-muted">
              Risk: <span className={r.risk_level === "high" ? "text-destructive" : r.risk_level === "medium" ? "text-amber-400" : "text-success"}>{r.risk_level}</span>
            </span>
          )}
          {r.merge_recommendation && (
            <span className="text-xs text-muted">Merge: <span className="text-primary">{r.merge_recommendation}</span></span>
          )}
          <button onClick={handleCopy} className="ml-auto flex items-center gap-1 text-xs text-muted hover:text-accent transition-colors">
            {copied ? <Check className="w-3 h-3 text-success" /> : <Copy className="w-3 h-3" />}
            {copied ? "Copied!" : "Share link"}
          </button>
        </div>
      </motion.div>

      {/* Files (PR only) */}
      {r.files_reviewed?.length > 0 && (
        <div className="card p-6">
          <h3 className="text-base font-semibold text-primary flex items-center gap-2 mb-4">
            <FileCode className="w-4 h-4 text-accent" /> Files ({r.files_reviewed.length})
          </h3>
          <div className="space-y-3">
            {r.files_reviewed.map((f, i) => (
              <div key={i} className="bg-surface-alt rounded-lg p-3">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-mono text-primary">{f.filename}</span>
                  <span className={`text-xs font-medium ${f.verdict === "approve" ? "text-success" : f.verdict === "request-changes" ? "text-destructive" : "text-amber-400"}`}>{f.verdict}</span>
                </div>
                {f.comments?.map((c, j) => <p key={j} className="text-xs text-muted">• {c}</p>)}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Bugs */}
      {r.bugs?.length > 0 && (
        <div className="card p-6">
          <h3 className="text-base font-semibold text-primary flex items-center gap-2 mb-4"><Bug className="w-4 h-4 text-destructive" /> Bugs ({r.bugs.length})</h3>
          <div className="space-y-3">
            {r.bugs.map((b, i) => (
              <div key={i} className="bg-surface-alt rounded-lg p-3">
                <span className={`text-xs font-medium ${getSeverityColor(b.severity)}`}>{b.severity?.toUpperCase()}</span>
                {b.line && <span className="text-xs text-muted ml-2">Line {b.line}</span>}
                <p className="text-sm text-primary mt-1">{b.description}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Security */}
      {r.security?.length > 0 && (
        <div className="card p-6">
          <h3 className="text-base font-semibold text-primary flex items-center gap-2 mb-4"><Shield className="w-4 h-4 text-amber-400" /> Security ({r.security.length})</h3>
          <div className="space-y-3">
            {r.security.map((s, i) => (
              <div key={i} className="bg-surface-alt rounded-lg p-3">
                <span className={`text-xs font-medium ${getSeverityColor(s.severity)}`}>{s.severity?.toUpperCase()}</span>
                <p className="text-sm text-primary mt-1">{s.issue}</p>
                <p className="text-xs text-muted mt-1">{s.recommendation}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Suggestions */}
      {r.suggestions?.length > 0 && (
        <div className="card p-6">
          <h3 className="text-base font-semibold text-primary flex items-center gap-2 mb-4"><Lightbulb className="w-4 h-4 text-accent" /> Suggestions</h3>
          <div className="space-y-3">
            {r.suggestions.map((s, i) => (
              <div key={i} className="bg-surface-alt rounded-lg p-3">
                <span className="inline-block text-xs bg-accent/10 text-accent px-2 py-0.5 rounded mb-1">{s.category}</span>
                <p className="text-sm text-primary">{s.description}</p>
                {s.improved_snippet && <pre className="mt-2 text-xs bg-code-bg rounded p-2 overflow-x-auto">{s.improved_snippet}</pre>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Positives */}
      {r.positive?.length > 0 && (
        <div className="card p-6">
          <h3 className="text-base font-semibold text-primary flex items-center gap-2 mb-4"><ThumbsUp className="w-4 h-4 text-success" /> What's Good</h3>
          <ul className="space-y-2">
            {r.positive.map((p, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-muted"><span className="text-success mt-0.5">✓</span>{p}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Source Code (for code reviews) */}
      {isCode && review.input_content && (
        <div className="card p-6">
          <h3 className="text-base font-semibold text-primary mb-4">Source Code</h3>
          <pre className="text-sm overflow-x-auto">{review.input_content}</pre>
        </div>
      )}
    </div>
  );
}
