import { Link, useLocation } from "react-router-dom";
import { SignedIn, SignedOut, UserButton } from "@clerk/clerk-react";
import { motion } from "framer-motion";
import { Activity, Code2, GitPullRequest, Clock, Mail, Menu, X } from "lucide-react";
import { useState } from "react";

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
    <nav className="sticky top-0 z-50 border-b border-border bg-background/80 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/dashboard" className="flex items-center gap-2 no-underline">
            <div className="w-8 h-8 rounded-lg bg-accent flex items-center justify-center">
              <Activity className="w-4 h-4 text-white" />
            </div>
            <span className="text-lg font-bold text-primary">DevPulse</span>
          </Link>

          {/* Desktop Nav */}
          <SignedIn>
            <div className="hidden md:flex items-center gap-1">
              {navLinks.map(({ to, label, icon: Icon }) => {
                const isActive = location.pathname === to;
                return (
                  <Link
                    key={to}
                    to={to}
                    className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors no-underline ${
                      isActive
                        ? "bg-surface-alt text-accent"
                        : "text-muted hover:text-primary hover:bg-surface"
                    }`}
                  >
                    <Icon className="w-4 h-4" />
                    {label}
                  </Link>
                );
              })}
            </div>
            <div className="hidden md:flex items-center gap-4">
              <UserButton
                afterSignOutUrl="/"
                appearance={{
                  elements: { avatarBox: "w-8 h-8" },
                }}
              />
            </div>
          </SignedIn>

          <SignedOut>
            <div className="flex items-center gap-3">
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
            </div>
          </SignedOut>

          {/* Mobile toggle */}
          <SignedIn>
            <button
              className="md:hidden p-2 text-muted hover:text-primary"
              onClick={() => setMobileOpen(!mobileOpen)}
            >
              {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </SignedIn>
        </div>

        {/* Mobile Nav */}
        {mobileOpen && (
          <motion.div
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            className="md:hidden border-t border-border py-4 space-y-1"
          >
            {navLinks.map(({ to, label, icon: Icon }) => {
              const isActive = location.pathname === to;
              return (
                <Link
                  key={to}
                  to={to}
                  onClick={() => setMobileOpen(false)}
                  className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm no-underline ${
                    isActive ? "bg-surface-alt text-accent" : "text-muted hover:text-primary"
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {label}
                </Link>
              );
            })}
            <div className="pt-3 px-3">
              <UserButton afterSignOutUrl="/" />
            </div>
          </motion.div>
        )}
      </div>
    </nav>
  );
}
