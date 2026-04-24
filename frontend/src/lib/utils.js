import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Merge Tailwind classes with clsx for conditional class names.
 */
export function cn(...inputs) {
  return twMerge(clsx(inputs));
}

/**
 * Format a date string to a human-readable format.
 */
export function formatDate(dateString) {
  return new Date(dateString).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

/**
 * Format a date string to a relative time (e.g., "2 hours ago").
 */
export function formatRelativeTime(dateString) {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return "just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return formatDate(dateString);
}

/**
 * Get a color class based on score value (1-10).
 */
export function getScoreColor(score) {
  if (score >= 8) return "text-success";
  if (score >= 5) return "text-amber-400";
  return "text-destructive";
}

/**
 * Get a color class based on severity level.
 */
export function getSeverityColor(severity) {
  switch (severity) {
    case "critical":
      return "text-destructive";
    case "high":
      return "text-orange-400";
    case "medium":
      return "text-amber-400";
    case "low":
      return "text-muted";
    default:
      return "text-muted";
  }
}

/**
 * Truncate a string to a maximum length.
 */
export function truncate(str, maxLength = 100) {
  if (!str || str.length <= maxLength) return str;
  return str.slice(0, maxLength) + "...";
}
