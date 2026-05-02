import { Link, useLocation } from "react-router-dom";
import { SignedIn, SignedOut, UserButton } from "@clerk/clerk-react";
import { motion, AnimatePresence } from "framer-motion";
import { Activity, Code2, GitPullRequest, Clock, Mail, Menu, X } from "lucide-react";
import { useState } from "react";

import ThemeToggle from "@/components/common/ThemeToggle";

const navLinks = [
  { to: "/dashboard", label: "Dashboard", icon: Activity },
  { to: "/review/code", label: "Code Review", icon: Code2 },
  { to: "/review/pr", label: "PR Review", icon: GitPullRequest },
  { to: "/history", label: "History", icon: Clock },
  { to: "/digest", label: "Digests", icon: Mail },
];

export default function Navbar() {
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <nav className="sticky top-0 z-50 bg-background/60 backdrop-blur-xl border-b border-white/5">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-20">
          {/* Logo */}
          <Link to="/dashboard" className="flex items-center gap-3 no-underline group">
            <div className="w-10 h-10 rounded-xl bg-accent flex items-center justify-center shadow-lg shadow-accent/20 group-hover:scale-110 transition-transform">
              <Activity className="w-5 h-5 text-white" />
            </div>
            <span className="text-2xl font-black text-primary tracking-tighter">DevPulse</span>
          </Link>

          {/* Desktop Nav */}
          <SignedIn>
            <div className="hidden md:flex items-center gap-2 px-2 py-1.5 bg-white/5 rounded-2xl border border-white/5">
              {navLinks.map(({ to, label, icon: Icon }) => {
                const isActive = location.pathname === to;
                return (
                  <Link
                    key={to}
                    to={to}
                    className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-bold transition-all no-underline ${
                      isActive
                        ? "bg-white/10 text-primary shadow-sm"
                        : "text-muted hover:text-primary hover:bg-white/5"
                    }`}
                  >
                    <Icon className="w-4 h-4" />
                    {label}
                  </Link>
                );
              })}
            </div>
            <div className="hidden md:flex items-center gap-6 ml-6">
              <ThemeToggle />
              <div className="h-6 w-px bg-white/10" />
              <UserButton
                afterSignOutUrl="/"
                appearance={{
                  elements: { 
                    avatarBox: "w-9 h-9 rounded-xl ring-2 ring-white/5 ring-offset-2 ring-offset-background",
                    userButtonTrigger: "focus:shadow-none focus:ring-0"
                  },
                }}
              />
            </div>
          </SignedIn>

          <SignedOut>
            <div className="flex items-center gap-6">
              <ThemeToggle />
              <Link
                to="/sign-in"
                className="text-sm font-bold text-muted hover:text-primary transition-colors no-underline"
              >
                Sign In
              </Link>
              <Link
                to="/sign-up"
                className="text-sm font-bold bg-accent text-white px-6 py-2.5 rounded-xl hover:scale-105 transition-all no-underline shadow-lg shadow-accent/20"
              >
                Get Started
              </Link>
            </div>
          </SignedOut>

          {/* Mobile toggle */}
          <SignedIn>
            <button
              className="md:hidden w-10 h-10 flex items-center justify-center rounded-xl bg-white/5 text-muted hover:text-primary transition-colors"
              onClick={() => setMobileOpen(!mobileOpen)}
            >
              {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </SignedIn>
        </div>

        {/* Mobile Nav */}
        <AnimatePresence>
          {mobileOpen && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="md:hidden overflow-hidden border-t border-white/5 py-6 space-y-2"
            >
              {navLinks.map(({ to, label, icon: Icon }) => {
                const isActive = location.pathname === to;
                return (
                  <Link
                    key={to}
                    to={to}
                    onClick={() => setMobileOpen(false)}
                    className={`flex items-center gap-4 px-4 py-3 rounded-xl text-base font-bold no-underline transition-all ${
                      isActive ? "bg-white/10 text-primary" : "text-muted hover:text-primary hover:bg-white/5"
                    }`}
                  >
                    <Icon className="w-5 h-5" />
                    {label}
                  </Link>
                );
              })}
              <div className="pt-4 px-4 flex items-center justify-between border-t border-white/5 mt-4">
                <span className="text-sm font-bold text-muted uppercase tracking-widest flex items-center gap-2">
                  Appearance
                  <ThemeToggle />
                </span>
                <UserButton afterSignOutUrl="/" />
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </nav>
  );
}
