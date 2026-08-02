/** cx design tokens from ui.md — dark glass enterprise shell */
export const cx = {
  void: "#040508",
  deep: "#080a10",
  surface: "#0c0f16",
  panel: "#10141d",
  raised: "#151a24",
  line: "rgba(148,163,184,0.09)",
  border: "rgba(148,163,184,0.11)",
  borderStrong: "rgba(148,163,184,0.2)",
  fg: "#e8edf4",
  fgMuted: "#cbd5e1",
  fgDim: "#8b9cb0",
  accent: "#5ec8f2",
  accent2: "#9b8bd4",
  success: "#3ecf9b",
  warn: "#e8b84a",
  danger: "#f08984",
} as const;

export const glassInset = "inset 0 1px 0 rgba(255,255,255,0.05)";
export const easeOut = [0.22, 1, 0.36, 1] as const;
