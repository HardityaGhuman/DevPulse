import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { ClerkProvider } from "@clerk/clerk-react";
import { dark } from "@clerk/themes";
import App from "./App.jsx";
import "./index.css";
import { ThemeProvider, useTheme } from "./context/ThemeContext";

const CLERK_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;

function ClerkWithTheme({ children }) {
  const { theme } = useTheme();
  
  return (
    <ClerkProvider
      publishableKey={CLERK_KEY}
      appearance={{
        baseTheme: theme === "dark" ? dark : undefined,
        variables: {
          colorPrimary: "#3b82f6",
          colorBackground: theme === "dark" ? "#111111" : "#ffffff",
          colorInputBackground: theme === "dark" ? "#1a1a1a" : "#f8fafc",
          colorText: theme === "dark" ? "#f1f5f9" : "#0f172a",
          borderRadius: "12px",
        },
      }}
    >
      {children}
    </ClerkProvider>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter>
      <ThemeProvider>
        <ClerkWithTheme>
          <App />
        </ClerkWithTheme>
      </ThemeProvider>
    </BrowserRouter>
  </React.StrictMode>
);
