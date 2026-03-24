import { lazy, Suspense } from "react";
import { Route, Routes } from "react-router-dom";
import Spinner from "./components/ui/Spinner";
import ErrorBoundary from "./components/ui/ErrorBoundary";
import { AuthProvider } from "./contexts/AuthContext";
import { WSProvider } from "./contexts/WSContext";
import { NotificationProvider } from "./contexts/NotificationContext";
import { ToastProvider } from "./contexts/ToastContext";
import AppShell from "./layouts/AppShell";

const Login = lazy(() => import("./pages/Login"));
const Register = lazy(() => import("./pages/Register"));
const VerifyEmailSent = lazy(() => import("./pages/VerifyEmailSent"));
const VerifyEmail = lazy(() => import("./pages/VerifyEmail"));
const LoginTotp = lazy(() => import("./pages/LoginTotp"));
const ForgotPassword = lazy(() => import("./pages/ForgotPassword"));
const ResetPassword = lazy(() => import("./pages/ResetPassword"));
const Feed = lazy(() => import("./pages/Feed"));
const Communities = lazy(() => import("./pages/Communities"));
const Messages = lazy(() => import("./pages/Messages"));
const Notifications = lazy(() => import("./pages/Notifications"));
const UserProfile = lazy(() => import("./pages/UserProfile"));

function PageLoader() {
  return (
    <div style={{ display: "flex", justifyContent: "center", paddingTop: "4rem" }}>
      <Spinner size={32} />
    </div>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <WSProvider>
          <NotificationProvider>
            <ToastProvider>
              <Suspense fallback={<PageLoader />}>
                <Routes>
                  <Route path="/login" element={<Login />} />
                  <Route path="/login/totp" element={<LoginTotp />} />
                  <Route path="/register" element={<Register />} />
                  <Route path="/verify-email-sent" element={<VerifyEmailSent />} />
                  <Route path="/verify-email" element={<VerifyEmail />} />
                  <Route path="/forgot-password" element={<ForgotPassword />} />
                  <Route path="/reset-password" element={<ResetPassword />} />
                  <Route element={<AppShell />}>
                    <Route index element={<Feed />} />
                    <Route path="/communities" element={<Communities />} />
                    <Route path="/messages" element={<Messages />} />
                    <Route path="/notifications" element={<Notifications />} />
                    <Route path="/@:username" element={<UserProfile />} />
                  </Route>
                </Routes>
              </Suspense>
            </ToastProvider>
          </NotificationProvider>
        </WSProvider>
      </AuthProvider>
    </ErrorBoundary>
  );
}
