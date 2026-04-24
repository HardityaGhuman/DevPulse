import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Code2, Send, Loader2, Bug, Shield, Lightbulb, ThumbsUp, BarChart3, Copy, Check } from "lucide-react";
import api from "@/lib/api";
import { getScoreColor, getSeverityColor } from "@/lib/utils";

const LANGUAGES = [
  "Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "Go", "Rust",
  "Ruby", "PHP", "Swift", "Kotlin", "SQL", "HTML", "CSS", "Shell",
];

export default function CodeReview() {
  const [code, setCode] = useState("");
  const [language, setLanguage] = useState("Python");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);

  const handleSubmit = async () => {
    if (!code.trim()) return;
    setLoading(true);
    setError("");
    setResult(null);

    try {
      const res = await api.post("/api/review/code", { code, language });
      setResult(res.data);
    } catch (e) {
      setError(e.response?.data?.detail || "Failed to review code. Please try again.");
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

  return (
    <div className="space-y-6">
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-2xl font-bold text-primary flex items-center gap-2">
          <Code2 className="w-6 h-6 text-accent" />
          Code Review
        </h1>
        <p className="text-muted mt-1">Paste your code below for instant AI-powered analysis</p>
      </motion.div>

      {/* Input Area */}
      <motion.div className="card p-6 space-y-4" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
        <div className="flex items-center gap-4">
          <div>
            <label className="text-sm text-muted block mb-1">Language</label>
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className="bg-surface-alt border border-border rounded-lg px-3 py-2 text-sm text-primary focus:border-accent outline-none"
            >
              {LANGUAGES.map((l) => (
                <option key={l} value={l}>{l}</option>
              ))}
            </select>
          </div>
          <div className="flex-1" />
          <button
            onClick={handleSubmit}
            disabled={loading || !code.trim()}
            className="inline-flex items-center gap-2 bg-accent text-white px-6 py-2 rounded-lg text-sm font-medium hover:bg-accent/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            {loading ? "Analyzing..." : "Review Code"}
          </button>
        </div>

        <textarea
          value={code}
          onChange={(e) => setCode(e.target.value)}
          placeholder="Paste your code here..."
          rows={16}
          className="w-full bg-code-bg border border-border rounded-lg p-4 text-sm text-primary font-mono resize-y focus:border-accent outline-none placeholder:text-muted/50"
        />
      </motion.div>

      {error && (
        <div className="card p-4 border-destructive/50">
          <p className="text-sm text-destructive">{error}</p>
        </div>
      )}

      {/* Result */}
      <AnimatePresence>
        {review && (
          <motion.div
            className="space-y-4"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.4 }}
          >
            {/* Summary + Score */}
            <div className="card p-6">
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <h2 className="text-lg font-semibold text-primary mb-2">Review Summary</h2>
                  <p className="text-sm text-muted leading-relaxed">{review.summary}</p>
                </div>
                <div className="text-center ml-6">
                  <div className={`text-4xl font-bold ${getScoreColor(review.score)}`}>
                    {review.score}
                  </div>
                  <p className="text-xs text-muted mt-1">/ 10</p>
                </div>
              </div>
              <div className="flex items-center gap-3 pt-4 border-t border-border">
                <div className="flex items-center gap-2 text-xs text-muted">
                  <BarChart3 className="w-3 h-3" />
                  Complexity: <span className="text-primary">{review.complexity?.rating}</span>
                </div>
                <button onClick={handleCopyShareLink} className="ml-auto flex items-center gap-1 text-xs text-muted hover:text-accent transition-colors">
                  {copied ? <Check className="w-3 h-3 text-success" /> : <Copy className="w-3 h-3" />}
                  {copied ? "Copied!" : "Share"}
                </button>
              </div>
            </div>

            {/* Bugs */}
            {review.bugs?.length > 0 && (
              <div className="card p-6">
                <h3 className="text-base font-semibold text-primary flex items-center gap-2 mb-4">
                  <Bug className="w-4 h-4 text-destructive" />
                  Bugs Found ({review.bugs.length})
                </h3>
                <div className="space-y-3">
                  {review.bugs.map((bug, i) => (
                    <div key={i} className="bg-surface-alt rounded-lg p-3">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`text-xs font-medium ${getSeverityColor(bug.severity)}`}>
                          {bug.severity?.toUpperCase()}
                        </span>
                        {bug.line && <span className="text-xs text-muted">Line {bug.line}</span>}
                      </div>
                      <p className="text-sm text-primary">{bug.description}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Security */}
            {review.security?.length > 0 && (
              <div className="card p-6">
                <h3 className="text-base font-semibold text-primary flex items-center gap-2 mb-4">
                  <Shield className="w-4 h-4 text-amber-400" />
                  Security Issues ({review.security.length})
                </h3>
                <div className="space-y-3">
                  {review.security.map((sec, i) => (
                    <div key={i} className="bg-surface-alt rounded-lg p-3">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`text-xs font-medium ${getSeverityColor(sec.severity)}`}>
                          {sec.severity?.toUpperCase()}
                        </span>
                      </div>
                      <p className="text-sm text-primary mb-1">{sec.issue}</p>
                      <p className="text-xs text-muted">{sec.recommendation}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Suggestions */}
            {review.suggestions?.length > 0 && (
              <div className="card p-6">
                <h3 className="text-base font-semibold text-primary flex items-center gap-2 mb-4">
                  <Lightbulb className="w-4 h-4 text-accent" />
                  Suggestions ({review.suggestions.length})
                </h3>
                <div className="space-y-3">
                  {review.suggestions.map((sug, i) => (
                    <div key={i} className="bg-surface-alt rounded-lg p-3">
                      <span className="inline-block text-xs bg-accent/10 text-accent px-2 py-0.5 rounded mb-2">
                        {sug.category}
                      </span>
                      <p className="text-sm text-primary">{sug.description}</p>
                      {sug.improved_snippet && (
                        <pre className="mt-2 text-xs bg-code-bg rounded p-2 overflow-x-auto">
                          {sug.improved_snippet}
                        </pre>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Positives */}
            {review.positive?.length > 0 && (
              <div className="card p-6">
                <h3 className="text-base font-semibold text-primary flex items-center gap-2 mb-4">
                  <ThumbsUp className="w-4 h-4 text-success" />
                  What's Good
                </h3>
                <ul className="space-y-2">
                  {review.positive.map((p, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-muted">
                      <span className="text-success mt-0.5">✓</span>
                      {p}
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
