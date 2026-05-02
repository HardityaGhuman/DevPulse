import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Clock, Code2, GitPullRequest, ArrowRight, Search } from "lucide-react";
import api from "@/lib/api";
import { formatRelativeTime, getScoreColor } from "@/lib/utils";

export default function ReviewHistory() {
  const [reviews, setReviews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");
  const [search, setSearch] = useState("");

  useEffect(() => {
    api.get("/api/review/history")
      .then((res) => setReviews(res.data.reviews || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const filtered = reviews.filter((r) => {
    if (filter !== "all" && r.type !== filter) return false;
    if (search) {
      const q = search.toLowerCase();
      return (
        (r.language || "").toLowerCase().includes(q) ||
        (r.repo_name || "").toLowerCase().includes(q)
      );
    }
    return true;
  });

  return (
    <div className="space-y-8 max-w-5xl mx-auto pb-20">
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-4xl font-black text-primary flex items-center gap-3">
          <div className="w-12 h-12 rounded-2xl bg-white/5 flex items-center justify-center border border-white/10">
            <Clock className="w-7 h-7 text-muted" />
          </div>
          Review History
        </h1>
        <p className="text-muted text-lg mt-3 font-medium">All your past code and PR reviews</p>
      </motion.div>

      {/* Filters */}
      <div className="flex flex-col md:flex-row gap-4 items-center">
        <div className="flex gap-2 p-1.5 bg-white/5 rounded-2xl border border-white/5">
          {["all", "code", "pr"].map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-6 py-2 rounded-xl text-sm font-bold transition-all uppercase tracking-wider ${
                filter === f ? "bg-accent text-white shadow-lg shadow-accent/20" : "text-muted hover:text-primary"
              }`}
            >
              {f === "all" ? "All" : f === "code" ? "Code" : "PR"}
            </button>
          ))}
        </div>
        <div className="relative flex-1 w-full md:max-w-sm">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-muted" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search reviews by language or repo..."
            className="w-full bg-white/5 border border-white/10 rounded-2xl pl-12 pr-4 py-3 text-base text-primary focus:border-accent outline-none placeholder:text-muted/30 backdrop-blur-sm"
          />
        </div>
      </div>

      {/* List */}
      {loading ? (
        <div className="space-y-4">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="glass-card p-5 h-20 rounded-2xl animate-pulse" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="glass-card p-24 text-center rounded-[40px] border-dashed border-2">
          <div className="w-20 h-20 bg-white/5 rounded-3xl flex items-center justify-center mx-auto mb-6">
            <Clock className="w-10 h-10 text-muted" />
          </div>
          <p className="text-xl text-muted font-medium">
            {reviews.length === 0 ? "No reviews yet. Start your first one!" : "No matching reviews found."}
          </p>
        </div>
      ) : (
        <div className="grid gap-4">
          {filtered.map((review, i) => (
            <motion.div
              key={review.id}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.04 }}
            >
              <Link
                to={`/review/${review.id}`}
                className="glass-card p-5 flex items-center justify-between group no-underline block rounded-2xl card-hover-effect"
              >
                <div className="flex items-center gap-5">
                  <div className={`w-12 h-12 rounded-xl flex items-center justify-center border border-white/5 ${
                    review.type === "code" ? "bg-accent/10" : "bg-success/10"
                  }`}>
                    {review.type === "code" ? (
                      <Code2 className="w-5 h-5 text-accent" />
                    ) : (
                      <GitPullRequest className="w-5 h-5 text-success" />
                    )}
                  </div>
                  <div>
                    <p className="text-lg text-primary font-bold">
                      {review.type === "pr" ? review.repo_name || "PR Review" : `${review.language || "Code"} Review`}
                    </p>
                    <p className="text-sm text-muted font-medium">{formatRelativeTime(review.created_at)}</p>
                  </div>
                </div>
                <div className="flex items-center gap-6">
                  {review.score != null && (
                    <div className="text-right px-4 py-1.5 rounded-xl bg-white/5 border border-white/5">
                      <span className={`text-lg font-black ${getScoreColor(review.score)}`}>{review.score}</span>
                      <span className="text-xs text-muted font-bold ml-1">/10</span>
                    </div>
                  )}
                  <div className="w-10 h-10 rounded-xl bg-white/5 flex items-center justify-center group-hover:bg-white/10 transition-colors">
                    <ArrowRight className="w-5 h-5 text-muted group-hover:text-primary transition-all" />
                  </div>
                </div>
              </Link>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
