import {
  Alert,
  LinearProgress,
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
import { useAuthStore } from "../store/authStore";
import { cx } from "../theme/tokens";
import type { LearnerSkill } from "../types";

export function SkillsPage() {
  const user = useAuthStore((s) => s.user);
  const skillsQuery = useQuery({
    queryKey: ["learner-skills"],
    queryFn: async () => {
      const { data } = await api.get<ApiEnvelope<LearnerSkill[]>>("/learners/me/skills");
      return data.data;
    },
  });

  return (
    <Stack spacing={3}>
      <Stack spacing={0.5}>
        <Typography variant="overline" sx={{ color: cx.accent }}>
          Skill intelligence
        </Typography>
        <Typography variant="h2">Skill profile</Typography>
        <Typography sx={{ color: cx.fgDim }}>
          Confirmed skills for {user?.first_name} {user?.last_name}, persisted from resume
          extraction and your corrections.
        </Typography>
      </Stack>

      {skillsQuery.isLoading && (
        <LinearProgress
          sx={{
            height: 4,
            borderRadius: 999,
            bgcolor: cx.border,
            "& .MuiLinearProgress-bar": {
              background: `linear-gradient(90deg, ${cx.accent}, ${cx.accent2})`,
            },
          }}
        />
      )}
      {skillsQuery.isError && (
        <Alert severity="error">Unable to load skills. Ensure you are signed in as a candidate.</Alert>
      )}
      {skillsQuery.data && skillsQuery.data.length === 0 && (
        <Alert severity="info">No confirmed skills yet. Complete My profile first.</Alert>
      )}
      {skillsQuery.data && skillsQuery.data.length > 0 && (
        <GlassPanel sx={{ p: 0, overflow: "hidden" }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Skill</TableCell>
                <TableCell>Pillar</TableCell>
                <TableCell>Proficiency</TableCell>
                <TableCell>Source</TableCell>
                <TableCell>Confidence</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {skillsQuery.data.map((skill) => (
                <TableRow key={skill.id}>
                  <TableCell sx={{ color: cx.fg }}>{skill.skill_name}</TableCell>
                  <TableCell>{skill.pillar_name || "—"}</TableCell>
                  <TableCell>{skill.proficiency_level}</TableCell>
                  <TableCell>{skill.source}</TableCell>
                  <TableCell>
                    {skill.confidence != null ? skill.confidence.toFixed(2) : "—"}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </GlassPanel>
      )}
    </Stack>
  );
}
