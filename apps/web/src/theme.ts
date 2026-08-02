import { alpha, createTheme } from "@mui/material/styles";

import { cx, glassInset } from "./theme/tokens";

export const theme = createTheme({
  palette: {
    mode: "dark",
    primary: {
      main: cx.accent,
      dark: "#3aa8d4",
      light: "#8ad8f7",
      contrastText: cx.void,
    },
    secondary: {
      main: cx.accent2,
      contrastText: cx.fg,
    },
    background: {
      default: cx.void,
      paper: cx.panel,
    },
    text: {
      primary: cx.fg,
      secondary: cx.fgMuted,
      disabled: cx.fgDim,
    },
    divider: cx.line,
    error: { main: cx.danger },
    warning: { main: cx.warn },
    success: { main: cx.success },
    info: { main: cx.accent },
  },
  typography: {
    fontFamily: '"Inter", system-ui, -apple-system, sans-serif',
    h1: {
      fontFamily: '"Outfit", "Inter", sans-serif',
      fontWeight: 600,
      letterSpacing: "-0.03em",
      fontSize: "2rem",
    },
    h2: {
      fontFamily: '"Outfit", "Inter", sans-serif',
      fontWeight: 600,
      letterSpacing: "-0.02em",
      fontSize: "1.65rem",
    },
    h3: {
      fontFamily: '"Outfit", "Inter", sans-serif',
      fontWeight: 600,
      letterSpacing: "-0.02em",
      fontSize: "1.35rem",
    },
    h4: {
      fontFamily: '"Outfit", "Inter", sans-serif',
      fontWeight: 600,
      fontSize: "1.15rem",
    },
    h5: { fontWeight: 600, fontSize: "1rem" },
    h6: { fontWeight: 600, fontSize: "0.95rem" },
    body1: { fontSize: "0.875rem", lineHeight: 1.55 },
    body2: { fontSize: "0.8125rem", lineHeight: 1.5, color: cx.fgMuted },
    caption: {
      fontSize: "0.6875rem",
      letterSpacing: "0.18em",
      textTransform: "uppercase",
      color: cx.fgDim,
    },
    button: { textTransform: "none", fontWeight: 600, letterSpacing: "0.01em" },
    overline: {
      fontSize: "0.625rem",
      letterSpacing: "0.2em",
      textTransform: "uppercase",
      color: cx.fgDim,
      fontWeight: 500,
    },
  },
  shape: { borderRadius: 14 },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        html: { height: "100%" },
        body: {
          height: "100%",
          backgroundColor: cx.void,
          color: cx.fg,
          backgroundImage:
            "radial-gradient(900px 480px at 12% -10%, rgba(94,200,242,0.08), transparent 55%), radial-gradient(700px 420px at 90% 0%, rgba(155,139,212,0.07), transparent 50%)",
        },
        "#root": { height: "100%", minHeight: "100%" },
        "*::-webkit-scrollbar": { width: 8, height: 8 },
        "*::-webkit-scrollbar-thumb": {
          background: alpha(cx.fgDim, 0.35),
          borderRadius: 999,
        },
        "*::-webkit-scrollbar-track": { background: "transparent" },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 10,
          boxShadow: "none",
          paddingInline: 16,
          "&:hover": { boxShadow: "none" },
        },
        containedPrimary: {
          background: `linear-gradient(135deg, ${alpha(cx.accent, 0.95)}, ${alpha(cx.accent2, 0.75)})`,
          color: cx.void,
          fontWeight: 650,
          "&:hover": {
            background: `linear-gradient(135deg, ${cx.accent}, ${cx.accent2})`,
          },
        },
        outlined: {
          borderColor: cx.border,
          background: alpha("#fff", 0.03),
          color: cx.fg,
          "&:hover": {
            borderColor: cx.borderStrong,
            background: alpha("#fff", 0.05),
          },
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: "none",
          backgroundColor: alpha(cx.panel, 0.75),
          border: `1px solid ${cx.border}`,
          boxShadow: glassInset,
          backdropFilter: "blur(18px)",
        },
      },
    },
    MuiTextField: {
      defaultProps: { size: "small", variant: "outlined" },
      styleOverrides: {
        root: {
          "& .MuiOutlinedInput-root": {
            background: alpha(cx.panel, 0.55),
            borderRadius: 12,
            "& fieldset": { borderColor: cx.border },
            "&:hover fieldset": { borderColor: cx.borderStrong },
            "&.Mui-focused fieldset": { borderColor: alpha(cx.accent, 0.55) },
          },
          "& .MuiInputLabel-root": { color: cx.fgDim },
        },
      },
    },
    MuiAlert: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          border: `1px solid ${cx.border}`,
          backdropFilter: "blur(12px)",
        },
        standardInfo: {
          background: alpha(cx.accent, 0.08),
          color: cx.fg,
        },
        standardWarning: {
          background: alpha(cx.warn, 0.1),
          color: cx.fg,
        },
        standardError: {
          background: alpha(cx.danger, 0.1),
          color: cx.fg,
        },
        standardSuccess: {
          background: alpha(cx.success, 0.1),
          color: cx.fg,
        },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        root: { borderColor: cx.line, color: cx.fgMuted },
        head: {
          color: cx.fgDim,
          fontSize: "0.65rem",
          letterSpacing: "0.16em",
          textTransform: "uppercase",
        },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: {
          backgroundImage: "none",
          backgroundColor: alpha(cx.deep, 0.88),
          backdropFilter: "blur(28px)",
          borderRight: `1px solid ${cx.line}`,
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundImage: "none",
          backgroundColor: alpha(cx.deep, 0.78),
          backdropFilter: "blur(28px)",
          borderBottom: `1px solid ${cx.line}`,
          boxShadow: "none",
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          border: `1px solid ${cx.border}`,
          background: alpha(cx.raised, 0.7),
        },
      },
    },
  },
});
