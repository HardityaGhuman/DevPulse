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
    <div className="space-y-6">
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-2xl font-bold text-primary flex items-center gap-2">
          <Clock className="w-6 h-6 text-muted" /> Review History
        </h1>
        <p className="text-muted mt-1">All your past code and PR reviews</p>
      </motion.div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="flex gap-2">
          {["all", "code", "pr"].map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
                filter === f ? "bg-accent text-white" : "bg-surface text-muted hover:text-primary border border-border"
              }`}
            >
              {f === "all" ? "All" : f === "code" ? "Code" : "PR"}
            </button>
          ))}
        </div>
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search reviews..."
            className="w-full bg-surface border border-border rounded-lg pl-9 pr-3 py-1.5 text-sm text-primary focus:border-accent outline-none placeholder:text-muted/50"
          />
        </div>
      </div>

      {/* List */}
      {loading ? (
        <div className="space-y-2">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="card p-4 h-16 animate-pulse" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="card p-12 text-center">
          <Clock className="w-10 h-10 text-muted mx-auto mb-3" />
          <p className="text-muted">{reviews.length === 0 ? "No reviews yet" : "No matching reviews"}</p>
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map((review, i) => (
            <motion.div
              key={review.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.03 }}
            >
              <Link
                to={`/review/${review.id}`}
                className="card p-4 flex items-center justify-between group no-underline block"
              >
                <div className="flex items-center gap-3">
                  {review.type === "code" ? (
                    <Code2 className="w-4 h-4 text-accent" />
                  ) : (
                    <GitPullRequest className="w-4 h-4 text-success" />
                  )}
                  <div>
                    <p className="text-sm text-primary font-medium">
                      {review.type === "pr" ? review.repo_name || "PR Review" : `${review.language || "Code"} Review`}
                    </p>
                    <p className="text-xs text-muted">{formatRelativeTime(review.created_at)}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  {review.score != null && (
                    <span className={`text-sm font-bold ${getScoreColor(review.score)}`}>{review.score}/10</span>
                  )}
                  <ArrowRight className="w-4 h-4 text-muted group-hover:text-accent transition-colors" />
                </div>
              </Link>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
