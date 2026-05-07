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
    { label: "Code Reviews", value: codeReviews.length, icon: Code2, color: "text-accent", bg: "bg-accent/10" },
    { label: "PR Reviews", value: prReviews.length, icon: GitPullRequest, color: "text-success", bg: "bg-success/10" },
    { label: "Avg Score", value: `${avgScore}/10`, icon: BarChart3, color: "text-amber-400", bg: "bg-amber-400/10" },
    { label: "Total Reviews", value: reviews.length, icon: TrendingUp, color: "text-purple-400", bg: "bg-purple-400/10" },
  ];

  if (loading) {
    return (
      <div className="space-y-8 max-w-6xl mx-auto">
        <div className="space-y-2">
          <div className="h-10 w-64 bg-surface-raised rounded-xl animate-pulse" />
          <div className="h-5 w-48 bg-surface-raised rounded-lg animate-pulse" />
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="glass-card p-6 h-32 rounded-3xl animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-12 max-w-6xl mx-auto pb-12">
      {/* Header */}
      <motion.div {...fadeUp} transition={{ duration: 0.6 }}>
        <h1 className="text-4xl font-black tracking-tight text-primary">
          Welcome back{user?.github_username ? `, ${user.github_username}` : ""}
        </h1>
        <p className="text-muted text-lg mt-2 font-medium">Here's your development overview</p>
      </motion.div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat, i) => (
          <motion.div
            key={stat.label}
            className="glass-card p-6 rounded-3xl card-hover-effect relative overflow-hidden group"
            variants={fadeUp}
            initial="initial"
            animate="animate"
            transition={{ delay: i * 0.1, duration: 0.5 }}
          >
            <div className={`absolute -right-4 -bottom-4 w-24 h-24 ${stat.bg} rounded-full blur-3xl opacity-0 group-hover:opacity-100 transition-opacity`} />
            <div className="flex items-center justify-between mb-4">
              <div className={`w-10 h-10 rounded-xl ${stat.bg} flex items-center justify-center border border-border/50`}>
                <stat.icon className={`w-5 h-5 ${stat.color}`} />
              </div>
              <span className="text-sm font-bold text-muted tracking-wider uppercase">{stat.label}</span>
            </div>
            <p className="text-4xl font-black text-primary tracking-tight">{stat.value}</p>
          </motion.div>
        ))}
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Link to="/review/code" className="glass-card p-8 group cursor-pointer no-underline block rounded-[32px] card-hover-effect relative overflow-hidden">
          <div className="absolute top-0 right-0 p-8 opacity-5 group-hover:opacity-10 transition-opacity">
            <Code2 className="w-32 h-32 text-accent" />
          </div>
          <div className="flex items-center justify-between relative z-10">
            <div>
              <h3 className="text-2xl font-bold text-primary flex items-center gap-3">
                <Code2 className="w-6 h-6 text-accent" />
                New Code Review
              </h3>
              <p className="text-muted mt-2 text-lg font-medium max-w-[280px]">
                Paste code and get instant AI-powered feedback
              </p>
            </div>
            <div className="w-12 h-12 rounded-2xl bg-primary/[0.03] border border-border/50 flex items-center justify-center group-hover:bg-accent transition-colors">
              <ArrowRight className="w-6 h-6 text-primary group-hover:translate-x-1 transition-transform" />
            </div>
          </div>
        </Link>
        
        <Link to="/review/pr" className="glass-card p-8 group cursor-pointer no-underline block rounded-[32px] card-hover-effect relative overflow-hidden">
          <div className="absolute top-0 right-0 p-8 opacity-5 group-hover:opacity-10 transition-opacity">
            <GitPullRequest className="w-32 h-32 text-success" />
          </div>
          <div className="flex items-center justify-between relative z-10">
            <div>
              <h3 className="text-2xl font-bold text-primary flex items-center gap-3">
                <GitPullRequest className="w-6 h-6 text-success" />
                New PR Review
              </h3>
              <p className="text-muted mt-2 text-lg font-medium max-w-[280px]">
                Analyze a GitHub pull request with AI
              </p>
            </div>
            <div className="w-12 h-12 rounded-2xl bg-primary/[0.03] border border-border/50 flex items-center justify-center group-hover:bg-success transition-colors">
              <ArrowRight className="w-6 h-6 text-primary group-hover:translate-x-1 transition-transform" />
            </div>
          </div>
        </Link>
      </div>

      {/* Recent Reviews */}
      <motion.div 
        variants={fadeUp} 
        initial="initial" 
        animate="animate" 
        transition={{ delay: 0.4 }}
        className="space-y-6"
      >
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold text-primary flex items-center gap-3">
            <Clock className="w-6 h-6 text-muted" />
            Recent Reviews
          </h2>
          {reviews.length > 0 && (
            <Link to="/history" className="text-sm font-bold text-accent hover:text-accent/80 transition-colors no-underline px-4 py-2 rounded-xl bg-accent/5 border border-accent/10">
              View all
            </Link>
          )}
        </div>

        {reviews.length === 0 ? (
          <div className="glass-card p-20 text-center rounded-[32px] border-dashed border-2">
            <div className="w-20 h-20 bg-primary/[0.03] rounded-3xl flex items-center justify-center mx-auto mb-6">
              <Code2 className="w-10 h-10 text-muted" />
            </div>
            <p className="text-muted text-xl font-medium">No reviews yet. Start your first code review!</p>
          </div>
        ) : (
          <div className="grid gap-4">
            {reviews.slice(0, 5).map((review, i) => (
              <motion.div
                key={review.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.5 + i * 0.05 }}
              >
                <Link
                  to={`/review/${review.id}`}
                  className="glass-card p-5 flex items-center justify-between group no-underline block rounded-2xl card-hover-effect"
                >
                  <div className="flex items-center gap-5">
                    <div className={`w-12 h-12 rounded-xl flex items-center justify-center border border-border/50 ${
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
                        {review.type === "pr"
                          ? review.repo_name || "PR Review"
                          : `${review.language || "Code"} Review`}
                      </p>
                      <p className="text-sm text-muted font-medium">{formatRelativeTime(review.created_at)}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-6">
                    {review.score && (
                      <div className="text-right px-4 py-1.5 rounded-xl bg-primary/[0.03] border border-border/50">
                        <span className={`text-lg font-black ${getScoreColor(review.score)}`}>
                          {review.score}
                        </span>
                        <span className="text-xs text-muted font-bold ml-1">/10</span>
                      </div>
                    )}
                    <div className="w-10 h-10 rounded-xl bg-primary/[0.03] border border-border/50 flex items-center justify-center group-hover:bg-primary/[0.08] transition-colors">
                      <ArrowRight className="w-5 h-5 text-muted group-hover:text-primary transition-all" />
                    </div>
                  </div>
                </Link>
              </motion.div>
            ))}
          </div>
        )}
      </motion.div>
    </div>
  );
}
