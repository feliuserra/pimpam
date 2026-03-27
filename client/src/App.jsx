import { lazy, Suspense } from "react";
import { Route, Routes } from "react-router-dom";
import Spinner from "./components/ui/Spinner";
import ErrorBoundary from "./components/ui/ErrorBoundary";
import UpdatePrompt from "./components/UpdatePrompt";
import { AuthProvider } from "./contexts/AuthContext";
import { WSProvider } from "./contexts/WSContext";
import { NotificationProvider } from "./contexts/NotificationContext";
import { ToastProvider } from "./contexts/ToastContext";
import { CloseFriendsProvider } from "./contexts/CloseFriendsContext";
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
const PostDetail = lazy(() => import("./pages/PostDetail"));
const CommunityPage = lazy(() => import("./pages/CommunityPage"));
const Search = lazy(() => import("./pages/Search"));
const HashtagPage = lazy(() => import("./pages/HashtagPage"));
const MessageThread = lazy(() => import("./pages/MessageThread"));
const Settings = lazy(() => import("./pages/Settings"));
const AccountSettings = lazy(() => import("./pages/settings/AccountSettings"));
const ProfileSettings = lazy(() => import("./pages/settings/ProfileSettings"));
const NotificationSettings = lazy(() => import("./pages/settings/NotificationSettings"));
const FriendGroupSettings = lazy(() => import("./pages/settings/FriendGroupSettings"));
const PrivacySettings = lazy(() => import("./pages/settings/PrivacySettings"));
const DataSettings = lazy(() => import("./pages/settings/DataSettings"));
const Discover = lazy(() => import("./pages/Discover"));
const Friends = lazy(() => import("./pages/Friends"));
const Issues = lazy(() => import("./pages/Issues"));
const IssueDetail = lazy(() => import("./pages/IssueDetail"));
const ModPanel = lazy(() => import("./pages/ModPanel"));
const AdminDashboard = lazy(() => import("./pages/AdminDashboard"));
const Terms = lazy(() => import("./pages/Terms"));
const Privacy = lazy(() => import("./pages/Privacy"));
const Offline = lazy(() => import("./pages/Offline"));

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
          <ToastProvider>
            <NotificationProvider>
              <CloseFriendsProvider>
              <UpdatePrompt />
              <Suspense fallback={<PageLoader />}>
                <Routes>
                  <Route path="/login" element={<Login />} />
                  <Route path="/login/totp" element={<LoginTotp />} />
                  <Route path="/register" element={<Register />} />
                  <Route path="/verify-email-sent" element={<VerifyEmailSent />} />
                  <Route path="/verify-email" element={<VerifyEmail />} />
                  <Route path="/forgot-password" element={<ForgotPassword />} />
                  <Route path="/reset-password" element={<ResetPassword />} />
                  <Route path="/terms" element={<Terms />} />
                  <Route path="/privacy" element={<Privacy />} />
                  <Route path="/offline" element={<Offline />} />
                  <Route element={<AppShell />}>
                    <Route index element={<Feed />} />
                    <Route path="/discover" element={<Discover />} />
                    <Route path="/friends" element={<Friends />} />
                    <Route path="/communities" element={<Communities />} />
                    <Route path="/messages" element={<Messages />} />
                    <Route path="/notifications" element={<Notifications />} />
                    <Route path="/issues" element={<Issues />} />
                    <Route path="/issues/:id" element={<IssueDetail />} />
                    <Route path="/u/:username" element={<UserProfile />} />
                    <Route path="/posts/:id" element={<PostDetail />} />
                    <Route path="/c/:name" element={<CommunityPage />} />
                    <Route path="/c/:name/mod" element={<ModPanel />} />
                    <Route path="/admin" element={<AdminDashboard />} />
                    <Route path="/search" element={<Search />} />
                    <Route path="/tag/:name" element={<HashtagPage />} />
                    <Route path="/messages/:userId" element={<MessageThread />} />
                    <Route path="/settings" element={<Settings />}>
                      <Route index element={<AccountSettings />} />
                      <Route path="profile" element={<ProfileSettings />} />
                      <Route path="notifications" element={<NotificationSettings />} />
                      <Route path="friend-groups" element={<FriendGroupSettings />} />
                      <Route path="privacy" element={<PrivacySettings />} />
                      <Route path="data" element={<DataSettings />} />
                    </Route>
                  </Route>
                </Routes>
              </Suspense>
            </CloseFriendsProvider>
            </NotificationProvider>
          </ToastProvider>
        </WSProvider>
      </AuthProvider>
    </ErrorBoundary>
  );
}
