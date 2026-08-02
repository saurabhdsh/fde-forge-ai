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
import { cx } from "../theme/tokens";
import type { AuditLog } from "../types";

export function AuditLogsPage() {
  const logsQuery = useQuery({
    queryKey: ["audit-logs"],
    queryFn: async () => {
      const { data } = await api.get<ApiEnvelope<AuditLog[]>>("/audit");
      return data.data;
    },
  });

  return (
    <Stack spacing={3}>
      <Stack spacing={0.5}>
        <Typography variant="overline" sx={{ color: cx.accent }}>
          Governance
        </Typography>
        <Typography variant="h2">Audit logs</Typography>
        <Typography sx={{ color: cx.fgDim }}>
          Append-only trail for authentication, user changes, uploads, and AI extractions.
        </Typography>
      </Stack>
      {logsQuery.isLoading && (
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
      {logsQuery.isError && <Alert severity="error">Unable to load audit logs.</Alert>}
      {logsQuery.data && logsQuery.data.length === 0 && (
        <Alert severity="info">No audit events yet.</Alert>
      )}
      {logsQuery.data && logsQuery.data.length > 0 && (
        <GlassPanel sx={{ p: 0, overflow: "hidden" }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Time</TableCell>
                <TableCell>Action</TableCell>
                <TableCell>Entity</TableCell>
                <TableCell>Actor</TableCell>
                <TableCell>Correlation</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {logsQuery.data.map((log) => (
                <TableRow key={log.id}>
                  <TableCell>{new Date(log.created_at).toLocaleString()}</TableCell>
                  <TableCell sx={{ color: cx.fg }}>{log.action}</TableCell>
                  <TableCell>
                    {log.entity_type}
                    {log.entity_id ? `:${log.entity_id.slice(0, 8)}` : ""}
                  </TableCell>
                  <TableCell>{log.actor_id?.slice(0, 8) || "—"}</TableCell>
                  <TableCell>{log.correlation_id?.slice(0, 8) || "—"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </GlassPanel>
      )}
    </Stack>
  );
}
