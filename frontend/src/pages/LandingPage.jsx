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
    <div className="min-h-screen bg-background">
      {/* Navbar */}
      <nav className="border-b border-border bg-background/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between h-16">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-accent flex items-center justify-center">
              <Activity className="w-4 h-4 text-white" />
            </div>
            <span className="text-lg font-bold text-primary">DevPulse</span>
          </div>
          <div className="flex items-center gap-3">
            <SignedOut>
              <Link
                to="/sign-in"
                className="text-sm text-muted hover:text-primary transition-colors no-underline"
              >
                Sign In
              </Link>
              <Link
                to="/sign-up"
                className="text-sm bg-accent text-white px-4 py-2 rounded-lg hover:bg-accent/90 transition-colors no-underline"
              >
                Get Started
              </Link>
            </SignedOut>
            <SignedIn>
              <Link
                to="/dashboard"
                className="text-sm bg-accent text-white px-4 py-2 rounded-lg hover:bg-accent/90 transition-colors no-underline flex items-center gap-2"
              >
                Dashboard <ArrowRight className="w-4 h-4" />
              </Link>
            </SignedIn>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative overflow-hidden pt-24 pb-32 px-4">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_rgba(59,130,246,0.08)_0%,_transparent_60%)]" />
        <div className="max-w-4xl mx-auto text-center relative z-10">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-border text-muted text-xs mb-8">
              <Zap className="w-3 h-3 text-accent" />
              Powered by Google Gemini
            </div>
            <h1 className="text-5xl sm:text-6xl lg:text-7xl font-bold tracking-tight mb-6">
              <span className="gradient-text">AI-powered</span>
              <br />
              <span className="text-primary">developer intelligence</span>
            </h1>
            <p className="text-lg sm:text-xl text-muted max-w-2xl mx-auto mb-10 leading-relaxed">
              Get instant code reviews, PR analysis, and personalized activity
              digests. Ship better code with an AI copilot that actually
              understands your workflow.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <SignedOut>
                <Link
                  to="/sign-up"
                  className="inline-flex items-center gap-2 bg-accent text-white px-8 py-3 rounded-lg text-base font-medium hover:bg-accent/90 transition-colors no-underline"
                >
                  Start reviewing for free
                  <ArrowRight className="w-4 h-4" />
                </Link>
              </SignedOut>
              <SignedIn>
                <Link
                  to="/dashboard"
                  className="inline-flex items-center gap-2 bg-accent text-white px-8 py-3 rounded-lg text-base font-medium hover:bg-accent/90 transition-colors no-underline"
                >
                  Go to Dashboard
                  <ArrowRight className="w-4 h-4" />
                </Link>
              </SignedIn>
              <Link
                to="/sign-in"
                className="inline-flex items-center gap-2 text-muted hover:text-primary px-8 py-3 rounded-lg text-base border border-border hover:border-accent transition-colors no-underline"
              >
                View demo
              </Link>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Features */}
      <section className="py-24 px-4 border-t border-border">
        <div className="max-w-6xl mx-auto">
          <motion.div
            className="text-center mb-16"
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
          >
            <h2 className="text-3xl sm:text-4xl font-bold text-primary mb-4">
              Everything you need to ship better code
            </h2>
            <p className="text-muted text-lg max-w-2xl mx-auto">
              A complete developer intelligence toolkit — from instant reviews to
              automated coaching.
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((feature, i) => (
              <motion.div
                key={feature.title}
                className="card p-6"
                variants={fadeUp}
                initial="initial"
                whileInView="animate"
                viewport={{ once: true }}
                transition={{ delay: i * 0.1, duration: 0.4 }}
              >
                <div className="w-10 h-10 rounded-lg bg-accent/10 flex items-center justify-center mb-4">
                  <feature.icon className="w-5 h-5 text-accent" />
                </div>
                <h3 className="text-lg font-semibold text-primary mb-2">
                  {feature.title}
                </h3>
                <p className="text-sm text-muted leading-relaxed">
                  {feature.description}
                </p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-24 px-4 border-t border-border">
        <motion.div
          className="max-w-3xl mx-auto text-center"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
        >
          <h2 className="text-3xl sm:text-4xl font-bold text-primary mb-4">
            Ready to level up your code?
          </h2>
          <p className="text-muted text-lg mb-8">
            Join developers who use AI to write better, more secure code every day.
          </p>
          <SignedOut>
            <Link
              to="/sign-up"
              className="inline-flex items-center gap-2 bg-accent text-white px-8 py-3 rounded-lg text-base font-medium hover:bg-accent/90 transition-colors no-underline"
            >
              Get started — it's free
              <ArrowRight className="w-4 h-4" />
            </Link>
          </SignedOut>
        </motion.div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border py-8 px-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded bg-accent flex items-center justify-center">
              <Activity className="w-3 h-3 text-white" />
            </div>
            <span className="text-sm text-muted">DevPulse</span>
          </div>
          <p className="text-xs text-muted">
            Powered by Google Gemini · Built with ♥
          </p>
        </div>
      </footer>
    </div>
  );
}
