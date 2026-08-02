import {
  Alert,
  Chip,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import { useQuery } from "@tanstack/react-query";

import { GlassPanel } from "../components/GlassPanel";
import { api, type ApiEnvelope } from "../lib/api";
import { cx } from "../theme/tokens";
import type { InterviewReadiness, AiProvidersResponse } from "../types";

function scoreLabel(status: string | null | undefined, score: number | null | undefined) {
  if (!status) return "Not started";
  if (status === "scored" && score != null) return `${score}%`;
  return status.replace(/_/g, " ");
}

export function AdminInterviewReadinessPage() {
  const readinessQuery = useQuery({
    queryKey: ["interview-readiness"],
    queryFn: async () => {
      const { data } = await api.get<ApiEnvelope<InterviewReadiness>>(
        "/analytics/interview-readiness",
      );
      return data.data;
    },
  });

  const providersQuery = useQuery({
    queryKey: ["ai-providers"],
    queryFn: async () => {
      const { data } = await api.get<ApiEnvelope<AiProvidersResponse>>("/ai/providers");
      return data.data;
    },
  });

  const data = readinessQuery.data;
  const candidates = data?.candidates || [];
  const providers = providersQuery.data;

  return (
    <Stack spacing={3}>
      <Stack spacing={0.5}>
        <Typography variant="overline" sx={{ color: cx.accent }}>
          Administration
        </Typography>
        <Typography variant="h2">Interview readiness</Typography>
        <Typography sx={{ color: cx.fgDim, maxWidth: 760 }}>
          Candidates with saved MCQ and Coding sessions. Ready for a manual human interview when
          both scores are at least 70%.
        </Typography>
      </Stack>

      {readinessQuery.isError && (
        <Alert severity="error">Unable to load interview readiness.</Alert>
      )}

      {providers && (
        <GlassPanel>
          <Typography variant="overline" sx={{ color: cx.fgDim }}>
            LLM providers
          </Typography>
          <Typography sx={{ color: cx.fgMuted, mb: 1.5, fontSize: "0.9rem" }}>
            Default: <strong style={{ color: cx.fg }}>{providers.default_provider}</strong> · Courses,
            Assessment, and Coding use this gateway (Bedrock with OpenAI fallback).
          </Typography>
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            {providers.providers.map((p) => (
              <Chip
                key={p.id}
                size="small"
                label={`${p.name}: ${p.enabled ? "ready" : "not ready"}${
                  p.default_model ? ` · ${p.default_model}` : ""
                }`}
                sx={{
                  bgcolor: p.enabled ? "rgba(62,207,155,0.15)" : "rgba(148,163,184,0.1)",
                  color: p.enabled ? cx.success : cx.fgMuted,
                  fontWeight: 600,
                  maxWidth: "100%",
                }}
              />
            ))}
          </Stack>
        </GlassPanel>
      )}

      {data && (
        <>
          <Stack direction={{ xs: "column", md: "row" }} spacing={2} useFlexGap flexWrap="wrap">
            <GlassPanel sx={{ flex: "1 1 160px", minWidth: 140, p: 2.5 }}>
              <Typography variant="overline">Organization</Typography>
              <Typography variant="h5" sx={{ mt: 1 }}>
                {data.organization_name}
              </Typography>
            </GlassPanel>
            <GlassPanel sx={{ flex: "1 1 160px", minWidth: 140, p: 2.5 }}>
              <Typography variant="overline">Ready for interview</Typography>
              <Typography variant="h4" sx={{ mt: 1, color: cx.success }}>
                {data.ready_count}
              </Typography>
            </GlassPanel>
            <GlassPanel sx={{ flex: "1 1 160px", minWidth: 140, p: 2.5 }}>
              <Typography variant="overline">Candidates</Typography>
              <Typography variant="h4" sx={{ mt: 1 }}>
                {candidates.length}
              </Typography>
            </GlassPanel>
            <GlassPanel sx={{ flex: "1 1 200px", minWidth: 160, p: 2.5 }}>
              <Typography variant="overline">Pass bar</Typography>
              <Typography variant="h5" sx={{ mt: 1 }}>
                MCQ ≥{data.mcq_pass_threshold}% · Coding ≥{data.coding_pass_threshold}%
              </Typography>
            </GlassPanel>
          </Stack>

          <GlassPanel sx={{ p: 0, overflow: "auto" }}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Candidate</TableCell>
                  <TableCell>Username</TableCell>
                  <TableCell>MCQ</TableCell>
                  <TableCell>Coding</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Notes</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {candidates.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={6}>
                      <Typography sx={{ color: cx.fgDim, p: 2 }}>
                        No learner candidates in this organization yet.
                      </Typography>
                    </TableCell>
                  </TableRow>
                )}
                {candidates.map((c) => (
                  <TableRow
                    key={c.user_id}
                    sx={{
                      bgcolor: c.ready_for_manual_interview
                        ? "rgba(62,207,155,0.06)"
                        : "transparent",
                    }}
                  >
                    <TableCell>
                      <Typography sx={{ fontWeight: 600 }}>
                        {c.first_name} {c.last_name}
                      </Typography>
                      <Typography sx={{ color: cx.fgDim, fontSize: "0.75rem" }}>
                        {c.email}
                      </Typography>
                    </TableCell>
                    <TableCell>{c.username || "—"}</TableCell>
                    <TableCell>
                      {scoreLabel(c.mcq_status, c.mcq_score_percent)}
                    </TableCell>
                    <TableCell>
                      {scoreLabel(c.coding_status, c.coding_score_percent)}
                    </TableCell>
                    <TableCell>
                      <Chip
                        size="small"
                        label={c.ready_for_manual_interview ? "Ready" : "Not ready"}
                        sx={{
                          bgcolor: c.ready_for_manual_interview
                            ? "rgba(62,207,155,0.15)"
                            : "rgba(148,163,184,0.1)",
                          color: c.ready_for_manual_interview ? cx.success : cx.fgMuted,
                          fontWeight: 600,
                        }}
                      />
                    </TableCell>
                    <TableCell>
                      <Typography sx={{ color: cx.fgDim, fontSize: "0.8rem", maxWidth: 320 }}>
                        {c.readiness_reason}
                      </Typography>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </GlassPanel>
        </>
      )}
    </Stack>
  );
}
