import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { ClerkProvider } from "@clerk/clerk-react";
import { dark } from "@clerk/themes";
import App from "./App.jsx";
import "./index.css";

const CLERK_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter>
      <ClerkProvider
        publishableKey={CLERK_KEY}
        appearance={{
          baseTheme: dark,
          variables: {
            colorPrimary: "#3b82f6",
            colorBackground: "#111111",
            colorInputBackground: "#1a1a1a",
            colorText: "#f1f5f9",
            borderRadius: "8px",
          },
        }}
      >
        <App />
      </ClerkProvider>
    </BrowserRouter>
  </React.StrictMode>
);
