import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { SignedIn, SignedOut } from "@clerk/clerk-react";
import {
  Code2,
  GitPullRequest,
  Mail,
  Zap,
  Shield,
  BarChart3,
  ArrowRight,
  Activity,
} from "lucide-react";

const fadeUp = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
};

const features = [
  {
    icon: Code2,
    title: "AI Code Review",
    description:
      "Paste any code snippet and get instant, structured feedback — bugs, security issues, and improvement suggestions.",
  },
  {
    icon: GitPullRequest,
    title: "PR Analysis",
    description:
      "Drop a GitHub PR URL and get a full review with file-level verdicts, risk assessment, and merge recommendations.",
  },
  {
    icon: Mail,
    title: "Smart Digests",
    description:
      "Automated daily or weekly email digests that summarize your GitHub activity with personalized coaching tips.",
  },
  {
    icon: Shield,
    title: "Security Scanning",
    description:
      "Every review includes dedicated security analysis with severity ratings and actionable remediation steps.",
  },
  {
    icon: BarChart3,
    title: "Momentum Tracking",
    description:
      "Track your development momentum over time — rising, steady, or declining — with AI-driven insights.",
  },
  {
    icon: Zap,
    title: "Instant Results",
    description:
      "Powered by Gemini 2.5 Flash for lightning-fast reviews. Get comprehensive feedback in seconds, not minutes.",
  },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background relative overflow-hidden">
      {/* Background Decor */}
      <div className="absolute top-0 left-1/4 w-96 h-96 bg-accent/20 rounded-full blur-[128px] -z-10 animate-pulse" />
      <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-accent-alt/10 rounded-full blur-[128px] -z-10" />

      {/* Navbar */}
      <nav className="glass border-b border-border sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between h-16">
          <div className="flex items-center gap-2">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-accent to-accent-alt flex items-center justify-center shadow-lg shadow-accent/20">
              <Activity className="w-5 h-5 text-white" />
            </div>
            <span className="text-xl font-bold tracking-tight text-primary">DevPulse</span>
          </div>
          <div className="flex items-center gap-4">
            <SignedOut>
              <Link
                to="/sign-in"
                className="text-sm font-medium text-muted hover:text-primary transition-colors no-underline"
              >
                Sign In
              </Link>
              <Link
                to="/sign-up"
                className="text-sm font-semibold bg-primary text-background px-5 py-2.5 rounded-lg hover:opacity-90 transition-all no-underline shadow-lg shadow-white/5"
              >
                Get Started
              </Link>
            </SignedOut>
            <SignedIn>
              <Link
                to="/dashboard"
                className="text-sm font-semibold bg-accent text-white px-5 py-2.5 rounded-lg hover:bg-accent/90 transition-all no-underline flex items-center gap-2 shadow-lg shadow-accent/20"
              >
                Dashboard <ArrowRight className="w-4 h-4" />
              </Link>
            </SignedIn>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative pt-32 pb-40 px-4">
        <div className="max-w-5xl mx-auto text-center relative z-10">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, ease: "easeOut" }}
          >
            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-border bg-white/5 text-muted text-xs font-medium mb-10 backdrop-blur-sm animate-float">
              <Zap className="w-3.5 h-3.5 text-accent fill-accent" />
              <span className="bg-gradient-to-r from-accent to-accent-alt bg-clip-text text-transparent">
                Powered by Google Gemini 2.5 Flash
              </span>
            </div>
            <h1 className="text-6xl sm:text-7xl lg:text-8xl font-black tracking-tight mb-8 leading-[1.1]">
              <span className="gradient-text">AI-powered</span>
              <br />
              <span className="text-primary">developer intelligence</span>
            </h1>
            <p className="text-xl sm:text-2xl text-muted max-w-3xl mx-auto mb-12 leading-relaxed font-medium">
              Get instant code reviews, PR analysis, and personalized activity
              digests. Ship better code with an AI copilot that actually
              understands your workflow.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-6">
              <SignedOut>
                <Link
                  to="/sign-up"
                  className="group inline-flex items-center gap-2 bg-primary text-background px-10 py-4 rounded-xl text-lg font-bold hover:scale-105 transition-all no-underline shadow-xl shadow-white/5"
                >
                  Start reviewing for free
                  <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                </Link>
              </SignedOut>
              <SignedIn>
                <Link
                  to="/dashboard"
                  className="group inline-flex items-center gap-2 bg-accent text-white px-10 py-4 rounded-xl text-lg font-bold hover:scale-105 transition-all no-underline shadow-xl shadow-accent/20"
                >
                  Go to Dashboard
                  <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                </Link>
              </SignedIn>
              <Link
                to="/sign-in"
                className="inline-flex items-center gap-2 text-primary hover:bg-white/5 px-10 py-4 rounded-xl text-lg font-semibold border border-white/10 transition-all no-underline backdrop-blur-sm"
              >
                View demo
              </Link>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Features */}
      <section className="py-32 px-4 relative">
        <div className="absolute inset-0 bg-white/[0.02] -skew-y-3 transform origin-top-left -z-10" />
        <div className="max-w-7xl mx-auto">
          <motion.div
            className="text-center mb-24"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
          >
            <h2 className="text-4xl sm:text-5xl font-bold text-primary mb-6">
              Everything you need to ship better code
            </h2>
            <p className="text-muted text-xl max-w-3xl mx-auto font-medium">
              A complete developer intelligence toolkit — from instant reviews to
              automated coaching.
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {features.map((feature, i) => (
              <motion.div
                key={feature.title}
                className="glass-card p-8 rounded-3xl card-hover-effect"
                variants={fadeUp}
                initial="initial"
                whileInView="animate"
                viewport={{ once: true }}
                transition={{ delay: i * 0.1, duration: 0.5 }}
              >
                <div className="w-14 h-14 rounded-2xl bg-accent/10 flex items-center justify-center mb-6 border border-accent/20">
                  <feature.icon className="w-7 h-7 text-accent" />
                </div>
                <h3 className="text-2xl font-bold text-primary mb-4">
                  {feature.title}
                </h3>
                <p className="text-muted text-lg leading-relaxed">
                  {feature.description}
                </p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-40 px-4">
        <div className="max-w-5xl mx-auto">
          <motion.div
            className="glass-card p-16 rounded-[40px] text-center relative overflow-hidden"
            initial={{ opacity: 0, scale: 0.95 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
          >
            <div className="absolute top-0 right-0 w-64 h-64 bg-accent/10 rounded-full blur-[100px] -z-10" />
            <div className="absolute bottom-0 left-0 w-64 h-64 bg-accent-alt/10 rounded-full blur-[100px] -z-10" />
            
            <h2 className="text-4xl sm:text-6xl font-bold text-primary mb-8 leading-tight">
              Ready to level up <br /> your code?
            </h2>
            <p className="text-muted text-xl mb-12 max-w-2xl mx-auto font-medium">
              Join thousands of developers who use AI to write better, more secure code every day.
            </p>
            <SignedOut>
              <Link
                to="/sign-up"
                className="group inline-flex items-center gap-3 bg-primary text-background px-12 py-5 rounded-2xl text-xl font-bold hover:scale-105 transition-all no-underline shadow-2xl shadow-white/10"
              >
                Get started — it's free
                <ArrowRight className="w-6 h-6 group-hover:translate-x-1 transition-transform" />
              </Link>
            </SignedOut>
            <SignedIn>
              <Link
                to="/dashboard"
                className="group inline-flex items-center gap-3 bg-accent text-white px-12 py-5 rounded-2xl text-xl font-bold hover:scale-105 transition-all no-underline shadow-2xl shadow-accent/20"
              >
                Go to Dashboard
                <ArrowRight className="w-6 h-6 group-hover:translate-x-1 transition-transform" />
              </Link>
            </SignedIn>
          </motion.div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border py-12 px-4 bg-background">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-8">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-accent to-accent-alt flex items-center justify-center shadow-lg shadow-accent/10">
              <Activity className="w-5 h-5 text-white" />
            </div>
            <span className="text-xl font-bold text-primary tracking-tight">DevPulse</span>
          </div>
          <div className="flex items-center gap-8 text-muted font-medium">
            <a href="#" className="hover:text-primary transition-colors no-underline">Terms</a>
            <a href="#" className="hover:text-primary transition-colors no-underline">Privacy</a>
            <a href="#" className="hover:text-primary transition-colors no-underline">Twitter</a>
          </div>
          <p className="text-sm text-muted font-medium">
            © 2026 DevPulse · AI-driven intelligence
          </p>
        </div>
      </footer>
    </div>
  );
}
