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
    <div className="space-y-10 max-w-5xl mx-auto pb-20">
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-4xl font-black text-primary flex items-center gap-3">
          <div className="w-12 h-12 rounded-2xl bg-success/10 flex items-center justify-center border border-success/20">
            <GitPullRequest className="w-7 h-7 text-success" />
          </div>
          PR Review
        </h1>
        <p className="text-muted text-lg mt-3 font-medium">Paste a GitHub PR URL for comprehensive AI analysis</p>
      </motion.div>

      {/* Input */}
      <motion.div 
        className="glass-card p-8 rounded-[32px] space-y-6 relative overflow-hidden" 
        initial={{ opacity: 0, y: 16 }} 
        animate={{ opacity: 1, y: 0 }} 
        transition={{ delay: 0.1 }}
      >
        <div className="space-y-2">
          <label className="text-sm font-bold text-muted uppercase tracking-wider mb-2 block">Pull Request URL</label>
          <div className="flex flex-col sm:flex-row gap-4">
            <input
              value={prUrl}
              onChange={(e) => setPrUrl(e.target.value)}
              placeholder="https://github.com/owner/repo/pull/123"
              className="flex-1 bg-white/5 border border-white/10 rounded-xl px-5 py-3.5 text-base text-primary focus:border-accent outline-none placeholder:text-muted/30 backdrop-blur-sm"
              onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
            />
            <button
              onClick={handleSubmit}
              disabled={loading || !prUrl.trim()}
              className="group inline-flex items-center justify-center gap-2 bg-accent text-white px-8 py-3.5 rounded-xl text-lg font-bold hover:scale-[1.02] transition-all disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap shadow-xl shadow-accent/20"
            >
              {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5 group-hover:translate-x-1 group-hover:-translate-y-1 transition-transform" />}
              {loading ? "Analyzing..." : "Review PR"}
            </button>
          </div>
          {loading && (
            <motion.p 
              initial={{ opacity: 0 }} 
              animate={{ opacity: 1 }} 
              className="text-sm font-medium text-muted mt-4 flex items-center gap-2"
            >
              <div className="w-2 h-2 rounded-full bg-accent animate-pulse" />
              Fetching PR diff and analyzing with AI — this may take a moment...
            </motion.p>
          )}
        </div>
      </motion.div>

      {error && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="glass-card p-6 border-destructive/30 rounded-2xl bg-destructive/5">
          <p className="text-destructive font-bold flex items-center gap-2">
            <AlertTriangle className="w-5 h-5" />
            {error}
          </p>
        </motion.div>
      )}

      <AnimatePresence>
        {review && (
          <motion.div 
            className="space-y-8" 
            initial={{ opacity: 0, y: 30 }} 
            animate={{ opacity: 1, y: 0 }} 
            exit={{ opacity: 0 }}
            transition={{ duration: 0.6, ease: "easeOut" }}
          >
            {/* Summary */}
            <div className="glass-card p-10 rounded-[32px] relative overflow-hidden">
              <div className="absolute top-0 right-0 w-64 h-64 bg-success/5 rounded-full blur-[100px] -z-10" />
              <div className="flex flex-col md:flex-row items-start justify-between gap-8">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="w-8 h-8 rounded-lg bg-success/10 flex items-center justify-center border border-success/20">
                      <Lightbulb className="w-4 h-4 text-success" />
                    </div>
                    <h2 className="text-2xl font-bold text-primary">Review Summary</h2>
                  </div>
                  <p className="text-lg text-muted leading-relaxed font-medium">{review.summary}</p>
                </div>
                <div className="flex flex-col items-center justify-center p-8 bg-white/5 rounded-3xl border border-white/5 min-w-[160px]">
                  <div className={`text-6xl font-black tracking-tighter ${getScoreColor(review.score)}`}>
                    {review.score}
                  </div>
                  <p className="text-sm font-bold text-muted uppercase tracking-widest mt-2">Score / 10</p>
                </div>
              </div>
              
              <div className="flex flex-wrap items-center gap-4 pt-8 mt-8 border-t border-white/5">
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/5 text-sm font-bold text-muted border border-white/5">
                  Risk Level: 
                  <span className={`uppercase tracking-wider ${
                    review.risk_level === "high" ? "text-destructive" : review.risk_level === "medium" ? "text-amber-400" : "text-success"
                  }`}>
                    {review.risk_level}
                  </span>
                </div>
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/5 text-sm font-bold text-muted border border-white/5">
                  Recommendation: 
                  <span className={`uppercase tracking-wider ${verdictColors[review.merge_recommendation] || "text-muted"}`}>
                    {review.merge_recommendation?.replace("-", " ")}
                  </span>
                </div>
                <button 
                  onClick={handleCopyShareLink} 
                  className="ml-auto flex items-center gap-2 text-sm font-bold text-accent hover:text-accent/80 transition-colors px-4 py-2 rounded-xl bg-accent/5 border border-accent/10"
                >
                  {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                  {copied ? "Copied!" : "Share Review"}
                </button>
              </div>
            </div>

            {/* Files Reviewed */}
            {review.files_reviewed?.length > 0 && (
              <div className="glass-card p-8 rounded-[32px]">
                <h3 className="text-xl font-bold text-primary flex items-center gap-3 mb-6">
                  <div className="w-10 h-10 rounded-xl bg-accent/10 flex items-center justify-center border border-accent/20">
                    <FileCode className="w-5 h-5 text-accent" />
                  </div>
                  Files Reviewed ({review.files_reviewed.length})
                </h3>
                <div className="grid gap-4">
                  {review.files_reviewed.map((file, i) => (
                    <div key={i} className="bg-white/5 rounded-2xl p-5 border border-white/5 group-hover:border-white/10 transition-colors">
                      <div className="flex items-center justify-between mb-3">
                        <span className="text-base text-primary font-mono font-medium">{file.filename}</span>
                        <span className={`px-2.5 py-1 rounded-lg text-xs font-black tracking-wider uppercase bg-white/5 border border-white/5 ${verdictColors[file.verdict] || "text-muted"}`}>
                          {file.verdict?.replace("-", " ")}
                        </span>
                      </div>
                      <div className="space-y-2">
                        {file.comments?.map((c, j) => (
                          <div key={j} className="flex items-start gap-2">
                            <div className="w-1.5 h-1.5 rounded-full bg-muted mt-1.5 flex-shrink-0" />
                            <p className="text-sm text-muted font-medium">{c}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Bugs */}
              {review.bugs?.length > 0 && (
                <div className="glass-card p-8 rounded-[32px]">
                  <h3 className="text-xl font-bold text-primary flex items-center gap-3 mb-6">
                    <div className="w-10 h-10 rounded-xl bg-destructive/10 flex items-center justify-center border border-destructive/20">
                      <Bug className="w-5 h-5 text-destructive" />
                    </div>
                    Bugs ({review.bugs.length})
                  </h3>
                  <div className="space-y-4">
                    {review.bugs.map((bug, i) => (
                      <div key={i} className="bg-white/5 rounded-2xl p-5 border border-white/5">
                        <span className={`px-2.5 py-1 rounded-lg text-xs font-black tracking-wider uppercase bg-white/5 border border-white/5 ${getSeverityColor(bug.severity)}`}>
                          {bug.severity}
                        </span>
                        <p className="text-base text-primary font-medium mt-3 leading-relaxed">{bug.description}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Suggestions */}
              {review.suggestions?.length > 0 && (
                <div className="glass-card p-8 rounded-[32px]">
                  <h3 className="text-xl font-bold text-primary flex items-center gap-3 mb-6">
                    <div className="w-10 h-10 rounded-xl bg-accent/10 flex items-center justify-center border border-accent/20">
                      <Lightbulb className="w-5 h-5 text-accent" />
                    </div>
                    Suggestions
                  </h3>
                  <div className="space-y-4">
                    {review.suggestions.map((s, i) => (
                      <div key={i} className="bg-white/5 rounded-2xl p-5 border border-white/5">
                        <span className="inline-block text-xs font-black tracking-wider uppercase bg-accent/10 text-accent px-3 py-1 rounded-lg mb-3 border border-accent/10">
                          {s.category}
                        </span>
                        <p className="text-base text-primary font-medium leading-relaxed">{s.description}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Positives */}
            {review.positive?.length > 0 && (
              <div className="glass-card p-8 rounded-[32px]">
                <h3 className="text-xl font-bold text-primary flex items-center gap-3 mb-6">
                  <div className="w-10 h-10 rounded-xl bg-success/10 flex items-center justify-center border border-success/20">
                    <ThumbsUp className="w-5 h-5 text-success" />
                  </div>
                  What's Good
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {review.positive.map((p, i) => (
                    <div key={i} className="flex items-start gap-4 p-4 rounded-2xl bg-success/5 border border-success/10">
                      <div className="w-6 h-6 rounded-full bg-success/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                        <Check className="w-3.5 h-3.5 text-success" />
                      </div>
                      <p className="text-base text-primary font-medium leading-relaxed">{p}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
