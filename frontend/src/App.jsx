import { Routes, Route, Navigate } from "react-router-dom";
import { useAuth, SignedIn, SignedOut } from "@clerk/clerk-react";
import { useEffect } from "react";
import { setTokenGetter } from "@/lib/api";

import LandingPage from "@/pages/LandingPage";
import Dashboard from "@/pages/Dashboard";
import CodeReview from "@/pages/CodeReview";
import PRReview from "@/pages/PRReview";
import DigestSettings from "@/pages/DigestSettings";
import ReviewHistory from "@/pages/ReviewHistory";
import ReviewDetail from "@/pages/ReviewDetail";
import SharedReview from "@/pages/SharedReview";
import SignInPage from "@/pages/SignIn";
import SignUpPage from "@/pages/SignUp";
import Navbar from "@/components/layout/Navbar";

function ProtectedRoute({ children }) {
  return (
    <>
      <SignedIn>{children}</SignedIn>
      <SignedOut>
        <Navigate to="/sign-in" replace />
      </SignedOut>
    </>
  );
}

function AppLayout({ children }) {
  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>
    </div>
  );
}

export default function App() {
  const { getToken } = useAuth();

  useEffect(() => {
    setTokenGetter(() => getToken());
  }, [getToken]);

  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/sign-in/*" element={<SignInPage />} />
      <Route path="/sign-up/*" element={<SignUpPage />} />
      <Route path="/share/:token" element={<SharedReview />} />

      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <AppLayout><Dashboard /></AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/review/code"
        element={
          <ProtectedRoute>
            <AppLayout><CodeReview /></AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/review/pr"
        element={
          <ProtectedRoute>
            <AppLayout><PRReview /></AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/review/:id"
        element={
          <ProtectedRoute>
            <AppLayout><ReviewDetail /></AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/digest"
        element={
          <ProtectedRoute>
            <AppLayout><DigestSettings /></AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/history"
        element={
          <ProtectedRoute>
            <AppLayout><ReviewHistory /></AppLayout>
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}
