import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Code2, GitPullRequest, BarChart3, Clock, ArrowRight, TrendingUp } from "lucide-react";
import api from "@/lib/api";
import { formatRelativeTime, getScoreColor } from "@/lib/utils";

const fadeUp = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
};

export default function Dashboard() {
  const [reviews, setReviews] = useState([]);
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [reviewsRes, userRes] = await Promise.all([
          api.get("/api/review/history"),
          api.get("/api/users/me"),
        ]);
        setReviews(reviewsRes.data.reviews || []);
        setUser(userRes.data);
      } catch (e) {
        console.error("Failed to load dashboard:", e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const codeReviews = reviews.filter((r) => r.type === "code");
  const prReviews = reviews.filter((r) => r.type === "pr");
  const avgScore =
    reviews.length > 0
      ? Math.round(reviews.reduce((sum, r) => sum + (r.score || 0), 0) / reviews.length)
      : 0;

  const stats = [
    { label: "Code Reviews", value: codeReviews.length, icon: Code2, color: "text-accent" },
    { label: "PR Reviews", value: prReviews.length, icon: GitPullRequest, color: "text-success" },
    { label: "Avg Score", value: `${avgScore}/10`, icon: BarChart3, color: "text-amber-400" },
    { label: "Total Reviews", value: reviews.length, icon: TrendingUp, color: "text-accent" },
  ];

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="h-8 w-48 bg-surface rounded animate-pulse" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="card p-6 h-28 animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <motion.div {...fadeUp} transition={{ duration: 0.4 }}>
        <h1 className="text-2xl font-bold text-primary">
          Welcome back{user?.github_username ? `, ${user.github_username}` : ""}
        </h1>
        <p className="text-muted mt-1">Here's your development overview</p>
      </motion.div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat, i) => (
          <motion.div
            key={stat.label}
            className="card p-6"
            variants={fadeUp}
            initial="initial"
            animate="animate"
            transition={{ delay: i * 0.1, duration: 0.4 }}
          >
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm text-muted">{stat.label}</span>
              <stat.icon className={`w-4 h-4 ${stat.color}`} />
            </div>
            <p className="text-3xl font-bold text-primary">{stat.value}</p>
          </motion.div>
        ))}
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Link to="/review/code" className="card p-6 group cursor-pointer no-underline block">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-primary flex items-center gap-2">
                <Code2 className="w-5 h-5 text-accent" />
                New Code Review
              </h3>
              <p className="text-sm text-muted mt-1">
                Paste code and get instant AI-powered feedback
              </p>
            </div>
            <ArrowRight className="w-5 h-5 text-muted group-hover:text-accent transition-colors" />
          </div>
        </Link>
        <Link to="/review/pr" className="card p-6 group cursor-pointer no-underline block">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-primary flex items-center gap-2">
                <GitPullRequest className="w-5 h-5 text-success" />
                New PR Review
              </h3>
              <p className="text-sm text-muted mt-1">
                Analyze a GitHub pull request with AI
              </p>
            </div>
            <ArrowRight className="w-5 h-5 text-muted group-hover:text-accent transition-colors" />
          </div>
        </Link>
      </div>

      {/* Recent Reviews */}
      <motion.div variants={fadeUp} initial="initial" animate="animate" transition={{ delay: 0.3 }}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-primary flex items-center gap-2">
            <Clock className="w-5 h-5 text-muted" />
            Recent Reviews
          </h2>
          {reviews.length > 0 && (
            <Link to="/history" className="text-sm text-accent hover:underline no-underline">
              View all
            </Link>
          )}
        </div>

        {reviews.length === 0 ? (
          <div className="card p-12 text-center">
            <Code2 className="w-10 h-10 text-muted mx-auto mb-3" />
            <p className="text-muted">No reviews yet. Start your first code review!</p>
          </div>
        ) : (
          <div className="space-y-2">
            {reviews.slice(0, 5).map((review) => (
              <Link
                key={review.id}
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
                      {review.type === "pr"
                        ? review.repo_name || "PR Review"
                        : `${review.language || "Code"} Review`}
                    </p>
                    <p className="text-xs text-muted">{formatRelativeTime(review.created_at)}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  {review.score && (
                    <span className={`text-sm font-bold ${getScoreColor(review.score)}`}>
                      {review.score}/10
                    </span>
                  )}
                  <ArrowRight className="w-4 h-4 text-muted group-hover:text-accent transition-colors" />
                </div>
              </Link>
            ))}
          </div>
        )}
      </motion.div>
    </div>
  );
}
