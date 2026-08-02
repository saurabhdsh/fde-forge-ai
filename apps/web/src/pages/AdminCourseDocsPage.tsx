import {
  Alert,
  Button,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileUp, Trash2 } from "lucide-react";
import { useRef, useState } from "react";

import { GlassPanel } from "../components/GlassPanel";
import { api, getApiErrorMessage, type ApiEnvelope } from "../lib/api";
import { useAuthStore } from "../store/authStore";
import { cx } from "../theme/tokens";

type EnrichmentDoc = {
  id: string;
  domain: string;
  title?: string | null;
  notes?: string | null;
  original_filename: string;
  file_extension: string;
  file_size_bytes: number;
  extraction_status: string;
  extraction_error?: string | null;
  extracted_chars: number;
  created_at: string;
};

const DOMAINS = [
  { id: "all", label: "All domains" },
  { id: "healthcare", label: "Healthcare" },
  { id: "life_sciences", label: "Life sciences" },
  { id: "technical", label: "Technical" },
];

export function AdminCourseDocsPage() {
  const qc = useQueryClient();
  const hasPermission = useAuthStore((s) => s.hasPermission);
  const user = useAuthStore((s) => s.user);
  const canManage =
    hasPermission("curriculum.create") || !!user?.is_super_admin;
  const fileRef = useRef<HTMLInputElement>(null);

  const [domain, setDomain] = useState("all");
  const [title, setTitle] = useState("");
  const [notes, setNotes] = useState("");

  const listQuery = useQuery({
    queryKey: ["course-enrichment-docs"],
    enabled: canManage,
    queryFn: async () => {
      const { data } = await api.get<ApiEnvelope<EnrichmentDoc[]>>(
        "/curriculum/enrichment-documents",
      );
      return data.data;
    },
  });

  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      const body = new FormData();
      body.append("file", file);
      body.append("domain", domain);
      if (title.trim()) body.append("title", title.trim());
      if (notes.trim()) body.append("notes", notes.trim());
      const { data } = await api.post<ApiEnvelope<EnrichmentDoc>>(
        "/curriculum/enrichment-documents",
        body,
        { headers: { "Content-Type": "multipart/form-data" }, timeout: 120000 },
      );
      return data.data;
    },
    onSuccess: () => {
      setTitle("");
      setNotes("");
      if (fileRef.current) fileRef.current.value = "";
      qc.invalidateQueries({ queryKey: ["course-enrichment-docs"] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/curriculum/enrichment-documents/${id}`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["course-enrichment-docs"] }),
  });

  if (!canManage) {
    return <Alert severity="warning">You need curriculum.create permission.</Alert>;
  }

  return (
    <Stack spacing={3}>
      <Stack spacing={0.5}>
        <Typography variant="overline" sx={{ color: cx.accent }}>
          Admin
        </Typography>
        <Typography variant="h2">Course source documents</Typography>
        <Typography sx={{ color: cx.fgDim, maxWidth: 760 }}>
          Upload PDF or Word docs that enrich AI-generated domain courses. Text is extracted and
          passed into course generation to sharpen content and add topics from your materials.
          Candidates who already generated a course can use{" "}
          <strong style={{ color: cx.fg }}>Regenerate (latest sources)</strong> on the Courses page
          after you upload new materials.
        </Typography>
      </Stack>

      <GlassPanel>
        <Stack spacing={2}>
          <Typography variant="h5">Upload enrichment document</Typography>
          <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
            <FormControl sx={{ minWidth: 200 }}>
              <InputLabel id="enrich-domain">Applies to</InputLabel>
              <Select
                labelId="enrich-domain"
                label="Applies to"
                value={domain}
                onChange={(e) => setDomain(e.target.value)}
              >
                {DOMAINS.map((d) => (
                  <MenuItem key={d.id} value={d.id}>
                    {d.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <TextField
              label="Title (optional)"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              fullWidth
            />
          </Stack>
          <TextField
            label="Notes (optional)"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            multiline
            minRows={2}
            fullWidth
          />
          <Stack direction="row" spacing={1.5} alignItems="center" flexWrap="wrap" useFlexGap>
            <Button
              variant="contained"
              startIcon={<FileUp size={16} />}
              component="label"
              disabled={uploadMutation.isPending}
            >
              {uploadMutation.isPending ? "Uploading & extracting…" : "Choose PDF / DOCX"}
              <input
                ref={fileRef}
                hidden
                type="file"
                accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) uploadMutation.mutate(file);
                }}
              />
            </Button>
            <Typography sx={{ color: cx.fgDim, fontSize: "0.82rem" }}>
              Max size matches org upload limit · text extracted immediately
            </Typography>
          </Stack>
          {uploadMutation.isError && (
            <Alert severity="error">{getApiErrorMessage(uploadMutation.error)}</Alert>
          )}
          {uploadMutation.isSuccess && (
            <Alert severity="success">
              Uploaded and extracted ({uploadMutation.data.extracted_chars} characters). New course
              generations for matching domains will use this source.
            </Alert>
          )}
        </Stack>
      </GlassPanel>

      <Stack spacing={1.5}>
        <Typography variant="h5">Active sources</Typography>
        {listQuery.isError && (
          <Alert severity="error">{getApiErrorMessage(listQuery.error)}</Alert>
        )}
        {(listQuery.data || []).length === 0 && !listQuery.isLoading && (
          <Alert severity="info">No enrichment documents yet. Upload a PDF or DOCX above.</Alert>
        )}
        {(listQuery.data || []).map((doc) => (
          <GlassPanel key={doc.id} sx={{ p: 2 }}>
            <Stack
              direction={{ xs: "column", md: "row" }}
              spacing={1.5}
              justifyContent="space-between"
              alignItems={{ md: "center" }}
            >
              <Stack spacing={0.35} sx={{ minWidth: 0 }}>
                <Typography sx={{ fontWeight: 700 }}>
                  {doc.title || doc.original_filename}
                </Typography>
                <Typography sx={{ color: cx.fgDim, fontSize: "0.8rem" }}>
                  {doc.original_filename} · {doc.domain.replace("_", " ")} ·{" "}
                  {Math.round(doc.file_size_bytes / 1024)} KB · {doc.extraction_status}
                  {doc.extracted_chars ? ` · ${doc.extracted_chars} chars` : ""}
                </Typography>
                {doc.notes && (
                  <Typography sx={{ color: cx.fgMuted, fontSize: "0.82rem" }}>{doc.notes}</Typography>
                )}
                {doc.extraction_error && (
                  <Typography sx={{ color: cx.danger, fontSize: "0.8rem" }}>
                    {doc.extraction_error}
                  </Typography>
                )}
              </Stack>
              <Button
                color="error"
                variant="outlined"
                startIcon={<Trash2 size={14} />}
                disabled={deleteMutation.isPending}
                onClick={() => deleteMutation.mutate(doc.id)}
              >
                Remove
              </Button>
            </Stack>
          </GlassPanel>
        ))}
        {deleteMutation.isError && (
          <Alert severity="error">{getApiErrorMessage(deleteMutation.error)}</Alert>
        )}
      </Stack>
    </Stack>
  );
}
