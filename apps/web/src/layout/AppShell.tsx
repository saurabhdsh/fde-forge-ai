import {
  Box,
  Button,
  IconButton,
  Stack,
  Tooltip,
  Typography,
} from "@mui/material";
import { AnimatePresence, motion } from "framer-motion";
import {
  BookOpen,
  ClipboardList,
  ClipboardCheck,
  Code2,
  FileStack,
  Home,
  LayoutDashboard,
  LogOut,
  Menu,
  PanelLeftClose,
  PanelLeftOpen,
  ScrollText,
  Sparkles,
  UserCheck,
  UserRound,
} from "lucide-react";
import { useMemo, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";

import { api } from "../lib/api";
import { useAuthStore } from "../store/authStore";
import { cx } from "../theme/tokens";

const COLLAPSED = 76;
const EXPANDED = 248;

type NavItem = {
  to: string;
  label: string;
  group: string;
  icon: React.ReactNode;
  end?: boolean;
  permission?: string;
  learnerOnly?: boolean;
  adminOnly?: boolean;
};

export function AppShell() {
  const user = useAuthStore((s) => s.user);
  const hasPermission = useAuthStore((s) => s.hasPermission);
  const setUser = useAuthStore((s) => s.setUser);
  const navigate = useNavigate();
  const location = useLocation();
  const [expanded, setExpanded] = useState(true);
  const appName = import.meta.env.VITE_APP_NAME || "FDE Forge AI";
  const isLearner = !!user?.roles.includes("learner");
  const isAdmin = hasPermission("user.view") || !!user?.is_super_admin;

  const navItems: NavItem[] = useMemo(
    () => [
      {
        to: "/",
        label: "Home",
        group: "Overview",
        icon: <Home size={20} strokeWidth={1.75} />,
        end: true,
      },
      {
        to: "/onboarding",
        label: "My profile",
        group: "Candidate",
        icon: <UserRound size={20} strokeWidth={1.75} />,
        learnerOnly: true,
      },
      {
        to: "/skills",
        label: "Skills",
        group: "Candidate",
        icon: <Sparkles size={20} strokeWidth={1.75} />,
        learnerOnly: true,
      },
      {
        to: "/courses",
        label: "Courses",
        group: "Candidate",
        icon: <BookOpen size={20} strokeWidth={1.75} />,
        learnerOnly: true,
      },
      {
        to: "/assessment",
        label: "Assessment",
        group: "Candidate",
        icon: <ClipboardCheck size={20} strokeWidth={1.75} />,
        learnerOnly: true,
      },
      {
        to: "/coding",
        label: "Coding lab",
        group: "Candidate",
        icon: <Code2 size={20} strokeWidth={1.75} />,
        learnerOnly: true,
      },
      {
        to: "/admin/interview-readiness",
        label: "Interview readiness",
        group: "Admin",
        icon: <UserCheck size={20} strokeWidth={1.75} />,
        permission: "analytics.executive",
      },
      {
        to: "/admin/users",
        label: "User Management",
        group: "Admin",
        icon: <ClipboardList size={20} strokeWidth={1.75} />,
        permission: "user.view",
      },
      {
        to: "/admin/course-docs",
        label: "Course sources",
        group: "Admin",
        icon: <FileStack size={20} strokeWidth={1.75} />,
        permission: "curriculum.create",
      },
      {
        to: "/admin/audit",
        label: "Audit logs",
        group: "Admin",
        icon: <ScrollText size={20} strokeWidth={1.75} />,
        permission: "audit.read",
      },
    ],
    [],
  );

  const visibleNav = navItems.filter((item) => {
    if (item.learnerOnly && !isLearner) return false;
    if (item.permission && !hasPermission(item.permission) && !user?.is_super_admin) {
      return false;
    }
    return true;
  });

  const logout = async () => {
    await api.post("/auth/logout");
    setUser(null);
    navigate("/login");
  };

  const sectionLabel =
    visibleNav.find((n) =>
      n.end ? location.pathname === n.to : location.pathname.startsWith(n.to),
    )?.label || "Workspace";

  const railWidth = expanded ? EXPANDED : COLLAPSED;

  return (
    <Box sx={{ height: "100%", minHeight: "100vh", display: "flex", bgcolor: cx.void }}>
      {/* Nav rail */}
      <Box
        component={motion.aside}
        animate={{ width: railWidth }}
        transition={{ type: "spring", stiffness: 400, damping: 42, mass: 0.7 }}
        sx={{
          flexShrink: 0,
          height: "100vh",
          position: "sticky",
          top: 0,
          borderRight: `1px solid ${cx.line}`,
          bgcolor: "rgba(8,10,16,0.88)",
          backdropFilter: "blur(28px)",
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
          zIndex: 20,
          backgroundImage: `linear-gradient(180deg, rgba(94,200,242,0.06) 0%, transparent 28%)`,
        }}
      >
        <Box
          sx={{
            height: "3.25rem",
            px: expanded ? 2 : 1,
            display: "flex",
            alignItems: "center",
            gap: 1.25,
            borderBottom: `1px solid ${cx.line}`,
          }}
        >
          <Box
            sx={{
              width: 36,
              height: 36,
              borderRadius: 1.5,
              display: "grid",
              placeItems: "center",
              background: `linear-gradient(135deg, ${cx.accent}33, ${cx.accent2}22)`,
              border: `1px solid ${cx.borderStrong}`,
              color: cx.accent,
              flexShrink: 0,
            }}
          >
            <LayoutDashboard size={18} strokeWidth={1.75} />
          </Box>
          <AnimatePresence>
            {expanded && (
              <Box
                component={motion.div}
                initial={{ opacity: 0, x: -6 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -6 }}
                transition={{ duration: 0.2 }}
                sx={{ minWidth: 0 }}
              >
                <Typography
                  sx={{
                    fontFamily: '"Outfit", sans-serif',
                    fontWeight: 600,
                    fontSize: "0.95rem",
                    lineHeight: 1.2,
                    whiteSpace: "nowrap",
                  }}
                >
                  {appName}
                </Typography>
                <Typography
                  sx={{
                    fontSize: "0.58rem",
                    letterSpacing: "0.18em",
                    textTransform: "uppercase",
                    color: cx.fgDim,
                    whiteSpace: "nowrap",
                  }}
                >
                  FDE academy
                </Typography>
              </Box>
            )}
          </AnimatePresence>
        </Box>

        <Stack sx={{ flex: 1, p: 1, gap: 0.5, overflow: "auto" }}>
          {visibleNav.map((item) => (
            <Tooltip key={item.to} title={expanded ? "" : item.label} placement="right">
              <Box
                component={NavLink}
                to={item.to}
                end={item.end}
                sx={{
                  display: "flex",
                  alignItems: "center",
                  gap: 1.25,
                  px: expanded ? 1.25 : 0,
                  py: 1.1,
                  minHeight: 48,
                  justifyContent: expanded ? "flex-start" : "center",
                  borderRadius: 1.5,
                  color: cx.fgDim,
                  textDecoration: "none",
                  borderLeft: "2px solid transparent",
                  transition: "background 0.2s, color 0.2s, border-color 0.2s",
                  "&:hover": { color: cx.fgMuted, bgcolor: "rgba(255,255,255,0.03)" },
                  "&.active": {
                    color: cx.fg,
                    bgcolor: "rgba(94,200,242,0.08)",
                    borderLeftColor: cx.accent,
                    boxShadow: `inset 0 0 24px rgba(94,200,242,0.06)`,
                  },
                }}
              >
                <Box sx={{ display: "grid", placeItems: "center", width: 28 }}>{item.icon}</Box>
                <AnimatePresence>
                  {expanded && (
                    <Box
                      component={motion.div}
                      initial={{ opacity: 0, x: -4 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0 }}
                      transition={{ duration: 0.18 }}
                      sx={{ minWidth: 0 }}
                    >
                      <Typography sx={{ fontSize: "0.84rem", fontWeight: 550, lineHeight: 1.2 }}>
                        {item.label}
                      </Typography>
                      <Typography sx={{ fontSize: "0.65rem", color: cx.fgDim, lineHeight: 1.2 }}>
                        {item.group}
                      </Typography>
                    </Box>
                  )}
                </AnimatePresence>
              </Box>
            </Tooltip>
          ))}
        </Stack>

        <Box sx={{ p: 1, borderTop: `1px solid ${cx.line}` }}>
          <Tooltip title={expanded ? "" : "Sign out"} placement="right">
            <Button
              fullWidth
              onClick={logout}
              startIcon={expanded ? <LogOut size={16} strokeWidth={1.75} /> : undefined}
              sx={{
                justifyContent: expanded ? "flex-start" : "center",
                minWidth: 0,
                color: cx.fgDim,
                border: `1px solid ${cx.border}`,
                bgcolor: "rgba(255,255,255,0.02)",
                "&:hover": { borderColor: cx.borderStrong, color: cx.fg },
              }}
            >
              {expanded ? "Sign out" : <LogOut size={16} strokeWidth={1.75} />}
            </Button>
          </Tooltip>
        </Box>
      </Box>

      {/* Main column */}
      <Box sx={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", minHeight: 0 }}>
        {/* Top bar */}
        <Box
          sx={{
            height: "3.25rem",
            flexShrink: 0,
            display: "flex",
            alignItems: "center",
            px: 2,
            gap: 1.5,
            borderBottom: `1px solid ${cx.line}`,
            bgcolor: "rgba(8,10,16,0.78)",
            backdropFilter: "blur(28px)",
            position: "relative",
          }}
        >
          <Box
            sx={{
              position: "absolute",
              top: 0,
              left: 0,
              right: 0,
              height: 1,
              background:
                "linear-gradient(90deg, transparent, rgba(255,255,255,0.07), transparent)",
            }}
          />
          <Button
            size="small"
            onClick={() => setExpanded((v) => !v)}
            startIcon={
              expanded ? (
                <PanelLeftClose size={15} strokeWidth={1.75} />
              ) : (
                <PanelLeftOpen size={15} strokeWidth={1.75} />
              )
            }
            sx={{
              display: { xs: "none", lg: "inline-flex" },
              fontSize: "0.62rem",
              letterSpacing: "0.14em",
              textTransform: "uppercase",
              color: cx.fgDim,
              border: `1px solid ${cx.border}`,
              bgcolor: "rgba(255,255,255,0.02)",
            }}
          >
            {expanded ? "Collapse" : "Expand"}
          </Button>
          <IconButton
            size="small"
            onClick={() => setExpanded((v) => !v)}
            sx={{ display: { lg: "none" }, color: cx.fgMuted, border: `1px solid ${cx.border}` }}
          >
            <Menu size={16} />
          </IconButton>

          <Box
            sx={{
              display: "flex",
              alignItems: "center",
              gap: 1,
              px: 1.25,
              py: 0.5,
              borderRadius: 999,
              border: `1px solid ${cx.border}`,
              bgcolor: "rgba(16,20,29,0.55)",
            }}
          >
            <Typography
              sx={{
                fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
                fontSize: "0.68rem",
                color: cx.accent,
              }}
            >
              {user?.organization_slug || "org"}
            </Typography>
            <Typography sx={{ color: cx.fgDim, fontSize: "0.75rem" }}>/</Typography>
            <Typography sx={{ color: cx.fgMuted, fontSize: "0.78rem" }}>{sectionLabel}</Typography>
          </Box>

          <Box sx={{ flex: 1 }} />

          <Stack direction="row" alignItems="center" spacing={1.25}>
            <Box sx={{ textAlign: "right", display: { xs: "none", sm: "block" } }}>
              <Typography sx={{ fontSize: "0.82rem", fontWeight: 600, lineHeight: 1.2 }}>
                {user?.first_name} {user?.last_name}
              </Typography>
              <Typography sx={{ fontSize: "0.65rem", color: cx.fgDim, lineHeight: 1.2 }}>
                {user?.username}
                {isLearner && isAdmin
                  ? " · Candidate · Admin"
                  : isLearner
                    ? " · Candidate"
                    : " · Admin"}
              </Typography>
            </Box>
            <Box
              sx={{
                width: 34,
                height: 34,
                borderRadius: "50%",
                display: "grid",
                placeItems: "center",
                border: `1px solid ${cx.borderStrong}`,
                bgcolor: "rgba(94,200,242,0.12)",
                color: cx.accent,
                fontSize: "0.75rem",
                fontWeight: 700,
              }}
            >
              {(user?.first_name?.[0] || "U").toUpperCase()}
              {(user?.last_name?.[0] || "").toUpperCase()}
            </Box>
          </Stack>
        </Box>

        {/* Scrollable content */}
        <Box
          component="main"
          sx={{
            flex: 1,
            minHeight: 0,
            overflowY: "auto",
            px: { xs: 2, md: 3.5 },
            py: { xs: 2.5, md: 3.5 },
            backgroundImage: "linear-gradient(145deg, rgba(255,255,255,0.02), transparent 40%)",
          }}
        >
          <Box sx={{ maxWidth: 1100, mx: "auto" }}>
            <Outlet />
          </Box>
        </Box>

        {/* Status strip */}
        <Box
          sx={{
            height: "2.25rem",
            flexShrink: 0,
            display: "flex",
            alignItems: "center",
            px: 2,
            gap: 2,
            borderTop: `1px solid ${cx.line}`,
            bgcolor: "rgba(8,10,16,0.9)",
            backdropFilter: "blur(18px)",
            position: "relative",
          }}
        >
          <Box
            sx={{
              position: "absolute",
              top: 0,
              left: 0,
              right: 0,
              height: 1,
              background:
                "linear-gradient(90deg, transparent, rgba(255,255,255,0.06), transparent)",
            }}
          />
          <Stack direction="row" alignItems="center" spacing={1} sx={{ minWidth: 0 }}>
            <Box
              sx={{
                width: 7,
                height: 7,
                borderRadius: "50%",
                bgcolor: cx.success,
                boxShadow: `0 0 10px ${cx.success}`,
              }}
            />
            <Typography sx={{ fontSize: "0.68rem", color: cx.fg, letterSpacing: "0.04em" }}>
              Signed in as {user?.username}
            </Typography>
            <Typography sx={{ fontSize: "0.68rem", color: cx.fgDim }}>
              · {user?.organization_name}
            </Typography>
          </Stack>
          <Box sx={{ flex: 1 }} />
          <Typography
            sx={{
              fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
              fontSize: "0.62rem",
              color: cx.fgDim,
              letterSpacing: "0.08em",
            }}
          >
            v0.1.0
          </Typography>
        </Box>
      </Box>
    </Box>
  );
}
