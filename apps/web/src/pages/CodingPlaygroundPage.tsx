import {
  Alert,
  Box,
  Button,
  Stack,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Code2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link as RouterLink } from "react-router-dom";

import { CodeEditor } from "../components/CodeEditor";
import { GlassPanel } from "../components/GlassPanel";
import { api, getApiErrorMessage, type ApiEnvelope } from "../lib/api";
import { downloadAssessmentExport } from "../lib/download";
import { cx } from "../theme/tokens";
import type { CodingAssessment, CodingQuestion } from "../types";

function isAttempted(q: CodingQuestion, code: string | undefined): boolean {
  const value = (code ?? "").trim();
  if (value.length < 8) return false;
  const starter = (q.starter_code || "").trim();
  return value !== starter;
}

export function CodingPlaygroundPage() {
  const qc = useQueryClient();
  const [index, setIndex] = useState(0);
  const [codes, setCodes] = useState<Record<string, string>>({});
  const [localError, setLocalError] = useState<string | null>(null);
  const [saveNote, setSaveNote] = useState<string | null>(null);
  const [incompleteIds, setIncompleteIds] = useState<string[]>([]);

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
    queryKey: ["coding-assessment-latest"],
    queryFn: async () => {
      const { data } = await api.get<ApiEnvelope<CodingAssessment | null>>(
        "/coding-assessments/me/latest",
      );
      return data.data;
    },
  });

  const assessment = latestQuery.data;
  const unlocked = unlockQuery.data?.unlocked ?? false;
  const scored = assessment?.status === "scored";
  const canWork =
    assessment &&
    (assessment.status === "ready" || assessment.status === "in_progress") &&
    assessment.questions.length > 0;

  useEffect(() => {
    if (!assessment?.questions?.length) return;
    const draftByQ: Record<string, string> = {};
    for (const a of assessment.draft_answers || []) {
      draftByQ[a.question_id] = a.code;
    }
    setCodes((prev) => {
      const next = { ...prev };
      for (const q of assessment.questions) {
        if (next[q.id] === undefined) {
          next[q.id] =
            draftByQ[q.id] ||
            q.submitted_code ||
            q.starter_code ||
            "# Write your solution here\n";
        }
      }
      return next;
    });
  }, [assessment?.id, assessment?.status]); // eslint-disable-line react-hooks/exhaustive-deps

  const questions = assessment?.questions || [];
  const current = questions[index];

  const answeredCount = useMemo(
    () => questions.filter((q) => isAttempted(q, codes[q.id])).length,
    [codes, questions],
  );

  const incompleteQuestions = useMemo(
    () => questions.filter((q) => !isAttempted(q, codes[q.id])),
    [codes, questions],
  );

  const startMutation = useMutation({
    mutationFn: async () => {
      const { data } = await api.post<ApiEnvelope<CodingAssessment>>(
        "/coding-assessments/start",
        null,
        { timeout: 180000 },
      );
      return data.data;
    },
    onSuccess: () => {
      setIndex(0);
      setCodes({});
      setLocalError(null);
      setSaveNote(null);
      setIncompleteIds([]);
      qc.invalidateQueries({ queryKey: ["coding-assessment-latest"] });
    },
  });

  const saveDraftMutation = useMutation({
    mutationFn: async () => {
      if (!assessment) throw new Error("No assessment");
      const answers = assessment.questions
        .filter((q) => codes[q.id] !== undefined)
        .map((q) => ({
          question_id: q.id,
          code: codes[q.id] ?? "",
        }));
      const { data } = await api.post<ApiEnvelope<CodingAssessment>>(
        `/coding-assessments/${assessment.id}/draft`,
        { answers },
      );
      return data.data;
    },
    onSuccess: () => {
      setSaveNote("Progress saved. You can leave and resume later.");
      setLocalError(null);
      qc.invalidateQueries({ queryKey: ["coding-assessment-latest"] });
    },
  });

  const exportMutation = useMutation({
    mutationFn: async (format: "markdown" | "json") => {
      if (!assessment) throw new Error("No assessment");
      await downloadAssessmentExport({
        path: `/coding-assessments/${assessment.id}/export`,
        format,
        fallbackName: `coding-assessment.${format === "json" ? "json" : "md"}`,
      });
    },
  });

  const submitMutation = useMutation({
    mutationFn: async (force: boolean) => {
      if (!assessment) throw new Error("No assessment");
      const missing = assessment.questions.filter((q) => !isAttempted(q, codes[q.id]));
      if (missing.length && !force) {
        const err = new Error(
          `Finish ${missing.length} remaining challenge(s) before submit, or choose Submit unfinished.`,
        );
        (err as Error & { incomplete: string[] }).incomplete = missing.map((q) => q.id);
        throw err;
      }
      const answers = assessment.questions.map((q) => ({
        question_id: q.id,
        code: (codes[q.id] ?? q.starter_code ?? "").trim() || "# unfinished\npass\n",
      }));
      const { data } = await api.post<ApiEnvelope<CodingAssessment>>(
        `/coding-assessments/${assessment.id}/submit`,
        { answers },
        { timeout: 360000 },
      );
      return data.data;
    },
    onSuccess: () => {
      setLocalError(null);
      setSaveNote(null);
      setIncompleteIds([]);
      qc.invalidateQueries({ queryKey: ["coding-assessment-latest"] });
    },
    onError: (error) => {
      const incomplete = (error as Error & { incomplete?: string[] }).incomplete;
      if (incomplete?.length) {
        setIncompleteIds(incomplete);
        setLocalError(getApiErrorMessage(error));
        return;
      }
      setIncompleteIds([]);
      setLocalError(getApiErrorMessage(error));
    },
  });

  return (
    <Stack spacing={3}>
      <Stack spacing={0.5}>
        <Typography variant="overline" sx={{ color: cx.accent }}>
          Candidate
        </Typography>
        <Typography variant="h2">Coding playground</Typography>
        <Typography sx={{ color: cx.fgDim, maxWidth: 760 }}>
          AI generates at least 25 hard Python challenges on agent development and GenAI systems for
          your domains. Type solutions interactively, then submit for AI rubric grading.
        </Typography>
      </Stack>

      {!unlocked && (
        <Alert
          severity="warning"
          action={
            <Button color="inherit" size="small" component={RouterLink} to="/courses">
              Open Courses
            </Button>
          }
        >
          Complete required domain courses before starting the coding assessment
          {unlockQuery.data?.incomplete_domains?.length
            ? ` (${unlockQuery.data.incomplete_domains.map((d) => d.replace("_", " ")).join(", ")})`
            : ""}
          .
        </Alert>
      )}

      {unlocked && (!assessment || assessment.status === "failed" || scored) && (
        <GlassPanel>
          <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
            <Code2 size={18} color={cx.accent} />
            <Typography variant="h5">
              {scored ? "Coding assessment complete" : "Start coding assessment"}
            </Typography>
          </Stack>
          {scored && (
            <Typography sx={{ color: cx.fgMuted, mb: 2 }}>
              Passed{" "}
              <strong style={{ color: cx.fg }}>
                {assessment?.passed_count}/{assessment?.total_count}
              </strong>{" "}
              ({assessment?.score_percent}%). You can start a new coding set when ready.
            </Typography>
          )}
          {assessment?.status === "failed" && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {assessment.error_message || "Coding assessment generation failed."}
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
              disabled={!unlocked || startMutation.isPending}
              onClick={() => startMutation.mutate()}
            >
              {startMutation.isPending
                ? "Generating 25+ coding challenges…"
                : scored
                  ? "Start new coding assessment"
                  : "Start coding assessment"}
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

      {canWork && assessment && current && (
        <Stack spacing={2}>
          <Typography sx={{ color: cx.fgDim }}>
            Edited {answeredCount} / {questions.length} · Question {index + 1} of {questions.length}
          </Typography>

          <Stack direction={{ xs: "column", md: "row" }} spacing={2} alignItems="stretch">
            <GlassPanel
              sx={{ width: { md: 260 }, flexShrink: 0, p: 1.5, maxHeight: 520, overflow: "auto" }}
            >
              <Typography variant="overline" sx={{ px: 1 }}>
                Challenges
              </Typography>
              <Stack spacing={0.4} sx={{ mt: 1 }}>
                {questions.map((q, i) => {
                  const edited = isAttempted(q, codes[q.id]);
                  const flagged = incompleteIds.includes(q.id);
                  return (
                    <Button
                      key={q.id}
                      size="small"
                      onClick={() => setIndex(i)}
                      sx={{
                        justifyContent: "flex-start",
                        color: flagged
                          ? cx.danger
                          : i === index
                            ? cx.accent
                            : edited
                              ? cx.success
                              : cx.fgMuted,
                        bgcolor: i === index ? "rgba(94,200,242,0.08)" : "transparent",
                        textAlign: "left",
                        fontSize: "0.75rem",
                      }}
                    >
                      {i + 1}. {q.title}
                    </Button>
                  );
                })}
              </Stack>
            </GlassPanel>

            <GlassPanel sx={{ flex: 1, minWidth: 0 }}>
              <Typography variant="overline" sx={{ color: cx.fgDim }}>
                {current.domain_focus || "general"} · {current.difficulty}
                {current.topic_tags?.length ? ` · ${current.topic_tags.join(", ")}` : ""}
              </Typography>
              <Typography variant="h4" sx={{ mt: 0.5, mb: 1.5 }}>
                {current.title}
              </Typography>
              <Typography
                sx={{
                  color: cx.fgMuted,
                  whiteSpace: "pre-wrap",
                  fontSize: "0.92rem",
                  lineHeight: 1.6,
                  mb: 2,
                }}
              >
                {current.prompt_markdown}
              </Typography>
              <CodeEditor
                language={current.language || "python"}
                value={codes[current.id] ?? current.starter_code}
                onChange={(next) => {
                  setCodes((prev) => ({ ...prev, [current.id]: next }));
                  setLocalError(null);
                  setSaveNote(null);
                }}
              />
              <Stack direction="row" spacing={1} sx={{ mt: 2 }} justifyContent="space-between">
                <Button
                  variant="outlined"
                  disabled={index <= 0}
                  onClick={() => setIndex((i) => Math.max(0, i - 1))}
                >
                  Previous
                </Button>
                <Button
                  variant="outlined"
                  disabled={index >= questions.length - 1}
                  onClick={() => setIndex((i) => Math.min(questions.length - 1, i + 1))}
                >
                  Next
                </Button>
              </Stack>
            </GlassPanel>
          </Stack>

          {(localError || submitMutation.isError || saveDraftMutation.isError) && (
            <Alert severity="warning">
              {localError ||
                getApiErrorMessage(submitMutation.error || saveDraftMutation.error)}
              {incompleteQuestions.length > 0 && (
                <Box sx={{ mt: 1 }}>
                  Unfinished:{" "}
                  {incompleteQuestions
                    .slice(0, 12)
                    .map((q) => questions.findIndex((x) => x.id === q.id) + 1)
                    .join(", ")}
                  {incompleteQuestions.length > 12 ? "…" : ""}
                </Box>
              )}
            </Alert>
          )}
          {saveNote && <Alert severity="success">{saveNote}</Alert>}

          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            <Button
              variant="outlined"
              disabled={saveDraftMutation.isPending || answeredCount === 0}
              onClick={() => saveDraftMutation.mutate()}
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
              disabled={submitMutation.isPending}
              onClick={() => {
                setLocalError(null);
                submitMutation.mutate(false);
              }}
            >
              {submitMutation.isPending
                ? "Submitting & grading (this can take a few minutes)…"
                : `Submit all ${questions.length} solutions`}
            </Button>
            {incompleteQuestions.length > 0 && (
              <Button
                variant="outlined"
                color="warning"
                disabled={submitMutation.isPending}
                onClick={() => {
                  setLocalError(null);
                  submitMutation.mutate(true);
                }}
              >
                Submit unfinished ({incompleteQuestions.length} left as draft)
              </Button>
            )}
          </Stack>
          <Typography sx={{ color: cx.fgDim, fontSize: "0.78rem" }}>
            Tip: Save progress to resume later. Green items in the left rail are edited. Submit stays
            clickable; if some are still starter code you’ll get a list — or use Submit unfinished.
          </Typography>
        </Stack>
      )}

      {scored && assessment && (
        <Stack spacing={2}>
          <Alert severity="success">
            Passed {assessment.passed_count}/{assessment.total_count} ({assessment.score_percent}
            %). Review feedback below.
          </Alert>
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
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
          {assessment.questions.map((q, i) => (
            <GlassPanel key={q.id}>
              <Typography variant="overline" sx={{ color: cx.fgDim }}>
                Q{i + 1} ·{" "}
                <Box
                  component="span"
                  sx={{ color: q.passed ? cx.success : cx.danger, fontWeight: 700 }}
                >
                  {q.passed ? "Passed" : "Needs work"}
                  {q.score != null ? ` · ${q.score}` : ""}
                </Box>
              </Typography>
              <Typography sx={{ fontWeight: 700, mt: 0.5 }}>{q.title}</Typography>
              {q.feedback && (
                <Typography sx={{ color: cx.fgDim, mt: 1, fontSize: "0.88rem" }}>
                  {q.feedback}
                </Typography>
              )}
              {q.submitted_code && (
                <Box sx={{ mt: 1.5 }}>
                  <CodeEditor
                    language={q.language}
                    value={q.submitted_code}
                    readOnly
                    minRows={10}
                    liveSyntax={false}
                  />
                </Box>
              )}
            </GlassPanel>
          ))}
        </Stack>
      )}
    </Stack>
  );
}
