import {
  Alert,
  Box,
  Button,
  LinearProgress,
  Stack,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { Link as RouterLink, useParams } from "react-router-dom";

import { CourseVisual } from "../components/CourseVisual";
import { GlassPanel } from "../components/GlassPanel";
import { api, getApiErrorMessage, type ApiEnvelope } from "../lib/api";
import { cx } from "../theme/tokens";
import type { Course, CourseSlide } from "../types";

export function CoursePlayerPage() {
  const { courseId } = useParams();
  const qc = useQueryClient();
  const [moduleIdx, setModuleIdx] = useState(0);
  const [slideIdx, setSlideIdx] = useState(0);

  const courseQuery = useQuery({
    queryKey: ["course", courseId],
    enabled: !!courseId,
    queryFn: async () => {
      const { data } = await api.get<ApiEnvelope<Course>>(`/courses/${courseId}`);
      return data.data;
    },
  });

  const course = courseQuery.data;
  const modules = course?.modules || [];
  const currentModule = modules[moduleIdx];
  const slides = currentModule?.slides || [];
  const slide: CourseSlide | undefined = slides[slideIdx];

  useEffect(() => {
    if (!course?.progress?.current_slide_id) return;
    for (let mi = 0; mi < modules.length; mi++) {
      const si = modules[mi].slides.findIndex((s) => s.id === course.progress?.current_slide_id);
      if (si >= 0) {
        setModuleIdx(mi);
        setSlideIdx(si);
        break;
      }
    }
  }, [course?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const flat = useMemo(() => {
    const list: Array<{ mi: number; si: number; slide: CourseSlide }> = [];
    modules.forEach((m, mi) => m.slides.forEach((s, si) => list.push({ mi, si, slide: s })));
    return list;
  }, [modules]);

  const absoluteIndex = flat.findIndex((x) => x.mi === moduleIdx && x.si === slideIdx);

  const completeSlide = useMutation({
    mutationFn: async (sid: string) => {
      const { data } = await api.post<ApiEnvelope<Course>>(`/courses/${courseId}/slides/complete`, {
        slide_id: sid,
      });
      return data.data;
    },
    onSuccess: (updated) => {
      qc.setQueryData(["course", courseId], updated);
      qc.invalidateQueries({ queryKey: ["courses-catalog"] });
      qc.invalidateQueries({ queryKey: ["assessment-unlocked"] });
    },
  });

  const goNext = async () => {
    if (!slide) return;
    if (!slide.completed) {
      await completeSlide.mutateAsync(slide.id);
    }
    if (absoluteIndex < flat.length - 1) {
      const n = flat[absoluteIndex + 1];
      setModuleIdx(n.mi);
      setSlideIdx(n.si);
    }
  };

  const goPrev = () => {
    if (absoluteIndex <= 0) return;
    const p = flat[absoluteIndex - 1];
    setModuleIdx(p.mi);
    setSlideIdx(p.si);
  };

  if (courseQuery.isLoading) {
    return <Typography sx={{ color: cx.fgDim }}>Loading course…</Typography>;
  }
  if (courseQuery.isError || !course) {
    return <Alert severity="error">Unable to load course.</Alert>;
  }

  return (
    <Stack spacing={2.5}>
      <Stack spacing={0.5}>
        <Typography variant="overline" sx={{ color: cx.accent }}>
          {course.domain.replace("_", " ")} course
        </Typography>
        <Typography variant="h2">{course.title}</Typography>
        <LinearProgress
          variant="determinate"
          value={course.progress?.percent_complete ?? 0}
          sx={{ height: 8, borderRadius: 999, maxWidth: 480 }}
        />
        <Typography sx={{ fontSize: "0.75rem", color: cx.fgDim }}>
          {course.completed_slides}/{course.total_slides} slides · Module {moduleIdx + 1}/
          {modules.length}
        </Typography>
      </Stack>

      <Stack direction={{ xs: "column", md: "row" }} spacing={2} alignItems="stretch">
        <GlassPanel sx={{ width: { md: 260 }, flexShrink: 0, p: 1.5 }}>
          <Typography variant="overline" sx={{ px: 1 }}>
            Modules
          </Typography>
          <Stack spacing={0.5} sx={{ mt: 1 }}>
            {modules.map((m, i) => (
              <Button
                key={m.id}
                size="small"
                onClick={() => {
                  setModuleIdx(i);
                  setSlideIdx(0);
                }}
                sx={{
                  justifyContent: "flex-start",
                  color: i === moduleIdx ? cx.accent : cx.fgMuted,
                  bgcolor: i === moduleIdx ? "rgba(94,200,242,0.08)" : "transparent",
                  textAlign: "left",
                }}
              >
                {i + 1}. {m.title}
              </Button>
            ))}
          </Stack>
        </GlassPanel>

        <GlassPanel sx={{ flex: 1, minWidth: 0 }}>
          {slide ? (
            <Stack spacing={2}>
              <Typography variant="overline" sx={{ color: cx.fgDim }}>
                Slide {slideIdx + 1} / {slides.length}
                {slide.completed ? " · completed" : ""}
              </Typography>
              <Typography variant="h4">{slide.title}</Typography>
              <Typography
                sx={{
                  color: cx.fgMuted,
                  whiteSpace: "pre-wrap",
                  fontSize: "0.95rem",
                  lineHeight: 1.65,
                }}
              >
                {slide.body_markdown}
              </Typography>

              <CourseVisual visualType={slide.visual_type} payload={slide.visual_payload} />

              {slide.key_takeaway && (
                <Box
                  sx={{
                    p: 2,
                    borderRadius: 2,
                    border: `1px solid ${cx.borderStrong}`,
                    bgcolor: "rgba(62,207,155,0.08)",
                  }}
                >
                  <Typography variant="overline" sx={{ color: cx.success }}>
                    Key takeaway
                  </Typography>
                  <Typography sx={{ mt: 0.5 }}>{slide.key_takeaway}</Typography>
                </Box>
              )}

              {slide.self_check?.question && (
                <Box
                  sx={{
                    p: 2,
                    borderRadius: 2,
                    border: `1px solid ${cx.border}`,
                    bgcolor: "rgba(155,139,212,0.08)",
                  }}
                >
                  <Typography variant="overline" sx={{ color: cx.accent2 }}>
                    Self-check
                  </Typography>
                  <Typography sx={{ mt: 0.5, fontWeight: 600 }}>
                    {slide.self_check.question}
                  </Typography>
                  {slide.self_check.answer && (
                    <Typography sx={{ mt: 1, color: cx.fgDim, fontSize: "0.85rem" }}>
                      Answer: {slide.self_check.answer}
                    </Typography>
                  )}
                </Box>
              )}

              {completeSlide.isError && (
                <Alert severity="error">{getApiErrorMessage(completeSlide.error)}</Alert>
              )}

              <Stack direction="row" spacing={1} justifyContent="space-between">
                <Button variant="outlined" onClick={goPrev} disabled={absoluteIndex <= 0}>
                  Previous
                </Button>
                <Button
                  variant="contained"
                  onClick={() => goNext()}
                  disabled={completeSlide.isPending}
                >
                  {absoluteIndex >= flat.length - 1
                    ? slide.completed
                      ? "Course complete"
                      : "Complete course"
                    : slide.completed
                      ? "Next"
                      : "Complete & next"}
                </Button>
              </Stack>

              {course.status === "completed" && (
                <Alert
                  severity="success"
                  action={
                    <Button color="inherit" size="small" component={RouterLink} to="/assessment">
                      Go to Assessment
                    </Button>
                  }
                >
                  Course completed. Finish any other required courses to unlock Assessment.
                </Alert>
              )}
            </Stack>
          ) : (
            <Alert severity="warning">No slides in this module.</Alert>
          )}
        </GlassPanel>
      </Stack>
    </Stack>
  );
}
