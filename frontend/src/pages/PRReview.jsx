import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { GitPullRequest, Send, Loader2, FileCode, Bug, Lightbulb, ThumbsUp, AlertTriangle, Copy, Check } from "lucide-react";
import api from "@/lib/api";
import { getScoreColor, getSeverityColor } from "@/lib/utils";

export default function PRReview() {
  const [prUrl, setPrUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);

  const handleSubmit = async () => {
    if (!prUrl.trim()) return;
    setLoading(true);
    setError("");
    setResult(null);

    try {
      const res = await api.post("/api/review/pr", { pr_url: prUrl });
      setResult(res.data);
    } catch (e) {
      setError(e.response?.data?.detail || "Failed to review PR. Please check the URL and try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleCopyShareLink = () => {
    if (result?.share_token) {
      navigator.clipboard.writeText(`${window.location.origin}/share/${result.share_token}`);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const review = result?.review_result;

  const verdictColors = {
    approve: "text-success",
    "request-changes": "text-destructive",
    comment: "text-amber-400",
    "needs-discussion": "text-amber-400",
  };

  return (
    <div className="space-y-6">
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-2xl font-bold text-primary flex items-center gap-2">
          <GitPullRequest className="w-6 h-6 text-success" />
          PR Review
        </h1>
        <p className="text-muted mt-1">Paste a GitHub PR URL for comprehensive AI analysis</p>
      </motion.div>

      {/* Input */}
      <motion.div className="card p-6" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
        <label className="text-sm text-muted block mb-2">Pull Request URL</label>
        <div className="flex gap-3">
          <input
            value={prUrl}
            onChange={(e) => setPrUrl(e.target.value)}
            placeholder="https://github.com/owner/repo/pull/123"
            className="flex-1 bg-surface-alt border border-border rounded-lg px-4 py-2.5 text-sm text-primary focus:border-accent outline-none placeholder:text-muted/50"
            onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
          />
          <button
            onClick={handleSubmit}
            disabled={loading || !prUrl.trim()}
            className="inline-flex items-center gap-2 bg-accent text-white px-6 py-2.5 rounded-lg text-sm font-medium hover:bg-accent/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            {loading ? "Analyzing..." : "Review PR"}
          </button>
        </div>
        {loading && (
          <p className="text-xs text-muted mt-3">Fetching PR diff and analyzing with AI — this may take a moment...</p>
        )}
      </motion.div>

      {error && (
        <div className="card p-4 border-destructive/50">
          <p className="text-sm text-destructive">{error}</p>
        </div>
      )}

      <AnimatePresence>
        {review && (
          <motion.div className="space-y-4" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
            {/* Summary */}
            <div className="card p-6">
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <h2 className="text-lg font-semibold text-primary mb-2">Review Summary</h2>
                  <p className="text-sm text-muted leading-relaxed">{review.summary}</p>
                </div>
                <div className="text-center ml-6">
                  <div className={`text-4xl font-bold ${getScoreColor(review.score)}`}>{review.score}</div>
                  <p className="text-xs text-muted mt-1">/ 10</p>
                </div>
              </div>
              <div className="flex flex-wrap items-center gap-3 pt-4 border-t border-border">
                <span className="text-xs bg-surface-alt px-2 py-1 rounded text-muted">
                  Risk: <span className={review.risk_level === "high" ? "text-destructive" : review.risk_level === "medium" ? "text-amber-400" : "text-success"}>{review.risk_level}</span>
                </span>
                <span className={`text-xs font-medium ${verdictColors[review.merge_recommendation] || "text-muted"}`}>
                  Recommendation: {review.merge_recommendation}
                </span>
                <button onClick={handleCopyShareLink} className="ml-auto flex items-center gap-1 text-xs text-muted hover:text-accent transition-colors">
                  {copied ? <Check className="w-3 h-3 text-success" /> : <Copy className="w-3 h-3" />}
                  {copied ? "Copied!" : "Share"}
                </button>
              </div>
            </div>

            {/* Files Reviewed */}
            {review.files_reviewed?.length > 0 && (
              <div className="card p-6">
                <h3 className="text-base font-semibold text-primary flex items-center gap-2 mb-4">
                  <FileCode className="w-4 h-4 text-accent" />
                  Files Reviewed ({review.files_reviewed.length})
                </h3>
                <div className="space-y-3">
                  {review.files_reviewed.map((file, i) => (
                    <div key={i} className="bg-surface-alt rounded-lg p-3">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm text-primary font-mono">{file.filename}</span>
                        <span className={`text-xs font-medium ${verdictColors[file.verdict] || "text-muted"}`}>
                          {file.verdict}
                        </span>
                      </div>
                      {file.comments?.map((c, j) => (
                        <p key={j} className="text-xs text-muted mt-1">• {c}</p>
                      ))}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Bugs */}
            {review.bugs?.length > 0 && (
              <div className="card p-6">
                <h3 className="text-base font-semibold text-primary flex items-center gap-2 mb-4">
                  <Bug className="w-4 h-4 text-destructive" /> Bugs ({review.bugs.length})
                </h3>
                <div className="space-y-3">
                  {review.bugs.map((bug, i) => (
                    <div key={i} className="bg-surface-alt rounded-lg p-3">
                      <span className={`text-xs font-medium ${getSeverityColor(bug.severity)}`}>{bug.severity?.toUpperCase()}</span>
                      <p className="text-sm text-primary mt-1">{bug.description}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Suggestions */}
            {review.suggestions?.length > 0 && (
              <div className="card p-6">
                <h3 className="text-base font-semibold text-primary flex items-center gap-2 mb-4">
                  <Lightbulb className="w-4 h-4 text-accent" /> Suggestions
                </h3>
                <div className="space-y-3">
                  {review.suggestions.map((s, i) => (
                    <div key={i} className="bg-surface-alt rounded-lg p-3">
                      <span className="inline-block text-xs bg-accent/10 text-accent px-2 py-0.5 rounded mb-1">{s.category}</span>
                      <p className="text-sm text-primary">{s.description}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Positives */}
            {review.positive?.length > 0 && (
              <div className="card p-6">
                <h3 className="text-base font-semibold text-primary flex items-center gap-2 mb-4">
                  <ThumbsUp className="w-4 h-4 text-success" /> What's Good
                </h3>
                <ul className="space-y-2">
                  {review.positive.map((p, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-muted">
                      <span className="text-success mt-0.5">✓</span> {p}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
