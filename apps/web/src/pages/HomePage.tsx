import { Alert, Button, Stack, Typography } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, BookOpen, ClipboardCheck, Code2, Users } from "lucide-react";
import { Link as RouterLink } from "react-router-dom";

import { GlassPanel } from "../components/GlassPanel";
import { api, type ApiEnvelope } from "../lib/api";
import { useAuthStore } from "../store/authStore";
import { cx } from "../theme/tokens";
import type {
  Assessment,
  CodingAssessment,
  CourseCatalog,
  LearnerProfile,
  LearnerSkill,
} from "../types";

export function HomePage() {
  const user = useAuthStore((s) => s.user);
  const hasPermission = useAuthStore((s) => s.hasPermission);
  const isLearner = !!user?.roles.includes("learner");
  const isAdmin = hasPermission("user.view") || !!user?.is_super_admin;
  const canAnalytics = hasPermission("analytics.executive") || !!user?.is_super_admin;

  const profileQuery = useQuery({
    queryKey: ["learner-profile"],
    enabled: isLearner,
    queryFn: async () => {
      const { data } = await api.get<ApiEnvelope<LearnerProfile>>("/learners/me/profile");
      return data.data;
    },
  });

  const skillsQuery = useQuery({
    queryKey: ["learner-skills"],
    enabled: isLearner,
    queryFn: async () => {
      const { data } = await api.get<ApiEnvelope<LearnerSkill[]>>("/learners/me/skills");
      return data.data;
    },
  });

  const assessmentQuery = useQuery({
    queryKey: ["assessment-latest"],
    enabled: isLearner,
    queryFn: async () => {
      const { data } = await api.get<ApiEnvelope<Assessment | null>>("/assessments/me/latest");
      return data.data;
    },
  });

  const codingQuery = useQuery({
    queryKey: ["coding-assessment-latest"],
    enabled: isLearner,
    queryFn: async () => {
      const { data } = await api.get<ApiEnvelope<CodingAssessment | null>>(
        "/coding-assessments/me/latest",
      );
      return data.data;
    },
  });

  const coursesQuery = useQuery({
    queryKey: ["courses-catalog"],
    enabled: isLearner,
    queryFn: async () => {
      const { data } = await api.get<ApiEnvelope<CourseCatalog>>("/courses/catalog");
      return data.data;
    },
  });

  const profileIncomplete = isLearner && !profileQuery.data?.profile_completed_at;
  const skillsConfirmed = !!profileQuery.data?.skills_confirmed_at;
  const assessmentScore =
    assessmentQuery.data?.status === "scored"
      ? `${assessmentQuery.data.score_percent}%`
      : assessmentQuery.data?.status || "Not started";
  const codingScore =
    codingQuery.data?.status === "scored"
      ? `${codingQuery.data.score_percent}%`
      : codingQuery.data?.status || "Not started";
  const courseItems = coursesQuery.data?.items || [];
  const coursesDone = courseItems.filter((i) => i.course?.status === "completed").length;
  const coursesTotal = courseItems.length;
  const courseProgressLabel =
    coursesTotal > 0
      ? coursesQuery.data?.assessment_unlocked
        ? `${coursesDone}/${coursesTotal} · unlocked`
        : `${coursesDone}/${coursesTotal}`
      : "No domains";

  return (
    <Stack spacing={3}>
      <Stack spacing={0.5}>
        <Typography variant="overline" sx={{ color: cx.accent }}>
          {isLearner ? "Candidate workspace" : "Workspace"}
        </Typography>
        <Typography variant="h2">Welcome, {user?.first_name}</Typography>
        <Typography sx={{ color: cx.fgDim, maxWidth: 720 }}>
          Signed in as <strong style={{ color: cx.fg }}>{user?.username}</strong>
          {user?.organization_name ? ` · ${user.organization_name}` : ""}.
          {isLearner
            ? " Track onboarding, courses, assessment, and coding progress here."
            : " Use User Management and Interview readiness to run the academy."}
        </Typography>
      </Stack>

      {isLearner && (
        <>
          {profileIncomplete && (
            <Alert
              severity="info"
              action={
                <Button
                  color="inherit"
                  size="small"
                  component={RouterLink}
                  to="/onboarding"
                  endIcon={<ArrowRight size={14} />}
                >
                  Complete profile
                </Button>
              }
            >
              Finish your profile, privacy consent, and resume upload to continue.
            </Alert>
          )}

          <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
            <Metric
              label="Onboarding status"
              value={profileQuery.data?.onboarding_status ?? "—"}
            />
            <Metric label="Confirmed skills" value={String(skillsQuery.data?.length ?? 0)} />
            <Metric label="Courses" value={courseProgressLabel} />
            <Metric label="Assessment" value={assessmentScore} />
            <Metric label="Coding" value={codingScore} />
          </Stack>

          <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
            <GlassPanel sx={{ flex: 1 }}>
              <Typography variant="h5" sx={{ mb: 1 }}>
                Continue profile
              </Typography>
              <Typography sx={{ color: cx.fgDim, mb: 2 }}>
                Resume upload and skill confirmation.
              </Typography>
              <Button variant="contained" component={RouterLink} to="/onboarding">
                My profile
              </Button>
            </GlassPanel>
            <GlassPanel sx={{ flex: 1 }}>
              <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
                <BookOpen size={18} color={cx.accent} />
                <Typography variant="h5">Courses</Typography>
              </Stack>
              <Typography sx={{ color: cx.fgDim, mb: 2 }}>
                Complete domain super-courses to unlock Assessment and Coding.
              </Typography>
              <Button variant="outlined" component={RouterLink} to="/courses">
                Open courses
              </Button>
            </GlassPanel>
            <GlassPanel sx={{ flex: 1 }}>
              <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
                <ClipboardCheck size={18} color={cx.accent} />
                <Typography variant="h5">Assessment</Typography>
              </Stack>
              <Typography sx={{ color: cx.fgDim, mb: 2 }}>
                {!skillsConfirmed
                  ? "Confirm skills first, then complete courses."
                  : coursesQuery.data?.assessment_unlocked
                    ? "Take or review your baseline skill quiz."
                    : "Finish domain courses to unlock the quiz."}
              </Typography>
              <Button
                variant="outlined"
                component={RouterLink}
                to="/assessment"
                disabled={!skillsConfirmed}
              >
                Open assessment
              </Button>
            </GlassPanel>
            <GlassPanel sx={{ flex: 1 }}>
              <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
                <Code2 size={18} color={cx.accent} />
                <Typography variant="h5">Coding lab</Typography>
              </Stack>
              <Typography sx={{ color: cx.fgDim, mb: 2 }}>
                {coursesQuery.data?.assessment_unlocked
                  ? "Complete coding challenges for interview readiness."
                  : "Finish domain courses to unlock coding."}
              </Typography>
              <Button
                variant="outlined"
                component={RouterLink}
                to="/coding"
                disabled={!skillsConfirmed}
              >
                Open coding lab
              </Button>
            </GlassPanel>
          </Stack>
        </>
      )}

      {isAdmin && (
        <GlassPanel>
          <Stack direction="row" spacing={1.5} alignItems="flex-start">
            <Users size={20} color={cx.accent} style={{ marginTop: 2 }} />
            <Stack spacing={0.5}>
              <Typography variant="h5" sx={{ mb: 0.75 }}>
                Admin tools
              </Typography>
              <Typography sx={{ color: cx.fgDim, mb: 2, maxWidth: 640 }}>
                Manage candidates and see who cleared MCQ + Coding for a manual interview.
              </Typography>
              <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                <Button variant="outlined" component={RouterLink} to="/admin/users">
                  Open User Management
                </Button>
                {canAnalytics && (
                  <Button
                    variant="outlined"
                    component={RouterLink}
                    to="/admin/interview-readiness"
                  >
                    Interview readiness
                  </Button>
                )}
              </Stack>
            </Stack>
          </Stack>
        </GlassPanel>
      )}
    </Stack>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <GlassPanel sx={{ flex: 1, p: 2.5 }}>
      <Typography variant="overline">{label}</Typography>
      <Typography variant="h4" sx={{ mt: 1, wordBreak: "break-word" }}>
        {value}
      </Typography>
    </GlassPanel>
  );
}
