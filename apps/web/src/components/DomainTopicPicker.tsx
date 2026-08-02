import { Alert, Box, Button, Stack, Typography } from "@mui/material";
import { useMemo, useState } from "react";

import { cx } from "../theme/tokens";
import type { CourseTopic } from "../types";

const GROUP_TINT: Record<string, string> = {
  Ecosystem: "rgba(94,200,242,0.14)",
  "Data & interop": "rgba(62,207,155,0.12)",
  "Privacy & risk": "rgba(232,184,74,0.12)",
  "GenAI in HC": "rgba(155,139,212,0.14)",
  Pipeline: "rgba(94,200,242,0.14)",
  "Quality & data": "rgba(62,207,155,0.12)",
  "AI & FDE": "rgba(155,139,212,0.14)",
  Foundations: "rgba(94,200,242,0.12)",
};

export function DomainTopicPicker({
  topics,
  selectedIds,
  onChange,
  disabled,
}: {
  topics: CourseTopic[];
  selectedIds: string[];
  onChange: (ids: string[]) => void;
  disabled?: boolean;
}) {
  const [limitHint, setLimitHint] = useState(false);
  const maxTopics = topics.length; // allow every topic in the domain catalog

  const groups = useMemo(() => {
    const map = new Map<string, CourseTopic[]>();
    for (const t of topics) {
      const list = map.get(t.group) || [];
      list.push(t);
      map.set(t.group, list);
    }
    return [...map.entries()];
  }, [topics]);

  const selected = useMemo(() => new Set(selectedIds), [selectedIds]);
  const atMax = selectedIds.length >= maxTopics;

  const toggle = (id: string) => {
    if (disabled) return;
    if (selected.has(id)) {
      setLimitHint(false);
      onChange(selectedIds.filter((x) => x !== id));
      return;
    }
    if (selectedIds.length >= maxTopics) {
      setLimitHint(true);
      return;
    }
    setLimitHint(false);
    onChange([...selectedIds, id]);
  };

  const selectGroup = (groupTopics: CourseTopic[]) => {
    if (disabled) return;
    const ids = groupTopics.map((t) => t.id);
    const allOn = ids.every((id) => selected.has(id));
    if (allOn) {
      setLimitHint(false);
      onChange(selectedIds.filter((id) => !ids.includes(id)));
      return;
    }
    // Prefer keeping the newly toggled group fully selected
    const others = selectedIds.filter((id) => !ids.includes(id));
    const room = Math.max(0, maxTopics - ids.length);
    const merged = [...ids, ...others.slice(0, room)];
    setLimitHint(others.length > room);
    onChange(merged);
  };

  if (!topics.length) {
    return (
      <Typography sx={{ color: cx.warn, fontSize: "0.85rem", mt: 1 }}>
        No topics loaded for this domain. Refresh the page.
      </Typography>
    );
  }

  return (
    <Stack spacing={1.75} sx={{ mt: 1.5 }}>
      <Stack
        direction="row"
        justifyContent="space-between"
        alignItems="baseline"
        flexWrap="wrap"
        useFlexGap
        spacing={1}
      >
        <Typography sx={{ color: cx.fgDim, fontSize: "0.82rem" }}>
          Select topics ({selectedIds.length}/{maxTopics}) — all domain topics allowed
        </Typography>
        <Stack direction="row" spacing={0.5}>
          <Button
            size="small"
            variant="text"
            disabled={!!disabled}
            onClick={() => {
              setLimitHint(false);
              onChange(topics.slice(0, Math.min(6, maxTopics)).map((t) => t.id));
            }}
          >
            Core set
          </Button>
          <Button
            size="small"
            variant="text"
            disabled={!!disabled}
            onClick={() => {
              setLimitHint(false);
              onChange(topics.map((t) => t.id));
            }}
          >
            Broad set
          </Button>
          <Button
            size="small"
            variant="text"
            disabled={!!disabled}
            onClick={() => {
              setLimitHint(false);
              onChange([]);
            }}
          >
            Clear
          </Button>
        </Stack>
      </Stack>

      {limitHint && (
        <Alert severity="info" onClose={() => setLimitHint(false)}>
          All {maxTopics} topics are already selected. Clear some first, or deselect another
          topic/group.
        </Alert>
      )}

      {groups.map(([group, groupTopics]) => (
        <Box key={group}>
          <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 0.75 }}>
            <Typography variant="overline" sx={{ color: cx.fgDim }}>
              {group}
            </Typography>
            <Button
              size="small"
              variant="text"
              disabled={!!disabled}
              onClick={() => selectGroup(groupTopics)}
              sx={{ minWidth: 0, fontSize: "0.7rem", py: 0 }}
            >
              Toggle group
            </Button>
          </Stack>
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: {
                xs: "1fr",
                sm: "1fr 1fr",
                md: "1fr 1fr 1fr",
              },
              gap: 1,
            }}
          >
            {groupTopics.map((topic) => {
              const on = selected.has(topic.id);
              const blocked = !on && atMax;
              return (
                <Box
                  key={topic.id}
                  component="button"
                  type="button"
                  disabled={!!disabled}
                  onClick={() => toggle(topic.id)}
                  aria-pressed={on}
                  title={
                    blocked
                      ? "Selection full — deselect another topic first"
                      : topic.blurb
                  }
                  sx={{
                    appearance: "none",
                    WebkitAppearance: "none",
                    textAlign: "left",
                    cursor: disabled ? "not-allowed" : blocked ? "help" : "pointer",
                    pointerEvents: "auto",
                    borderRadius: 2,
                    px: 1.5,
                    py: 1.25,
                    border: "1px solid",
                    borderColor: on
                      ? "rgba(94,200,242,0.65)"
                      : blocked
                        ? "rgba(148,163,184,0.08)"
                        : cx.border,
                    background: on
                      ? `linear-gradient(145deg, rgba(94,200,242,0.18), ${GROUP_TINT[group] || "rgba(148,163,184,0.06)"})`
                      : `linear-gradient(145deg, ${GROUP_TINT[group] || "rgba(148,163,184,0.05)"}, rgba(16,20,29,0.45))`,
                    boxShadow: on ? "inset 0 0 0 1px rgba(94,200,242,0.25)" : "none",
                    color: cx.fg,
                    font: "inherit",
                    minHeight: 76,
                    width: "100%",
                    opacity: disabled ? 0.55 : blocked ? 0.45 : 1,
                    transition:
                      "border-color 160ms ease, transform 160ms ease, background 160ms ease",
                    "&:hover": disabled
                      ? undefined
                      : {
                          borderColor: "rgba(94,200,242,0.45)",
                          transform: blocked ? undefined : "translateY(-1px)",
                        },
                    "&:focus-visible": {
                      outline: `2px solid ${cx.accent}`,
                      outlineOffset: 2,
                    },
                  }}
                >
                  <Typography sx={{ fontWeight: 700, fontSize: "0.86rem", lineHeight: 1.25 }}>
                    {topic.label}
                  </Typography>
                  <Typography sx={{ color: cx.fgDim, fontSize: "0.72rem", mt: 0.45 }}>
                    {topic.blurb}
                  </Typography>
                </Box>
              );
            })}
          </Box>
        </Box>
      ))}
    </Stack>
  );
}
