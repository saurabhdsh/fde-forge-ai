import { api, API_URL } from "./api";

function getCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

/** Download assessment export (markdown or json) via authenticated blob request. */
export async function downloadAssessmentExport(opts: {
  path: string; // e.g. /assessments/{id}/export
  format?: "markdown" | "json";
  fallbackName: string;
}): Promise<void> {
  const format = opts.format || "markdown";
  const response = await api.get(opts.path, {
    params: { format },
    responseType: "blob",
  });
  const blob = response.data as Blob;
  const disposition = response.headers["content-disposition"] as string | undefined;
  let filename = opts.fallbackName;
  if (disposition) {
    const match = /filename="?([^"]+)"?/i.exec(disposition);
    if (match?.[1]) filename = match[1];
  }
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}

export { API_URL, getCookie };
