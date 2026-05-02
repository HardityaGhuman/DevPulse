import { Sun, Moon } from "lucide-react";
import { useTheme } from "@/context/ThemeContext";
import { motion } from "framer-motion";

export default function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();

  return (
    <button
      onClick={toggleTheme}
      className="relative w-14 h-8 rounded-full bg-white/5 border border-white/10 flex items-center px-1 group hover:border-accent transition-colors"
      aria-label="Toggle theme"
    >
      <motion.div
        animate={{ x: theme === "dark" ? 24 : 0 }}
        transition={{ type: "spring", stiffness: 300, damping: 25 }}
        className="w-6 h-6 rounded-full bg-accent flex items-center justify-center shadow-lg shadow-accent/20"
      >
        {theme === "dark" ? (
          <Moon className="w-3.5 h-3.5 text-white" />
        ) : (
          <Sun className="w-3.5 h-3.5 text-white" />
        )}
      </motion.div>
    </button>
  );
}
