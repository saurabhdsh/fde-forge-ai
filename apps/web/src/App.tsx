import { CircularProgress, Box } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { Navigate, Route, Routes } from "react-router-dom";

import { api, type ApiEnvelope } from "./lib/api";
import { AppShell } from "./layout/AppShell";
import { AssessmentPage } from "./pages/AssessmentPage";
import { AuditLogsPage } from "./pages/AuditLogsPage";
import { CodingPlaygroundPage } from "./pages/CodingPlaygroundPage";
import { CoursePlayerPage } from "./pages/CoursePlayerPage";
import { CoursesPage } from "./pages/CoursesPage";
import { HomePage } from "./pages/HomePage";
import { LoginPage } from "./pages/LoginPage";
import { OnboardingPage } from "./pages/OnboardingPage";
import { SkillsPage } from "./pages/SkillsPage";
import { AdminCourseDocsPage } from "./pages/AdminCourseDocsPage";
import { AdminInterviewReadinessPage } from "./pages/AdminInterviewReadinessPage";
import { AdminUsersPage } from "./pages/AdminUsersPage";
import { useAuthStore } from "./store/authStore";
import type { AuthSession } from "./types";

function Protected({ children }: { children: React.ReactNode }) {
  const user = useAuthStore((s) => s.user);
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function RequirePermission({
  permission,
  children,
}: {
  permission: string;
  children: React.ReactNode;
}) {
  const user = useAuthStore((s) => s.user);
  const hasPermission = useAuthStore((s) => s.hasPermission);
  if (!user) return <Navigate to="/login" replace />;
  if (!hasPermission(permission) && !user.is_super_admin) {
    return <Navigate to="/" replace />;
  }
  return <>{children}</>;
}

export function App() {
  const setUser = useAuthStore((s) => s.setUser);
  const user = useAuthStore((s) => s.user);

  const sessionQuery = useQuery({
    queryKey: ["session"],
    queryFn: async () => {
      try {
        const { data } = await api.get<ApiEnvelope<AuthSession>>("/auth/me");
        setUser(data.data.user);
        return data.data;
      } catch {
        setUser(null);
        return null;
      }
    },
    retry: false,
    refetchOnWindowFocus: false,
  });

  if (sessionQuery.isPending) {
    return (
      <Box
        sx={{
          minHeight: "100vh",
          display: "grid",
          placeItems: "center",
          bgcolor: "#040508",
        }}
      >
        <CircularProgress sx={{ color: "#5ec8f2" }} />
      </Box>
    );
  }

  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to="/" replace /> : <LoginPage />} />
      <Route
        path="/"
        element={
          <Protected>
            <AppShell />
          </Protected>
        }
      >
        <Route index element={<HomePage />} />
        <Route path="onboarding" element={<OnboardingPage />} />
        <Route path="skills" element={<SkillsPage />} />
        <Route path="courses" element={<CoursesPage />} />
        <Route path="courses/:courseId" element={<CoursePlayerPage />} />
        <Route path="assessment" element={<AssessmentPage />} />
        <Route path="coding" element={<CodingPlaygroundPage />} />
        <Route path="admin/users" element={<AdminUsersPage />} />
        <Route
          path="admin/course-docs"
          element={
            <RequirePermission permission="curriculum.create">
              <AdminCourseDocsPage />
            </RequirePermission>
          }
        />
        <Route
          path="admin/interview-readiness"
          element={
            <RequirePermission permission="analytics.executive">
              <AdminInterviewReadinessPage />
            </RequirePermission>
          }
        />
        <Route
          path="admin/audit"
          element={
            <RequirePermission permission="audit.read">
              <AuditLogsPage />
            </RequirePermission>
          }
        />
      </Route>
      <Route path="*" element={<Navigate to={user ? "/" : "/login"} replace />} />
    </Routes>
  );
}
