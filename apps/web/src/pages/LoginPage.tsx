import {
  Alert,
  Box,
  Button,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { z } from "zod";

import { GlassPanel } from "../components/GlassPanel";
import { api, getApiErrorMessage, type ApiEnvelope } from "../lib/api";
import { useAuthStore } from "../store/authStore";
import { cx } from "../theme/tokens";
import type { AuthSession } from "../types";

const schema = z.object({
  username: z.string().min(1, "Username is required"),
  password: z.string().min(8),
  organization_slug: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

export function LoginPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const setUser = useAuthStore((s) => s.setUser);
  const appName = import.meta.env.VITE_APP_NAME || "FDE Forge AI";
  const tagline =
    import.meta.env.VITE_APP_TAGLINE ||
    "Transform AI Engineers into Customer-Ready Forward Deployed Engineers.";

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      username: "",
      password: "",
      organization_slug: "acme-health",
    },
  });

  const loginMutation = useMutation({
    mutationFn: async (values: FormValues) => {
      const { data } = await api.post<ApiEnvelope<AuthSession>>("/auth/login", {
        username: values.username,
        password: values.password,
        organization_slug: values.organization_slug || null,
      });
      return data.data;
    },
    onSuccess: async (session) => {
      setUser(session.user);
      await queryClient.setQueryData(["session"], session);
      const isLearner = session.user.roles.includes("learner");
      navigate(isLearner ? "/onboarding" : "/");
    },
  });

  return (
    <Box
      sx={{
        minHeight: "100vh",
        position: "relative",
        overflow: "hidden",
        background: cx.void,
      }}
    >
      {/* Ambient mesh */}
      <Box
        sx={{
          pointerEvents: "none",
          position: "absolute",
          inset: 0,
          background: `
            radial-gradient(900px 520px at 8% 0%, rgba(94,200,242,0.14), transparent 55%),
            radial-gradient(700px 480px at 92% 12%, rgba(155,139,212,0.12), transparent 50%),
            radial-gradient(600px 400px at 50% 100%, rgba(62,207,155,0.06), transparent 45%)
          `,
        }}
      />

      {/* TCS logo — login only, top left, prominent */}
      <Box
        component={motion.div}
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        sx={{
          position: "absolute",
          top: { xs: 20, md: 28 },
          left: { xs: 20, md: 36 },
          zIndex: 2,
        }}
      >
        <Box
          component="img"
          src="/tcs-logo-white.svg"
          alt="TCS"
          sx={{
            height: { xs: 96, sm: 120, md: 148 },
            width: "auto",
            display: "block",
            objectFit: "contain",
            filter: "drop-shadow(0 10px 28px rgba(0,0,0,0.5))",
          }}
        />
      </Box>

      <Box
        sx={{
          minHeight: "100vh",
          display: "grid",
          placeItems: "center",
          px: 2,
          py: 8,
          position: "relative",
          zIndex: 1,
        }}
      >
        <Box
          component={motion.div}
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.05 }}
          sx={{ width: "100%", maxWidth: 440 }}
        >
          <GlassPanel hero>
            <Stack spacing={3}>
              <Box>
                <Typography variant="overline" sx={{ color: cx.accent, display: "block", mb: 1.25 }}>
                  Sign in
                </Typography>
                <Typography variant="h2" sx={{ mb: 1 }}>
                  {appName}
                </Typography>
                <Typography sx={{ color: cx.fgDim, fontSize: "0.875rem", lineHeight: 1.55 }}>
                  {tagline}
                </Typography>
              </Box>

              <Box
                sx={{
                  px: 1.5,
                  py: 1.25,
                  borderRadius: 2,
                  border: `1px solid ${cx.border}`,
                  bgcolor: "rgba(255,255,255,0.02)",
                }}
              >
                <Typography sx={{ color: cx.fgMuted, fontSize: "0.78rem", lineHeight: 1.5 }}>
                  Candidates: complete your profile and resume after sign-in. Admins: manage users
                  under User Management — your own candidate journey stays under My profile.
                </Typography>
              </Box>

              {loginMutation.isError && (
                <Alert severity="error">{getApiErrorMessage(loginMutation.error)}</Alert>
              )}

              <Stack
                component="form"
                spacing={2}
                onSubmit={handleSubmit((values) => loginMutation.mutate(values))}
              >
                <TextField
                  label="Username"
                  autoComplete="username"
                  placeholder="Saurabh"
                  {...register("username")}
                  error={!!errors.username}
                  helperText={errors.username?.message}
                  fullWidth
                />
                <TextField
                  label="Password"
                  type="password"
                  autoComplete="current-password"
                  {...register("password")}
                  error={!!errors.password}
                  helperText={errors.password?.message}
                  fullWidth
                />
                <TextField
                  label="Organization slug"
                  {...register("organization_slug")}
                  helperText="Provided by your admin (e.g. acme-health)"
                  fullWidth
                />
                <Button
                  type="submit"
                  variant="contained"
                  size="large"
                  disabled={loginMutation.isPending}
                  sx={{ mt: 0.5, py: 1.2 }}
                >
                  {loginMutation.isPending ? "Signing in…" : "Sign in to your workspace"}
                </Button>
              </Stack>
            </Stack>
          </GlassPanel>
        </Box>
      </Box>
    </Box>
  );
}
