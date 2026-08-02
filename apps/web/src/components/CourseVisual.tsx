import { Box, Stack, Typography } from "@mui/material";
import { useId, useMemo } from "react";

import { cx } from "../theme/tokens";

type AnyRec = Record<string, unknown>;

type Node = {
  id: string;
  label: string;
  x: number;
  y: number;
  detail?: string;
};

type Edge = { from: string; to: string; label?: string };

type CardItem = { title: string; body?: string };

function asRecord(v: unknown): AnyRec {
  return v && typeof v === "object" && !Array.isArray(v) ? (v as AnyRec) : {};
}

function asArray(v: unknown): unknown[] {
  return Array.isArray(v) ? v : [];
}

function str(v: unknown, fallback = ""): string {
  if (typeof v === "string") return v.trim();
  if (typeof v === "number" || typeof v === "boolean") return String(v);
  return fallback;
}

function num(v: unknown): number | null {
  if (typeof v === "number" && Number.isFinite(v)) return v;
  if (typeof v === "string" && v.trim() !== "" && Number.isFinite(Number(v))) {
    return Number(v);
  }
  return null;
}

/** Pull the first non-empty array under common AI key aliases. */
function pickList(payload: AnyRec, keys: string[]): unknown[] {
  for (const key of keys) {
    const arr = asArray(payload[key]);
    if (arr.length) return arr;
  }
  // Last resort: any array value in the payload
  for (const value of Object.values(payload)) {
    if (Array.isArray(value) && value.length) return value;
  }
  return [];
}

function normalizeCards(payload: AnyRec): CardItem[] {
  return pickList(payload, ["items", "cards", "nodes", "steps", "events", "phases"]).map(
    (raw, i) => {
      if (typeof raw === "string") return { title: raw };
      const o = asRecord(raw);
      return {
        title:
          str(o.title) ||
          str(o.label) ||
          str(o.name) ||
          str(o.heading) ||
          `Item ${i + 1}`,
        body: str(o.body) || str(o.detail) || str(o.description) || str(o.text) || undefined,
      };
    },
  );
}

function normalizeSteps(payload: AnyRec, preferred: string[]): CardItem[] {
  return pickList(payload, preferred).map((raw, i) => {
    if (typeof raw === "string") return { title: raw };
    const o = asRecord(raw);
    return {
      title:
        str(o.label) ||
        str(o.title) ||
        str(o.name) ||
        str(o.stage) ||
        str(o.step) ||
        `Step ${i + 1}`,
      body: str(o.detail) || str(o.body) || str(o.description) || undefined,
    };
  });
}

function normalizeGraph(payload: AnyRec): { nodes: Node[]; edges: Edge[] } {
  const rawNodes = pickList(payload, ["nodes", "entities", "points", "items"]);
  const rawEdges = pickList(payload, ["edges", "links", "connections"]);

  const nodes: Node[] = rawNodes.map((raw, i) => {
    if (typeof raw === "string") {
      return { id: `n${i}`, label: raw, x: NaN, y: NaN };
    }
    const o = asRecord(raw);
    const id = str(o.id) || str(o.key) || `n${i}`;
    return {
      id,
      label: str(o.label) || str(o.title) || str(o.name) || id,
      x: num(o.x) ?? NaN,
      y: num(o.y) ?? NaN,
      detail: str(o.detail) || str(o.body) || str(o.description) || undefined,
    };
  });

  // Auto-layout when coords missing / invalid / clustered
  const validCoords = nodes.filter(
    (n) => Number.isFinite(n.x) && Number.isFinite(n.y) && n.x >= 0 && n.y >= 0,
  );
  const needLayout =
    validCoords.length < Math.max(1, Math.ceil(nodes.length * 0.6)) ||
    (validCoords.length >= 2 &&
      new Set(validCoords.map((n) => `${Math.round(n.x)},${Math.round(n.y)}`)).size === 1);

  if (needLayout) {
    const count = Math.max(nodes.length, 1);
    const cols = Math.min(4, Math.max(2, Math.ceil(Math.sqrt(count))));
    nodes.forEach((n, i) => {
      const col = i % cols;
      const row = Math.floor(i / cols);
      const rows = Math.ceil(count / cols);
      n.x = ((col + 0.5) / cols) * 100;
      n.y = ((row + 0.5) / rows) * 100;
    });
  } else {
    nodes.forEach((n, i) => {
      if (!Number.isFinite(n.x) || !Number.isFinite(n.y)) {
        n.x = 15 + (i % 4) * 23;
        n.y = 18 + Math.floor(i / 4) * 28;
      }
      // Keep inside pad zone (prompts sometimes use 0–100 that clips labels)
      n.x = Math.min(92, Math.max(8, n.x));
      n.y = Math.min(90, Math.max(10, n.y));
    });
  }

  const idSet = new Set(nodes.map((n) => n.id));
  const edges: Edge[] = rawEdges
    .map((raw) => {
      const o = asRecord(raw);
      const from = str(o.from) || str(o.source) || str(o.start);
      const to = str(o.to) || str(o.target) || str(o.end);
      return { from, to, label: str(o.label) || undefined };
    })
    .filter((e) => e.from && e.to && idSet.has(e.from) && idSet.has(e.to));

  return { nodes, edges };
}

function FlowStrip({
  items,
  kind,
}: {
  items: CardItem[];
  kind: "process" | "timeline";
}) {
  if (!items.length) return null;
  return (
    <Stack
      direction="row"
      spacing={1}
      flexWrap="wrap"
      useFlexGap
      sx={{ mt: 2 }}
      role="list"
      aria-label={kind === "process" ? "Process steps" : "Timeline"}
    >
      {items.map((item, i) => (
        <Box
          key={`${item.title}-${i}`}
          role="listitem"
          sx={{
            flex: "1 1 150px",
            p: 1.5,
            borderRadius: 2,
            border: `1px solid ${cx.border}`,
            bgcolor: "rgba(94,200,242,0.06)",
            minHeight: 88,
          }}
        >
          <Typography variant="overline" sx={{ color: cx.accent }}>
            {kind === "process" ? `Step ${i + 1}` : `Stage ${i + 1}`}
          </Typography>
          <Typography sx={{ fontWeight: 600, fontSize: "0.9rem", mt: 0.25 }}>
            {item.title}
          </Typography>
          {item.body && (
            <Typography sx={{ color: cx.fgDim, fontSize: "0.78rem", mt: 0.5 }}>
              {item.body}
            </Typography>
          )}
        </Box>
      ))}
    </Stack>
  );
}

function CardsGrid({ items }: { items: CardItem[] }) {
  if (!items.length) return null;
  return (
    <Stack direction="row" spacing={1.25} flexWrap="wrap" useFlexGap sx={{ mt: 2 }}>
      {items.map((item, i) => (
        <Box
          key={`${item.title}-${i}`}
          sx={{
            flex: "1 1 180px",
            p: 2,
            borderRadius: 2,
            border: `1px solid ${cx.borderStrong}`,
            background:
              "linear-gradient(145deg, rgba(155,139,212,0.12), rgba(94,200,242,0.05))",
            minHeight: 96,
          }}
        >
          <Typography sx={{ fontWeight: 700, mb: 0.75 }}>{item.title}</Typography>
          {item.body && (
            <Typography sx={{ color: cx.fgMuted, fontSize: "0.82rem" }}>{item.body}</Typography>
          )}
        </Box>
      ))}
    </Stack>
  );
}

function GraphSchematic({ nodes, edges }: { nodes: Node[]; edges: Edge[] }) {
  const uid = useId().replace(/:/g, "");
  const byId = useMemo(
    () => Object.fromEntries(nodes.map((n) => [n.id, n])),
    [nodes],
  );

  // Fit viewBox to content with padding so nodes never clip
  const xs = nodes.map((n) => n.x);
  const ys = nodes.map((n) => n.y);
  const minX = Math.min(...xs, 0) - 12;
  const maxX = Math.max(...xs, 100) + 12;
  const minY = Math.min(...ys, 0) - 14;
  const maxY = Math.max(...ys, 100) + 14;
  const vbW = Math.max(40, maxX - minX);
  const vbH = Math.max(40, maxY - minY);

  const nodeW = Math.min(28, Math.max(18, vbW / Math.max(3, Math.sqrt(nodes.length) + 1)));
  const nodeH = Math.min(16, Math.max(10, vbH / Math.max(3, Math.sqrt(nodes.length) + 1)));

  return (
    <Box
      sx={{
        mt: 2,
        borderRadius: 2,
        border: `1px solid ${cx.border}`,
        bgcolor: "rgba(8,10,16,0.65)",
        overflow: "hidden",
        position: "relative",
      }}
    >
      <svg
        viewBox={`${minX} ${minY} ${vbW} ${vbH}`}
        width="100%"
        height={Math.min(360, Math.max(220, vbH * 2.4))}
        role="img"
        aria-label="Course diagram"
        preserveAspectRatio="xMidYMid meet"
      >
        <defs>
          <linearGradient id={`nodeFill-${uid}`} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="rgba(94,200,242,0.4)" />
            <stop offset="100%" stopColor="rgba(155,139,212,0.28)" />
          </linearGradient>
          <marker
            id={`arrow-${uid}`}
            viewBox="0 0 10 10"
            refX="8"
            refY="5"
            markerWidth="5"
            markerHeight="5"
            orient="auto-start-reverse"
          >
            <path d="M 0 0 L 10 5 L 0 10 z" fill="rgba(148,163,184,0.7)" />
          </marker>
        </defs>

        {edges.map((e, i) => {
          const a = byId[e.from];
          const b = byId[e.to];
          if (!a || !b) return null;
          const mx = (a.x + b.x) / 2;
          const my = (a.y + b.y) / 2;
          return (
            <g key={`e-${i}`}>
              <line
                x1={a.x}
                y1={a.y}
                x2={b.x}
                y2={b.y}
                stroke="rgba(148,163,184,0.55)"
                strokeWidth={Math.max(0.5, vbW / 180)}
                markerEnd={`url(#arrow-${uid})`}
              />
              {e.label && (
                <text
                  x={mx}
                  y={my - 2}
                  fill="#9aabc0"
                  fontSize={Math.max(2.8, vbW / 38)}
                  textAnchor="middle"
                >
                  {e.label.length > 24 ? `${e.label.slice(0, 22)}…` : e.label}
                </text>
              )}
            </g>
          );
        })}

        {nodes.map((n) => {
          const label = n.label;
          const fontSize = Math.max(2.6, Math.min(4.2, nodeW / (label.length > 18 ? 5.5 : 4.2)));
          const lines =
            label.length > 22
              ? [label.slice(0, 18).trim(), label.slice(18, 36).trim() + (label.length > 36 ? "…" : "")]
              : label.length > 12
                ? [
                    label.slice(0, Math.ceil(label.length / 2)).trim(),
                    label.slice(Math.ceil(label.length / 2)).trim(),
                  ]
                : [label];
          return (
            <g key={n.id}>
              <rect
                x={n.x - nodeW / 2}
                y={n.y - nodeH / 2}
                width={nodeW}
                height={nodeH}
                rx={2}
                fill={`url(#nodeFill-${uid})`}
                stroke="rgba(94,200,242,0.65)"
                strokeWidth={Math.max(0.35, vbW / 220)}
              />
              {lines.map((line, li) => (
                <text
                  key={li}
                  x={n.x}
                  y={n.y + (li - (lines.length - 1) / 2) * (fontSize + 0.6) + fontSize * 0.35}
                  fill="#e8edf4"
                  fontSize={fontSize}
                  textAnchor="middle"
                >
                  {line}
                </text>
              ))}
            </g>
          );
        })}
      </svg>

      {/* Accessible text fallback under the schematic */}
      <Stack spacing={0.5} sx={{ px: 2, pb: 1.5 }}>
        <Typography variant="overline" sx={{ color: cx.fgDim }}>
          Schematic nodes
        </Typography>
        <Typography sx={{ color: cx.fgMuted, fontSize: "0.78rem" }}>
          {nodes.map((n) => n.label).join(" · ")}
        </Typography>
      </Stack>
    </Box>
  );
}

function EmptyVisualNotice({ visualType }: { visualType: string }) {
  return (
    <Box
      sx={{
        mt: 2,
        p: 2,
        borderRadius: 2,
        border: `1px dashed ${cx.border}`,
        bgcolor: "rgba(148,163,184,0.04)",
      }}
    >
      <Typography sx={{ color: cx.fgDim, fontSize: "0.85rem" }}>
        Visual ({visualType}) had no usable layout data for this slide.
      </Typography>
    </Box>
  );
}

export function CourseVisual({
  visualType,
  payload,
}: {
  visualType: string;
  payload: Record<string, unknown> | null | undefined;
}) {
  const type = (visualType || "none").toLowerCase().trim();
  const data = asRecord(payload);

  if (!type || type === "none") return null;

  if (type === "process" || type === "timeline") {
    const preferred =
      type === "process"
        ? ["steps", "process", "stages", "phases", "items", "events"]
        : ["events", "timeline", "stages", "phases", "steps", "items"];
    const items = normalizeSteps(data, preferred);
    if (!items.length) {
      // Fall back to cards / graph nodes if mis-typed
      const cards = normalizeCards(data);
      if (cards.length) return <CardsGrid items={cards} />;
      const graph = normalizeGraph(data);
      if (graph.nodes.length) return <GraphSchematic {...graph} />;
      return <EmptyVisualNotice visualType={type} />;
    }
    return <FlowStrip items={items} kind={type} />;
  }

  if (type === "cards") {
    const items = normalizeCards(data);
    if (!items.length) {
      const steps = normalizeSteps(data, ["steps", "events", "items"]);
      if (steps.length) return <CardsGrid items={steps} />;
      return <EmptyVisualNotice visualType={type} />;
    }
    return <CardsGrid items={items} />;
  }

  // map / diagram / unknown structured visuals
  if (type === "map" || type === "diagram" || type === "graph" || type === "flowchart") {
    const graph = normalizeGraph(data);
    if (graph.nodes.length >= 1) return <GraphSchematic {...graph} />;
    const cards = normalizeCards(data);
    if (cards.length) return <CardsGrid items={cards} />;
    return <EmptyVisualNotice visualType={type} />;
  }

  // Unknown type: try cards then graph before giving up
  const cards = normalizeCards(data);
  if (cards.length) return <CardsGrid items={cards} />;
  const graph = normalizeGraph(data);
  if (graph.nodes.length) return <GraphSchematic {...graph} />;
  return <EmptyVisualNotice visualType={type} />;
}
