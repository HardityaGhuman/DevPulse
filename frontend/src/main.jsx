import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { ClerkProvider } from "@clerk/clerk-react";
import App from "./App.jsx";
import "./index.css";

const CLERK_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter>
      <ClerkProvider
        publishableKey={CLERK_KEY}
        appearance={{
          variables: {
            colorPrimary: "#5b5bd6",
            colorText: "#1a1a1a",
            colorBackground: "#ffffff",
            borderRadius: "10px",
            fontFamily: "Inter, system-ui, sans-serif",
          },
        }}
      >
        <App />
      </ClerkProvider>
    </BrowserRouter>
  </React.StrictMode>
);
