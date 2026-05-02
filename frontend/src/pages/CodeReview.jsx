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
    <div className="space-y-10 max-w-5xl mx-auto pb-20">
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-4xl font-black text-primary flex items-center gap-3">
          <div className="w-12 h-12 rounded-2xl bg-accent/10 flex items-center justify-center border border-accent/20">
            <Code2 className="w-7 h-7 text-accent" />
          </div>
          Code Review
        </h1>
        <p className="text-muted text-lg mt-3 font-medium">Paste your code below for instant AI-powered analysis</p>
      </motion.div>

      {/* Input Area */}
      <motion.div 
        className="glass-card p-8 rounded-[32px] space-y-6 relative overflow-hidden" 
        initial={{ opacity: 0, y: 16 }} 
        animate={{ opacity: 1, y: 0 }} 
        transition={{ delay: 0.1 }}
      >
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-6">
          <div className="flex-1 max-w-xs">
            <label className="text-sm font-bold text-muted uppercase tracking-wider mb-2 block">Language</label>
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-primary font-medium focus:border-accent outline-none appearance-none"
            >
              {LANGUAGES.map((l) => (
                <option key={l} value={l} className="bg-surface">{l}</option>
              ))}
            </select>
          </div>
          
          <button
            onClick={handleSubmit}
            disabled={loading || !code.trim()}
            className="group inline-flex items-center justify-center gap-2 bg-accent text-white px-8 py-3.5 rounded-xl text-lg font-bold hover:scale-[1.02] transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-xl shadow-accent/20"
          >
            {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5 group-hover:translate-x-1 group-hover:-translate-y-1 transition-transform" />}
            {loading ? "Analyzing..." : "Review Code"}
          </button>
        </div>

        <div className="relative group">
          <div className="absolute inset-0 bg-gradient-to-br from-accent/5 to-accent-alt/5 rounded-2xl opacity-0 group-focus-within:opacity-100 transition-opacity pointer-events-none" />
          <textarea
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="Paste your code here..."
            rows={12}
            className="w-full bg-code-bg/50 border border-white/5 rounded-2xl p-6 text-base text-primary font-mono resize-y focus:border-accent/50 outline-none placeholder:text-muted/30 backdrop-blur-sm relative z-10"
          />
        </div>
      </motion.div>

      {error && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="glass-card p-6 border-destructive/30 rounded-2xl bg-destructive/5">
          <p className="text-destructive font-bold flex items-center gap-2">
            <Bug className="w-5 h-5" />
            {error}
          </p>
        </motion.div>
      )}

      {/* Result */}
      <AnimatePresence>
        {review && (
          <motion.div
            className="space-y-8"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.6, ease: "easeOut" }}
          >
            {/* Summary + Score */}
            <div className="glass-card p-10 rounded-[32px] relative overflow-hidden">
              <div className="absolute top-0 right-0 w-64 h-64 bg-accent/5 rounded-full blur-[100px] -z-10" />
              <div className="flex flex-col md:flex-row items-start justify-between gap-8">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="w-8 h-8 rounded-lg bg-accent/10 flex items-center justify-center border border-accent/20">
                      <Lightbulb className="w-4 h-4 text-accent" />
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
              <div className="flex items-center gap-6 pt-8 mt-8 border-t border-white/5">
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/5 text-sm font-bold text-muted">
                  <BarChart3 className="w-4 h-4" />
                  Complexity: <span className="text-primary">{review.complexity?.rating}</span>
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

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Bugs */}
              {review.bugs?.length > 0 && (
                <div className="glass-card p-8 rounded-[32px]">
                  <h3 className="text-xl font-bold text-primary flex items-center gap-3 mb-6">
                    <div className="w-10 h-10 rounded-xl bg-destructive/10 flex items-center justify-center border border-destructive/20">
                      <Bug className="w-5 h-5 text-destructive" />
                    </div>
                    Bugs Found ({review.bugs.length})
                  </h3>
                  <div className="space-y-4">
                    {review.bugs.map((bug, i) => (
                      <div key={i} className="bg-white/5 rounded-2xl p-5 border border-white/5">
                        <div className="flex items-center justify-between mb-3">
                          <span className={`px-2.5 py-1 rounded-lg text-xs font-black tracking-wider uppercase ${getSeverityColor(bug.severity)} bg-white/5 border border-white/5`}>
                            {bug.severity}
                          </span>
                          {bug.line && <span className="text-xs font-bold text-muted bg-white/5 px-2 py-1 rounded-md">Line {bug.line}</span>}
                        </div>
                        <p className="text-base text-primary font-medium leading-relaxed">{bug.description}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Security */}
              {review.security?.length > 0 && (
                <div className="glass-card p-8 rounded-[32px]">
                  <h3 className="text-xl font-bold text-primary flex items-center gap-3 mb-6">
                    <div className="w-10 h-10 rounded-xl bg-amber-400/10 flex items-center justify-center border border-amber-400/20">
                      <Shield className="w-5 h-5 text-amber-400" />
                    </div>
                    Security Issues ({review.security.length})
                  </h3>
                  <div className="space-y-4">
                    {review.security.map((sec, i) => (
                      <div key={i} className="bg-white/5 rounded-2xl p-5 border border-white/5">
                        <div className="mb-3">
                          <span className={`px-2.5 py-1 rounded-lg text-xs font-black tracking-wider uppercase ${getSeverityColor(sec.severity)} bg-white/5 border border-white/5`}>
                            {sec.severity}
                          </span>
                        </div>
                        <p className="text-base text-primary font-bold mb-2 leading-relaxed">{sec.issue}</p>
                        <p className="text-sm text-muted font-medium italic">{sec.recommendation}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Suggestions */}
            {review.suggestions?.length > 0 && (
              <div className="glass-card p-8 rounded-[32px]">
                <h3 className="text-xl font-bold text-primary flex items-center gap-3 mb-6">
                  <div className="w-10 h-10 rounded-xl bg-accent/10 flex items-center justify-center border border-accent/20">
                    <Lightbulb className="w-5 h-5 text-accent" />
                  </div>
                  Suggestions ({review.suggestions.length})
                </h3>
                <div className="grid gap-6">
                  {review.suggestions.map((sug, i) => (
                    <div key={i} className="bg-white/5 rounded-2xl p-6 border border-white/5">
                      <span className="inline-block text-xs font-black tracking-wider uppercase bg-accent/10 text-accent px-3 py-1 rounded-lg mb-4 border border-accent/10">
                        {sug.category}
                      </span>
                      <p className="text-lg text-primary font-medium mb-4 leading-relaxed">{sug.description}</p>
                      {sug.improved_snippet && (
                        <div className="relative group/code">
                          <pre className="bg-code-bg/80 rounded-xl p-5 overflow-x-auto text-sm font-mono border border-white/5">
                            {sug.improved_snippet}
                          </pre>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

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
