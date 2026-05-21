import { useEffect } from "react";
import { Navigate, Route, Routes, useNavigate, useLocation } from "react-router-dom";

import { useTelegram } from "@/hooks/useTelegram";
import { useAuthStore } from "@/store/authStore";

import Splash from "@/pages/Splash";
import ShareContact from "@/pages/ShareContact";
import Home from "@/pages/Home";
import CourseMocks from "@/pages/CourseMocks";
import MockIntro from "@/pages/MockIntro";
import MockPlayer from "@/pages/MockPlayer";
import MockResults from "@/pages/MockResults";
import History from "@/pages/History";
import AdminHome from "@/pages/admin/AdminHome";
import MockEditor from "@/pages/admin/MockEditor";
import NotInTelegram from "@/pages/NotInTelegram";

function ProtectedRoute({ children, adminOnly }: { children: JSX.Element; adminOnly?: boolean }) {
  const user = useAuthStore((s) => s.user);
  if (!user) return <Navigate to="/" replace />;
  if (adminOnly && user.role !== "admin") return <Navigate to="/home" replace />;
  return children;
}

function BackButtonBridge() {
  const navigate = useNavigate();
  const location = useLocation();
  const { tg } = useTelegram();

  useEffect(() => {
    if (!tg) return;
    if (location.pathname === "/" || location.pathname === "/home") {
      tg.BackButton.hide();
      return;
    }
    tg.BackButton.show();
    const handler = () => navigate(-1);
    tg.BackButton.onClick(handler);
    return () => tg.BackButton.offClick(handler);
  }, [tg, location.pathname, navigate]);

  return null;
}

export default function App() {
  const { tg, isInTelegram } = useTelegram();

  useEffect(() => {
    if (!tg) return;
    tg.ready();
    tg.expand();
    document.documentElement.style.setProperty("--tg-bg", tg.themeParams.bg_color || "#ffffff");
    document.documentElement.style.setProperty("--tg-text", tg.themeParams.text_color || "#1a1a1a");
    document.documentElement.style.setProperty("--tg-hint", tg.themeParams.hint_color || "#707070");
    document.documentElement.style.setProperty("--tg-link", tg.themeParams.link_color || "#2481cc");
    document.documentElement.style.setProperty("--tg-button", tg.themeParams.button_color || "#2481cc");
    document.documentElement.style.setProperty(
      "--tg-button-text",
      tg.themeParams.button_text_color || "#ffffff",
    );
    document.documentElement.style.setProperty(
      "--tg-secondary-bg",
      tg.themeParams.secondary_bg_color || "#f4f4f4",
    );
  }, [tg]);

  if (!isInTelegram && import.meta.env.PROD) {
    return <NotInTelegram />;
  }

  return (
    <>
      <BackButtonBridge />
      <Routes>
        <Route path="/" element={<Splash />} />
        <Route path="/share-contact" element={<ShareContact />} />
        <Route
          path="/home"
          element={
            <ProtectedRoute>
              <Home />
            </ProtectedRoute>
          }
        />
        <Route
          path="/courses/:courseId/mocks"
          element={
            <ProtectedRoute>
              <CourseMocks />
            </ProtectedRoute>
          }
        />
        <Route
          path="/mocks/:mockId"
          element={
            <ProtectedRoute>
              <MockIntro />
            </ProtectedRoute>
          }
        />
        <Route
          path="/attempts/:attemptId"
          element={
            <ProtectedRoute>
              <MockPlayer />
            </ProtectedRoute>
          }
        />
        <Route
          path="/attempts/:attemptId/results"
          element={
            <ProtectedRoute>
              <MockResults />
            </ProtectedRoute>
          }
        />
        <Route
          path="/history"
          element={
            <ProtectedRoute>
              <History />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin"
          element={
            <ProtectedRoute adminOnly>
              <AdminHome />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/mocks/:mockId"
          element={
            <ProtectedRoute adminOnly>
              <MockEditor />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </>
  );
}
