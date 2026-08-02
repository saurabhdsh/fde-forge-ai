import { Alert, Button, LinearProgress, Stack, Typography } from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BookOpen, Lock, Unlock } from "lucide-react";
import { useEffect, useState } from "react";
import { Link as RouterLink, useNavigate } from "react-router-dom";

import { DomainTopicPicker } from "../components/DomainTopicPicker";
import { GlassPanel } from "../components/GlassPanel";
import { api, getApiErrorMessage, type ApiEnvelope } from "../lib/api";
import { cx } from "../theme/tokens";
import type { Course, CourseCatalog, CourseCatalogItem } from "../types";

export function CoursesPage() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [selections, setSelections] = useState<Record<string, string[]>>({});

  const catalogQuery = useQuery({
    queryKey: ["courses-catalog"],
    queryFn: async () => {
      const { data } = await api.get<ApiEnvelope<CourseCatalog>>("/courses/catalog");
      return data.data;
    },
  });

  useEffect(() => {
    const items = catalogQuery.data?.items || [];
    if (!items.length) return;
    setSelections((prev) => {
      const next = { ...prev };
      let changed = false;
      for (const item of items) {
        if (next[item.domain] === undefined) {
          next[item.domain] = [...(item.selected_topic_ids || [])];
          changed = true;
        }
      }
      return changed ? next : prev;
    });
  }, [catalogQuery.data]);

  const saveTopics = useMutation({
    mutationFn: async ({ domain, topic_ids }: { domain: string; topic_ids: string[] }) => {
      const { data } = await api.put<ApiEnvelope<CourseCatalogItem>>(
        `/courses/domains/${domain}/topics`,
        { topic_ids },
      );
      return data.data;
    },
    onSuccess: (item) => {
      setSelections((prev) => ({ ...prev, [item.domain]: [...item.selected_topic_ids] }));
      qc.invalidateQueries({ queryKey: ["courses-catalog"] });
    },
  });

  const ensureCourse = useMutation({
    mutationFn: async ({
      domain,
      force,
      topic_ids,
    }: {
      domain: string;
      force?: boolean;
      topic_ids: string[];
    }) => {
      const { data } = await api.post<ApiEnvelope<Course>>(
        `/courses/domains/${domain}/ensure`,
        { topic_ids, force: !!force },
        { timeout: 120000, params: force ? { force: true } : undefined },
      );
      return data.data;
    },
    onSuccess: (course) => {
      qc.invalidateQueries({ queryKey: ["courses-catalog"] });
      navigate(`/courses/${course.id}`);
    },
  });

  const catalog = catalogQuery.data;
  const pickingLocked = ensureCourse.isPending;

  return (
    <Stack spacing={3}>
      <Stack spacing={0.5}>
        <Typography variant="overline" sx={{ color: cx.accent }}>
          Candidate
        </Typography>
        <Typography variant="h2">Domain courses</Typography>
        <Typography sx={{ color: cx.fgDim, maxWidth: 760 }}>
          Pick topics for each domain, then generate one tailored super-course. Assessment unlocks
          after every required domain course is completed.
        </Typography>
      </Stack>

      {catalogQuery.isError && (
        <Alert severity="error">{getApiErrorMessage(catalogQuery.error)}</Alert>
      )}

      {catalog && (
        <Alert
          severity={catalog.assessment_unlocked ? "success" : "info"}
          icon={catalog.assessment_unlocked ? <Unlock size={18} /> : <Lock size={18} />}
        >
          {catalog.assessment_unlocked
            ? "All required courses complete — Assessment is unlocked."
            : "Assessment is locked until you complete every course below."}
        </Alert>
      )}

      {(ensureCourse.isError || saveTopics.isError) && (
        <Alert severity="error">
          {getApiErrorMessage(ensureCourse.error || saveTopics.error)}
        </Alert>
      )}

      {saveTopics.isSuccess && (
        <Alert severity="success">Topics saved for {saveTopics.data.domain.replace("_", " ")}.</Alert>
      )}

      <Stack spacing={2.5}>
        {(catalog?.items || []).map((item) => {
          const course = item.course;
          const pct = course?.progress?.percent_complete ?? 0;
          const ready =
            course && ["ready", "in_progress", "completed"].includes(course.status);
          const topicIds =
            selections[item.domain] !== undefined
              ? selections[item.domain]
              : item.selected_topic_ids || [];
          const canGenerate = topicIds.length > 0;
          const generatingThis =
            ensureCourse.isPending && ensureCourse.variables?.domain === item.domain;

          return (
            <GlassPanel key={item.domain}>
              <Stack spacing={1.5}>
                <Stack
                  direction={{ xs: "column", md: "row" }}
                  spacing={2}
                  justifyContent="space-between"
                  alignItems={{ md: "flex-start" }}
                >
                  <Stack spacing={0.75} sx={{ minWidth: 0, flex: 1 }}>
                    <Stack direction="row" spacing={1} alignItems="center">
                      <BookOpen size={18} color={cx.accent} />
                      <Typography variant="overline" sx={{ color: cx.fgDim }}>
                        {item.domain.replace("_", " ")} · required · one course
                      </Typography>
                    </Stack>
                    <Typography variant="h5">{course?.title || item.title_hint}</Typography>
                    <Typography sx={{ color: cx.fgDim, fontSize: "0.88rem" }}>
                      {course?.summary || item.description}
                    </Typography>
                    {course && (
                      <Stack spacing={0.75} sx={{ mt: 1, maxWidth: 420 }}>
                        <LinearProgress
                          variant="determinate"
                          value={pct}
                          sx={{ height: 8, borderRadius: 999 }}
                        />
                        <Typography sx={{ fontSize: "0.75rem", color: cx.fgDim }}>
                          {course.completed_slides}/{course.total_slides} slides · {pct}% ·{" "}
                          {course.status}
                        </Typography>
                      </Stack>
                    )}
                    {course?.status === "failed" && (
                      <Alert severity="error" sx={{ mt: 1 }}>
                        {course.error_message || "Generation failed"}
                      </Alert>
                    )}
                  </Stack>
                  <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                    {ready && (
                      <Button
                        variant="contained"
                        component={RouterLink}
                        to={`/courses/${course!.id}`}
                      >
                        {course!.status === "completed" ? "Review course" : "Continue"}
                      </Button>
                    )}
                    <Button
                      variant={ready ? "outlined" : "contained"}
                      disabled={pickingLocked || !canGenerate}
                      onClick={() =>
                        ensureCourse.mutate({
                          domain: item.domain,
                          force: !!ready || course?.status === "failed",
                          topic_ids: topicIds,
                        })
                      }
                    >
                      {generatingThis
                        ? "Generating detailed course…"
                        : ready
                          ? "Regenerate with topics"
                          : course?.status === "failed"
                            ? "Retry generate"
                            : "Generate & start"}
                    </Button>
                    <Button
                      variant="outlined"
                      disabled={pickingLocked || saveTopics.isPending || !canGenerate}
                      onClick={() =>
                        saveTopics.mutate({ domain: item.domain, topic_ids: topicIds })
                      }
                    >
                      {saveTopics.isPending && saveTopics.variables?.domain === item.domain
                        ? "Saving…"
                        : "Save topics"}
                    </Button>
                  </Stack>
                </Stack>

                <DomainTopicPicker
                  topics={item.topics || []}
                  selectedIds={topicIds}
                  disabled={pickingLocked}
                  onChange={(ids) =>
                    setSelections((prev) => ({ ...prev, [item.domain]: ids }))
                  }
                />
                {!canGenerate && (
                  <Alert severity="warning">
                    Select at least one topic (or tap Core set), then Save / Generate.
                  </Alert>
                )}
              </Stack>
            </GlassPanel>
          );
        })}
      </Stack>

      {catalog && catalog.items.length === 0 && (
        <Alert
          severity="warning"
          action={
            <Button color="inherit" size="small" component={RouterLink} to="/onboarding">
              My profile
            </Button>
          }
        >
          Select healthcare, life sciences, and/or technical domains in My profile first.
        </Alert>
      )}
    </Stack>
  );
}
