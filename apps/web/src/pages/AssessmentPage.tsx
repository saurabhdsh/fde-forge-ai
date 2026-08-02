import {
  Alert,
  Box,
  Button,
  FormControl,
  FormControlLabel,
  Radio,
  RadioGroup,
  Stack,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { Link as RouterLink } from "react-router-dom";

import { GlassPanel } from "../components/GlassPanel";
import { api, getApiErrorMessage, type ApiEnvelope } from "../lib/api";
import { downloadAssessmentExport } from "../lib/download";
import { cx } from "../theme/tokens";
import type { Assessment, LearnerProfile } from "../types";

export function AssessmentPage() {
  const qc = useQueryClient();
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [saveNote, setSaveNote] = useState<string | null>(null);

  const profileQuery = useQuery({
    queryKey: ["learner-profile"],
    queryFn: async () => {
      const { data } = await api.get<ApiEnvelope<LearnerProfile>>("/learners/me/profile");
      return data.data;
    },
  });

  const unlockQuery = useQuery({
    queryKey: ["assessment-unlocked"],
    queryFn: async () => {
      const { data } = await api.get<
        ApiEnvelope<{ unlocked: boolean; incomplete_domains: string[] }>
      >("/courses/assessment-unlocked");
      return data.data;
    },
  });

  const latestQuery = useQuery({
    queryKey: ["assessment-latest"],
    queryFn: async () => {
      const { data } = await api.get<ApiEnvelope<Assessment | null>>("/assessments/me/latest");
      return data.data;
    },
  });

  const assessment = latestQuery.data;
  const skillsConfirmed = !!profileQuery.data?.skills_confirmed_at;
  const coursesUnlocked = unlockQuery.data?.unlocked ?? false;
  const incompleteDomains = unlockQuery.data?.incomplete_domains || [];
  const canTake =
    assessment &&
    (assessment.status === "ready" || assessment.status === "in_progress") &&
    assessment.questions.length > 0;
  const scored = assessment?.status === "scored";

  useEffect(() => {
    if (!assessment) return;
    const next: Record<string, number> = {};
    for (const a of assessment.draft_answers || []) {
      next[a.question_id] = a.selected_index;
    }
    for (const q of assessment.questions) {
      if (q.selected_index != null && next[q.id] === undefined) {
        next[q.id] = q.selected_index;
      }
    }
    if (Object.keys(next).length) setAnswers(next);
  }, [assessment?.id, assessment?.status]); // eslint-disable-line react-hooks/exhaustive-deps

  const startMutation = useMutation({
    mutationFn: async () => {
      const { data } = await api.post<ApiEnvelope<Assessment>>("/assessments/baseline", null, {
        timeout: 180000,
      });
      return data.data;
    },
    onSuccess: () => {
      setAnswers({});
      setSaveNote(null);
      qc.invalidateQueries({ queryKey: ["assessment-latest"] });
    },
  });

  const saveDraftMutation = useMutation({
    mutationFn: async () => {
      if (!assessment) throw new Error("No assessment");
      const payload = {
        answers: Object.entries(answers).map(([question_id, selected_index]) => ({
          question_id,
          selected_index,
        })),
      };
      const { data } = await api.post<ApiEnvelope<Assessment>>(
        `/assessments/${assessment.id}/draft`,
        payload,
      );
      return data.data;
    },
    onSuccess: () => {
      setSaveNote("Progress saved. You can leave and resume later.");
      qc.invalidateQueries({ queryKey: ["assessment-latest"] });
    },
  });

  const submitMutation = useMutation({
    mutationFn: async () => {
      if (!assessment) throw new Error("No assessment");
      const payload = {
        answers: assessment.questions.map((q) => ({
          question_id: q.id,
          selected_index: answers[q.id] ?? -1,
        })),
      };
      if (payload.answers.some((a) => a.selected_index < 0)) {
        throw new Error("Answer every question before submitting");
      }
      const { data } = await api.post<ApiEnvelope<Assessment>>(
        `/assessments/${assessment.id}/submit`,
        payload,
      );
      return data.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["assessment-latest"] });
      qc.invalidateQueries({ queryKey: ["learner-skills"] });
      qc.invalidateQueries({ queryKey: ["learner-profile"] });
    },
  });

  const exportMutation = useMutation({
    mutationFn: async (format: "markdown" | "json") => {
      if (!assessment) throw new Error("No assessment");
      await downloadAssessmentExport({
        path: `/assessments/${assessment.id}/export`,
        format,
        fallbackName: `baseline-assessment.${format === "json" ? "json" : "md"}`,
      });
    },
  });

  const answeredCount = useMemo(() => Object.keys(answers).length, [answers]);

  return (
    <Stack spacing={3}>
      <Stack spacing={0.5}>
        <Typography variant="overline" sx={{ color: cx.accent }}>
          Candidate
        </Typography>
        <Typography variant="h2">Baseline assessment</Typography>
        <Typography sx={{ color: cx.fgDim, maxWidth: 720 }}>
          AI-generated, advanced multiple-choice quiz from your confirmed skills (minimum 25 hard
          questions). Results update your skill profile and unlock a learning plan.
        </Typography>
      </Stack>

      {!skillsConfirmed && (
        <Alert
          severity="warning"
          action={
            <Button color="inherit" size="small" component={RouterLink} to="/onboarding">
              My profile
            </Button>
          }
        >
          Confirm your skills before starting a baseline assessment.
        </Alert>
      )}

      {skillsConfirmed && !coursesUnlocked && (
        <Alert
          severity="warning"
          action={
            <Button color="inherit" size="small" component={RouterLink} to="/courses">
              Open Courses
            </Button>
          }
        >
          Assessment is locked until you complete required domain courses
          {incompleteDomains.length
            ? ` (${incompleteDomains.map((d) => d.replace("_", " ")).join(", ")})`
            : ""}
          .
        </Alert>
      )}

      {skillsConfirmed &&
        coursesUnlocked &&
        (!assessment || assessment.status === "failed" || scored) && (
          <GlassPanel>
            <Typography variant="h5" sx={{ mb: 1 }}>
              {scored ? "Assessment complete" : "Start baseline assessment"}
            </Typography>
            {scored && (
              <Typography sx={{ color: cx.fgMuted, mb: 2 }}>
                Score: <strong style={{ color: cx.fg }}>{assessment?.score_percent}%</strong> (
                {assessment?.correct_count}/{assessment?.total_count}). You can generate a new
                baseline when ready.
              </Typography>
            )}
            {assessment?.status === "failed" && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {assessment.error_message || "Assessment generation failed."}
              </Alert>
            )}
            {startMutation.isError && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {getApiErrorMessage(startMutation.error)}
              </Alert>
            )}
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
              <Button
                variant="contained"
                onClick={() => startMutation.mutate()}
                disabled={startMutation.isPending || !skillsConfirmed || !coursesUnlocked}
              >
                {startMutation.isPending
                  ? "Generating questions…"
                  : scored
                    ? "Start new assessment"
                    : "Start assessment"}
              </Button>
              {assessment && (
                <>
                  <Button
                    variant="outlined"
                    disabled={exportMutation.isPending}
                    onClick={() => exportMutation.mutate("markdown")}
                  >
                    Export Markdown
                  </Button>
                  <Button
                    variant="outlined"
                    disabled={exportMutation.isPending}
                    onClick={() => exportMutation.mutate("json")}
                  >
                    Export JSON
                  </Button>
                </>
              )}
            </Stack>
            {exportMutation.isError && (
              <Alert severity="error" sx={{ mt: 2 }}>
                {getApiErrorMessage(exportMutation.error)}
              </Alert>
            )}
          </GlassPanel>
        )}

      {canTake && assessment && (
        <Stack spacing={2}>
          <Typography sx={{ color: cx.fgDim }}>
            Answered {answeredCount} / {assessment.questions.length}
          </Typography>
          {assessment.questions.map((q, idx) => (
            <GlassPanel key={q.id}>
              <Typography variant="overline" sx={{ color: cx.fgDim }}>
                Question {idx + 1}
                {q.skill_name ? ` · ${q.skill_name}` : ""}
              </Typography>
              <Typography sx={{ mt: 1, mb: 2, fontWeight: 600 }}>{q.stem}</Typography>
              <FormControl>
                <RadioGroup
                  value={answers[q.id] ?? ""}
                  onChange={(e) => {
                    setAnswers((prev) => ({ ...prev, [q.id]: Number(e.target.value) }));
                    setSaveNote(null);
                  }}
                >
                  {q.choices.map((choice, i) => (
                    <FormControlLabel
                      key={`${q.id}-${i}`}
                      value={i}
                      control={<Radio />}
                      label={choice}
                    />
                  ))}
                </RadioGroup>
              </FormControl>
            </GlassPanel>
          ))}
          {(submitMutation.isError || saveDraftMutation.isError) && (
            <Alert severity="error">
              {getApiErrorMessage(submitMutation.error || saveDraftMutation.error)}
            </Alert>
          )}
          {saveNote && <Alert severity="success">{saveNote}</Alert>}
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            <Button
              variant="outlined"
              onClick={() => saveDraftMutation.mutate()}
              disabled={saveDraftMutation.isPending || answeredCount === 0}
            >
              {saveDraftMutation.isPending ? "Saving…" : "Save progress"}
            </Button>
            <Button
              variant="outlined"
              disabled={exportMutation.isPending}
              onClick={() => exportMutation.mutate("markdown")}
            >
              Export Markdown
            </Button>
            <Button
              variant="outlined"
              disabled={exportMutation.isPending}
              onClick={() => exportMutation.mutate("json")}
            >
              Export JSON
            </Button>
            <Button
              variant="contained"
              onClick={() => submitMutation.mutate()}
              disabled={submitMutation.isPending || answeredCount < assessment.questions.length}
            >
              {submitMutation.isPending ? "Submitting…" : "Submit assessment"}
            </Button>
          </Stack>
        </Stack>
      )}

      {scored && assessment && (
        <Stack spacing={2}>
          <Alert severity="success">
            Score {assessment.score_percent}% — review answers below. Admins track interview
            readiness after Coding is also scored (≥70% each).
          </Alert>
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            <Button variant="outlined" component={RouterLink} to="/coding">
              Open coding lab
            </Button>
            <Button
              variant="outlined"
              disabled={exportMutation.isPending}
              onClick={() => exportMutation.mutate("markdown")}
            >
              Export Markdown
            </Button>
            <Button
              variant="outlined"
              disabled={exportMutation.isPending}
              onClick={() => exportMutation.mutate("json")}
            >
              Export JSON
            </Button>
          </Stack>
          {assessment.questions.map((q, idx) => (
            <GlassPanel key={q.id}>
              <Typography variant="overline" sx={{ color: cx.fgDim }}>
                Q{idx + 1}
                {" · "}
                <Box
                  component="span"
                  sx={{ color: q.is_correct ? cx.success : cx.danger, fontWeight: 700 }}
                >
                  {q.is_correct ? "Correct" : "Incorrect"}
                </Box>
              </Typography>
              <Typography sx={{ mt: 1, mb: 1, fontWeight: 600 }}>{q.stem}</Typography>
              <Typography sx={{ color: cx.fgMuted, fontSize: "0.85rem" }}>
                Your answer: {q.selected_index != null ? q.choices[q.selected_index] : "—"}
              </Typography>
              {q.correct_index != null && (
                <Typography sx={{ color: cx.success, fontSize: "0.85rem" }}>
                  Correct: {q.choices[q.correct_index]}
                </Typography>
              )}
              {q.explanation && (
                <Typography sx={{ color: cx.fgDim, mt: 1, fontSize: "0.85rem" }}>
                  {q.explanation}
                </Typography>
              )}
            </GlassPanel>
          ))}
        </Stack>
      )}
    </Stack>
  );
}
