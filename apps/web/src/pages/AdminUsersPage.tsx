import {
  Alert,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  MenuItem,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Eye, KeyRound, Trash2 } from "lucide-react";
import { useState } from "react";

import { GlassPanel } from "../components/GlassPanel";
import { api, getApiErrorMessage, type ApiEnvelope } from "../lib/api";
import { useAuthStore } from "../store/authStore";
import { cx } from "../theme/tokens";
import type { UserOut } from "../types";

type RevealedPassword = {
  user_id: string;
  username: string;
  first_name: string;
  last_name: string;
  password: string;
};

export function AdminUsersPage() {
  const qc = useQueryClient();
  const me = useAuthStore((s) => s.user);
  const orgSlug = me?.organization_slug || "acme-health";
  const canManage = useAuthStore((s) => s.hasPermission("user.manage"));

  const [createdCreds, setCreatedCreds] = useState<{
    username: string;
    password: string;
    org: string;
  } | null>(null);
  const [revealed, setRevealed] = useState<RevealedPassword | null>(null);
  const [passwordTarget, setPasswordTarget] = useState<UserOut | null>(null);
  const [newPassword, setNewPassword] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<UserOut | null>(null);

  const [form, setForm] = useState({
    username: "",
    first_name: "",
    last_name: "",
    password: "ChangeMeLearner123!",
    role_codes: ["learner"],
  });

  const usersQuery = useQuery({
    queryKey: ["users"],
    queryFn: async () => {
      const { data } = await api.get<ApiEnvelope<UserOut[]>>("/users");
      return data.data;
    },
  });

  const createUser = useMutation({
    mutationFn: async () => {
      const { data } = await api.post<ApiEnvelope<UserOut>>("/users", form);
      return { user: data.data, password: form.password };
    },
    onSuccess: ({ user, password }) => {
      qc.invalidateQueries({ queryKey: ["users"] });
      setCreatedCreds({ username: user.username, password, org: orgSlug });
      setForm((f) => ({ ...f, username: "", first_name: "", last_name: "" }));
    },
  });

  const revealPassword = useMutation({
    mutationFn: async (userId: string) => {
      const { data } = await api.get<ApiEnvelope<RevealedPassword>>(
        `/users/${userId}/password`,
      );
      return data.data;
    },
    onSuccess: (data) => setRevealed(data),
  });

  const changePassword = useMutation({
    mutationFn: async () => {
      if (!passwordTarget) throw new Error("No user selected");
      const { data } = await api.patch<ApiEnvelope<UserOut>>(`/users/${passwordTarget.id}`, {
        password: newPassword,
      });
      return data.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["users"] });
      setPasswordTarget(null);
      setNewPassword("");
    },
  });

  const deleteUser = useMutation({
    mutationFn: async () => {
      if (!deleteTarget) throw new Error("No user selected");
      await api.delete(`/users/${deleteTarget.id}`);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["users"] });
      setDeleteTarget(null);
    },
  });

  return (
    <Stack spacing={3}>
      <Stack spacing={0.5}>
        <Typography variant="overline" sx={{ color: cx.accent }}>
          Administration
        </Typography>
        <Typography variant="h2">User Management</Typography>
        <Typography sx={{ color: cx.fgDim, maxWidth: 720 }}>
          Create, update passwords, reveal credentials, and delete candidates. Your personal
          candidate profile remains under <strong style={{ color: cx.fg }}>My profile</strong>.
        </Typography>
      </Stack>

      <GlassPanel>
        <Typography variant="h5" sx={{ mb: 2 }}>
          Create candidate
        </Typography>
        <Stack spacing={2} maxWidth={520}>
          <TextField
            label="Username"
            value={form.username}
            onChange={(e) => setForm((f) => ({ ...f, username: e.target.value }))}
            helperText="Login name — no email needed"
          />
          <TextField
            label="First name"
            value={form.first_name}
            onChange={(e) => setForm((f) => ({ ...f, first_name: e.target.value }))}
          />
          <TextField
            label="Last name"
            value={form.last_name}
            onChange={(e) => setForm((f) => ({ ...f, last_name: e.target.value }))}
          />
          <TextField
            label="Initial password"
            value={form.password}
            onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
          />
          <TextField
            select
            label="Role"
            value={form.role_codes[0]}
            onChange={(e) => setForm((f) => ({ ...f, role_codes: [e.target.value] }))}
          >
            {["learner", "mentor", "evaluator", "academy_admin"].map((role) => (
              <MenuItem key={role} value={role}>
                {role === "learner" ? "candidate (learner)" : role}
              </MenuItem>
            ))}
          </TextField>
          {createUser.isError && (
            <Alert severity="error">{getApiErrorMessage(createUser.error)}</Alert>
          )}
          {createdCreds && (
            <Alert severity="success">
              Created <strong>{createdCreds.username}</strong> / <strong>{createdCreds.password}</strong>{" "}
              · org <strong>{createdCreds.org}</strong>
            </Alert>
          )}
          <Button
            variant="contained"
            onClick={() => createUser.mutate()}
            disabled={
              createUser.isPending || !form.username || !form.first_name || !form.last_name
            }
            sx={{ alignSelf: "flex-start" }}
          >
            {createUser.isPending ? "Creating…" : "Create candidate"}
          </Button>
        </Stack>
      </GlassPanel>

      {(revealPassword.isError || changePassword.isError || deleteUser.isError) && (
        <Alert severity="error">
          {getApiErrorMessage(
            revealPassword.error || changePassword.error || deleteUser.error,
          )}
        </Alert>
      )}
      {changePassword.isSuccess && (
        <Alert severity="success">Password updated and stored for admin recovery.</Alert>
      )}

      <GlassPanel sx={{ p: 0, overflow: "hidden" }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell>
              <TableCell>Username</TableCell>
              <TableCell>Roles</TableCell>
              <TableCell>Status</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {(usersQuery.data || []).map((user) => {
              const isSelf = user.id === me?.id;
              return (
                <TableRow key={user.id}>
                  <TableCell sx={{ color: cx.fg }}>
                    {user.first_name} {user.last_name}
                    {isSelf ? " (you)" : ""}
                  </TableCell>
                  <TableCell>{user.username}</TableCell>
                  <TableCell>{user.roles.join(", ")}</TableCell>
                  <TableCell>{user.status}</TableCell>
                  <TableCell align="right">
                    {canManage && (
                      <Stack direction="row" spacing={0.5} justifyContent="flex-end">
                        <Button
                          size="small"
                          startIcon={<Eye size={14} />}
                          onClick={() => revealPassword.mutate(user.id)}
                          sx={{ color: cx.accent }}
                        >
                          Reveal
                        </Button>
                        <Button
                          size="small"
                          startIcon={<KeyRound size={14} />}
                          onClick={() => {
                            setPasswordTarget(user);
                            setNewPassword("");
                          }}
                          sx={{ color: cx.fgMuted }}
                        >
                          Password
                        </Button>
                        <Button
                          size="small"
                          startIcon={<Trash2 size={14} />}
                          disabled={isSelf}
                          onClick={() => setDeleteTarget(user)}
                          sx={{ color: isSelf ? cx.fgDim : cx.danger }}
                        >
                          Delete
                        </Button>
                      </Stack>
                    )}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </GlassPanel>

      <Dialog open={!!revealed} onClose={() => setRevealed(null)} fullWidth maxWidth="xs">
        <DialogTitle>Password</DialogTitle>
        <DialogContent>
          {revealed && (
            <Stack spacing={1.5} sx={{ pt: 1 }}>
              <Typography sx={{ color: cx.fgMuted }}>
                {revealed.first_name} {revealed.last_name} · {revealed.username}
              </Typography>
              <GlassPanel sx={{ p: 2 }}>
                <Typography variant="overline">Password</Typography>
                <Typography
                  sx={{
                    mt: 0.75,
                    fontFamily: "ui-monospace, monospace",
                    fontSize: "1.1rem",
                    color: cx.accent,
                    wordBreak: "break-all",
                  }}
                >
                  {revealed.password}
                </Typography>
              </GlassPanel>
            </Stack>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRevealed(null)}>Close</Button>
          {revealed && (
            <Button
              variant="contained"
              onClick={() => navigator.clipboard.writeText(revealed.password)}
            >
              Copy
            </Button>
          )}
        </DialogActions>
      </Dialog>

      <Dialog
        open={!!passwordTarget}
        onClose={() => setPasswordTarget(null)}
        fullWidth
        maxWidth="xs"
      >
        <DialogTitle>Change password</DialogTitle>
        <DialogContent>
          <Typography sx={{ color: cx.fgMuted, mb: 2, mt: 1 }}>
            {passwordTarget?.first_name} {passwordTarget?.last_name} · {passwordTarget?.username}
          </Typography>
          <TextField
            label="New password"
            type="text"
            fullWidth
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            helperText="Minimum 8 characters"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPasswordTarget(null)}>Cancel</Button>
          <Button
            variant="contained"
            disabled={newPassword.length < 8 || changePassword.isPending}
            onClick={() => changePassword.mutate()}
          >
            Save password
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={!!deleteTarget} onClose={() => setDeleteTarget(null)} fullWidth maxWidth="xs">
        <DialogTitle>Delete user</DialogTitle>
        <DialogContent>
          <Typography sx={{ mt: 1, color: cx.fgMuted }}>
            Permanently delete{" "}
            <strong style={{ color: cx.fg }}>
              {deleteTarget?.first_name} {deleteTarget?.last_name}
            </strong>{" "}
            ({deleteTarget?.username})? This cannot be undone.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteTarget(null)}>Cancel</Button>
          <Button
            variant="contained"
            color="error"
            disabled={deleteUser.isPending}
            onClick={() => deleteUser.mutate()}
          >
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </Stack>
  );
}
