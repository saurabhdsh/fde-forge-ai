import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
const API_PREFIX = "/api/v1";

export type ApiEnvelope<T> = {
  data: T;
  meta: Record<string, unknown>;
  errors: Array<{ code: string; message: string; details?: Record<string, unknown> }>;
};

function getCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

function isAuthBootstrapUrl(url?: string): boolean {
  if (!url) return false;
  return (
    url.includes("/auth/login") ||
    url.includes("/auth/refresh") ||
    url.includes("/auth/me") ||
    url.includes("/auth/logout")
  );
}

export const api = axios.create({
  baseURL: `${API_URL}${API_PREFIX}`,
  withCredentials: true,
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use((config) => {
  const csrf = getCookie("csrf_token");
  if (csrf && config.method && ["post", "put", "patch", "delete"].includes(config.method)) {
    config.headers["X-CSRF-Token"] = csrf;
  }
  return config;
});

let refreshPromise: Promise<void> | null = null;

async function refreshSessionOnce(): Promise<void> {
  if (!refreshPromise) {
    refreshPromise = api
      .post("/auth/refresh")
      .then(() => undefined)
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<ApiEnvelope<unknown>>) => {
    const config = error.config as (InternalAxiosRequestConfig & { _retry?: boolean }) | undefined;
    const status = error.response?.status;

    // Never attempt token refresh for auth bootstrap endpoints, and never loop.
    if (status !== 401 || !config || config._retry || isAuthBootstrapUrl(config.url)) {
      return Promise.reject(error);
    }

    try {
      config._retry = true;
      await refreshSessionOnce();
      return api.request(config);
    } catch {
      return Promise.reject(error);
    }
  },
);

export function getApiErrorMessage(error: unknown, fallback = "Something went wrong"): string {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data as ApiEnvelope<unknown> | undefined;
    if (data?.errors?.length) {
      return data.errors[0].message;
    }
    return error.message || fallback;
  }
  if (error instanceof Error) return error.message;
  return fallback;
}

export { API_URL };
