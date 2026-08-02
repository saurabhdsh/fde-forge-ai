import {
  Alert,
  Box,
  Button,
  Checkbox,
  FormControlLabel,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { GlassPanel } from "../components/GlassPanel";
import { api, getApiErrorMessage, type ApiEnvelope } from "../lib/api";
import { useAuthStore } from "../store/authStore";
import { cx } from "../theme/tokens";
import type {
  AIExtraction,
  ExtractedSkill,
  LearnerProfile,
  ResumeExtractionPayload,
} from "../types";

const TARGET_ROLES = [
  "Payer FDE",
  "Provider FDE",
  "Claims FDE",
  "Healthcare Interoperability FDE",
  "Clinical Development FDE",
  "Agentic AI FDE",
  "Knowledge Fabric FDE",
];

export function OnboardingPage() {
  const qc = useQueryClient();
  const user = useAuthStore((s) => s.user);
  const [file, setFile] = useState<File | null>(null);
  const [editablePayload, setEditablePayload] = useState<ResumeExtractionPayload | null>(null);

  const profileQuery = useQuery({
    queryKey: ["learner-profile"],
    queryFn: async () => {
      const { data } = await api.get<ApiEnvelope<LearnerProfile>>("/learners/me/profile");
      return data.data;
    },
  });

  const extractionQuery = useQuery({
    queryKey: ["learner-extraction"],
    queryFn: async () => {
      const { data } = await api.get<ApiEnvelope<AIExtraction | null>>("/learners/me/extraction");
      return data.data;
    },
  });

  useEffect(() => {
    const payload =
      extractionQuery.data?.edited_payload ||
      extractionQuery.data?.validated_payload ||
      null;
    if (payload) setEditablePayload(payload);
  }, [extractionQuery.data]);

  const [form, setForm] = useState({
    target_fde_role: "",
    available_weekly_hours: 8,
    years_of_experience: 3,
    summary: "",
    consent_privacy: false,
    consent_ai_processing: false,
    domain_preferences: [] as string[],
  });

  useEffect(() => {
    if (!profileQuery.data) return;
    setForm({
      target_fde_role: profileQuery.data.target_fde_role || "",
      available_weekly_hours: profileQuery.data.available_weekly_hours || 8,
      years_of_experience: profileQuery.data.years_of_experience || 3,
      summary: profileQuery.data.summary || "",
      consent_privacy: profileQuery.data.consent_privacy,
      consent_ai_processing: profileQuery.data.consent_ai_processing,
      domain_preferences: profileQuery.data.domain_preferences || [],
    });
  }, [profileQuery.data]);

  const saveProfile = useMutation({
    mutationFn: async () => {
      const { data } = await api.patch<ApiEnvelope<LearnerProfile>>("/learners/me/profile", form);
      return data.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["learner-profile"] }),
  });

  const uploadResume = useMutation({
    mutationFn: async () => {
      if (!file) throw new Error("Select a PDF or DOCX resume first");
      const body = new FormData();
      body.append("file", file);
      const { data } = await api.post<
        ApiEnvelope<{ resume: unknown; extraction: AIExtraction | null }>
      >("/learners/me/resume", body, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      return data.data;
    },
    onSuccess: (result) => {
      if (result.extraction?.validated_payload) {
        setEditablePayload(result.extraction.validated_payload);
      }
      qc.invalidateQueries({ queryKey: ["learner-extraction"] });
      qc.invalidateQueries({ queryKey: ["learner-profile"] });
    },
  });

  const retryExtraction = useMutation({
    mutationFn: async (resumeId: string) => {
      const { data } = await api.post<ApiEnvelope<AIExtraction>>(
        `/learners/me/resume/${resumeId}/extract`,
      );
      return data.data;
    },
    onSuccess: (extraction) => {
      if (extraction.validated_payload) {
        setEditablePayload(extraction.validated_payload);
      }
      qc.invalidateQueries({ queryKey: ["learner-extraction"] });
      qc.invalidateQueries({ queryKey: ["learner-profile"] });
    },
  });

  const confirmSkills = useMutation({
    mutationFn: async () => {
      if (!extractionQuery.data?.id || !editablePayload) {
        throw new Error("No extraction available to confirm");
      }
      const { data } = await api.post(
        `/learners/me/extraction/${extractionQuery.data.id}/confirm`,
        { payload: editablePayload },
      );
      return data.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["learner-skills"] });
      qc.invalidateQueries({ queryKey: ["learner-profile"] });
      qc.invalidateQueries({ queryKey: ["learner-extraction"] });
    },
  });

  const updateSkill = (index: number, patch: Partial<ExtractedSkill>) => {
    if (!editablePayload) return;
    const skills = [...editablePayload.skills];
    skills[index] = { ...skills[index], ...patch };
    setEditablePayload({ ...editablePayload, skills });
  };

  const removeSkill = (index: number) => {
    if (!editablePayload) return;
    setEditablePayload({
      ...editablePayload,
      skills: editablePayload.skills.filter((_, i) => i !== index),
    });
  };

  return (
    <Stack spacing={4}>
      <Box>
        <Typography variant="overline" sx={{ color: cx.accent }}>
          Candidate profile
        </Typography>
        <Typography variant="h2" sx={{ mt: 0.75, mb: 1 }}>
          Welcome, {user?.first_name}
        </Typography>
        <Typography sx={{ color: cx.fgDim, maxWidth: 720 }}>
          Signed in as <strong style={{ color: cx.fg }}>{user?.username}</strong>. Complete your
          profile, upload a resume, then edit and confirm skills. Everything is saved to your
          candidate account.
        </Typography>
      </Box>

      <Section title="1. Profile & consent">
        <Stack spacing={2} maxWidth={640}>
          <TextField
            select
            label="Target FDE role"
            value={form.target_fde_role}
            onChange={(e) => setForm((f) => ({ ...f, target_fde_role: e.target.value }))}
            fullWidth
          >
            {TARGET_ROLES.map((role) => (
              <MenuItem key={role} value={role}>
                {role}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            label="Years of experience"
            type="number"
            value={form.years_of_experience}
            onChange={(e) =>
              setForm((f) => ({ ...f, years_of_experience: Number(e.target.value) }))
            }
          />
          <TextField
            label="Available weekly hours"
            type="number"
            value={form.available_weekly_hours}
            onChange={(e) =>
              setForm((f) => ({ ...f, available_weekly_hours: Number(e.target.value) }))
            }
          />
          <TextField
            label="Professional summary"
            multiline
            minRows={3}
            value={form.summary}
            onChange={(e) => setForm((f) => ({ ...f, summary: e.target.value }))}
          />
          <Box>
            <Typography sx={{ color: cx.fgMuted, fontSize: "0.8rem", mb: 1 }}>
              Domain preferences — select all that apply
            </Typography>
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
              {(
                [
                  { id: "healthcare", label: "Healthcare" },
                  { id: "life_sciences", label: "Life sciences" },
                  { id: "technical", label: "Technical" },
                ] as const
              ).map((d) => {
                const selected = form.domain_preferences.includes(d.id);
                return (
                  <Button
                    key={d.id}
                    type="button"
                    variant={selected ? "contained" : "outlined"}
                    onClick={() =>
                      setForm((f) => ({
                        ...f,
                        domain_preferences: selected
                          ? f.domain_preferences.filter((x) => x !== d.id)
                          : [...f.domain_preferences, d.id],
                      }))
                    }
                    sx={{
                      textTransform: "none",
                      borderColor: selected ? cx.accent : cx.border,
                      bgcolor: selected ? "rgba(94,200,242,0.18)" : "rgba(255,255,255,0.02)",
                      color: selected ? cx.accent : cx.fgMuted,
                      "&:hover": {
                        borderColor: cx.accent,
                        bgcolor: selected
                          ? "rgba(94,200,242,0.28)"
                          : "rgba(255,255,255,0.05)",
                      },
                    }}
                  >
                    {d.label}
                  </Button>
                );
              })}
            </Stack>
            {form.domain_preferences.length > 0 && (
              <Typography sx={{ mt: 1, fontSize: "0.72rem", color: cx.fgDim }}>
                Selected: {form.domain_preferences.join(", ")}
              </Typography>
            )}
          </Box>
          <FormControlLabel
            control={
              <Checkbox
                checked={form.consent_privacy}
                onChange={(e) => setForm((f) => ({ ...f, consent_privacy: e.target.checked }))}
              />
            }
            label="I acknowledge the privacy notice and consent to profile processing."
          />
          <FormControlLabel
            control={
              <Checkbox
                checked={form.consent_ai_processing}
                onChange={(e) =>
                  setForm((f) => ({ ...f, consent_ai_processing: e.target.checked }))
                }
              />
            }
            label="I consent to AI processing of my resume for skills extraction (human review required for published training content)."
          />
          {saveProfile.isError && (
            <Alert severity="error">{getApiErrorMessage(saveProfile.error)}</Alert>
          )}
          {saveProfile.isSuccess && <Alert severity="success">Profile saved.</Alert>}
          <Button
            variant="contained"
            onClick={() => saveProfile.mutate()}
            disabled={saveProfile.isPending}
            sx={{ alignSelf: "flex-start" }}
          >
            Save profile
          </Button>
        </Stack>
      </Section>

      <Section title="2. Resume upload & AI extraction">
        <Stack spacing={2} maxWidth={720}>
          <Alert severity="info">
            Supported types: PDF, DOCX, TXT, MD. Files are stored in MinIO. Text is extracted with
            PyMuPDF/python-docx, then sent to the configured OpenAI model. No mocked AI responses.
          </Alert>
          <Button variant="outlined" component="label" sx={{ alignSelf: "flex-start" }}>
            Select resume
            <input
              hidden
              type="file"
              accept=".pdf,.docx,.txt,.md"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
            />
          </Button>
          {file && (
            <Typography variant="body2">
              Selected: {file.name} ({Math.round(file.size / 1024)} KB)
            </Typography>
          )}
          {uploadResume.isError && (
            <Alert severity="error">{getApiErrorMessage(uploadResume.error)}</Alert>
          )}
          {uploadResume.isSuccess && uploadResume.data.extraction?.status === "configuration_error" && (
            <Alert severity="warning">
              Resume and text were stored, but AI extraction is not configured:{" "}
              {uploadResume.data.extraction.error_message}. Set OPENAI_API_KEY and retry extraction.
            </Alert>
          )}
          {uploadResume.isSuccess &&
            uploadResume.data.extraction &&
            uploadResume.data.extraction.status !== "configuration_error" &&
            uploadResume.data.extraction.status !== "failed" && (
              <Alert severity="success">
                Resume stored and processed. Provider: {uploadResume.data.extraction.provider} /{" "}
                {uploadResume.data.extraction.model}
              </Alert>
            )}
          {uploadResume.isSuccess && uploadResume.data.extraction?.status === "failed" && (
            <Alert severity="error">
              Resume stored, but AI extraction failed: {uploadResume.data.extraction.error_message}
            </Alert>
          )}
          {retryExtraction.isError && (
            <Alert severity="error">{getApiErrorMessage(retryExtraction.error)}</Alert>
          )}
          {retryExtraction.isSuccess &&
            retryExtraction.data.status !== "configuration_error" &&
            retryExtraction.data.status !== "failed" && (
            <Alert severity="success">
              Extraction retried successfully via {retryExtraction.data.provider} /{" "}
              {retryExtraction.data.model}
            </Alert>
          )}
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            <Button
              variant="contained"
              onClick={() => uploadResume.mutate()}
              disabled={!file || uploadResume.isPending || !form.consent_ai_processing}
            >
              {uploadResume.isPending ? "Uploading & extracting…" : "Upload & extract skills"}
            </Button>
            {(
              uploadResume.data?.extraction?.resume_document_id ||
              extractionQuery.data?.resume_document_id
            ) && (
              <Button
                variant="outlined"
                onClick={() => {
                  const resumeId =
                    uploadResume.data?.extraction?.resume_document_id ||
                    extractionQuery.data?.resume_document_id;
                  if (resumeId) retryExtraction.mutate(resumeId);
                }}
                disabled={retryExtraction.isPending || !form.consent_ai_processing}
              >
                {retryExtraction.isPending ? "Retrying…" : "Retry AI extraction"}
              </Button>
            )}
          </Stack>
        </Stack>
      </Section>

      <Section title="3. Review & confirm extracted skills">
        {!editablePayload && (
          <Alert severity="warning">No extraction available yet. Upload a resume first.</Alert>
        )}
        {editablePayload && (
          <Stack spacing={2}>
            {extractionQuery.data && (
              <Typography variant="body2" color="text.secondary">
                Prompt {extractionQuery.data.prompt_version} · Risk score{" "}
                {extractionQuery.data.hallucination_risk_score ?? "—"} · Tokens{" "}
                {extractionQuery.data.input_tokens ?? 0}/
                {extractionQuery.data.output_tokens ?? 0}
              </Typography>
            )}
            <TextField
              label="Extracted summary"
              multiline
              minRows={2}
              value={editablePayload.summary || ""}
              onChange={(e) =>
                setEditablePayload({ ...editablePayload, summary: e.target.value })
              }
              fullWidth
            />
            {editablePayload.skills.map((skill, index) => (
              <Stack
                key={`${skill.name}-${index}`}
                direction={{ xs: "column", md: "row" }}
                spacing={1}
                alignItems="flex-start"
              >
                <TextField
                  label="Skill"
                  value={skill.name}
                  onChange={(e) => updateSkill(index, { name: e.target.value })}
                  fullWidth
                />
                <TextField
                  select
                  label="Level"
                  value={skill.proficiency_level}
                  onChange={(e) => updateSkill(index, { proficiency_level: e.target.value })}
                  sx={{ minWidth: 160 }}
                >
                  {["awareness", "foundational", "working", "proficient", "advanced", "expert"].map(
                    (level) => (
                      <MenuItem key={level} value={level}>
                        {level}
                      </MenuItem>
                    ),
                  )}
                </TextField>
                <Button color="inherit" onClick={() => removeSkill(index)}>
                  Remove
                </Button>
              </Stack>
            ))}
            {confirmSkills.isError && (
              <Alert severity="error">{getApiErrorMessage(confirmSkills.error)}</Alert>
            )}
            {confirmSkills.isSuccess && (
              <Alert severity="success">Skills are confirmed.</Alert>
            )}
            <Button
              variant="contained"
              onClick={() => confirmSkills.mutate()}
              disabled={confirmSkills.isPending}
              sx={{ alignSelf: "flex-start" }}
            >
              Confirm skills
            </Button>
          </Stack>
        )}
      </Section>
    </Stack>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <GlassPanel>
      <Typography variant="h5" sx={{ mb: 2 }}>
        {title}
      </Typography>
      {children}
    </GlassPanel>
  );
}
