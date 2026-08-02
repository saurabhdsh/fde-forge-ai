import Editor, { type OnMount } from "@monaco-editor/react";
import { Box, Stack, Typography } from "@mui/material";
import { useCallback, useEffect, useRef, useState } from "react";

import { api, type ApiEnvelope } from "../lib/api";
import { cx } from "../theme/tokens";

export type SyntaxDiagnostic = {
  line: number;
  column: number;
  message: string;
  severity: string;
  source?: string;
};

type Monaco = Parameters<OnMount>[1];
type MonacoEditor = Parameters<OnMount>[0];

export function CodeEditor({
  value,
  onChange,
  language = "python",
  readOnly,
  minRows = 16,
  liveSyntax = true,
}: {
  value: string;
  onChange?: (next: string) => void;
  language?: string;
  readOnly?: boolean;
  minRows?: number;
  liveSyntax?: boolean;
}) {
  const editorRef = useRef<MonacoEditor | null>(null);
  const monacoRef = useRef<Monaco | null>(null);
  const timerRef = useRef<number | null>(null);
  const [diagnostics, setDiagnostics] = useState<SyntaxDiagnostic[]>([]);
  const [checking, setChecking] = useState(false);
  const [checkUnavailable, setCheckUnavailable] = useState(false);
  const height = Math.max(280, minRows * 18);

  const applyMarkers = useCallback((diags: SyntaxDiagnostic[]) => {
    const editor = editorRef.current;
    const monaco = monacoRef.current;
    if (!editor || !monaco) return;
    const model = editor.getModel();
    if (!model) return;
    monaco.editor.setModelMarkers(
      model,
      "fde-python",
      diags.map((d) => ({
        startLineNumber: Math.max(1, d.line),
        startColumn: Math.max(1, d.column),
        endLineNumber: Math.max(1, d.line),
        endColumn: Math.max(1, d.column) + 1,
        message: d.message,
        severity:
          d.severity === "warning"
            ? monaco.MarkerSeverity.Warning
            : monaco.MarkerSeverity.Error,
      })),
    );
  }, []);

  const runSyntaxCheck = useCallback(
    async (code: string) => {
      if (!liveSyntax || readOnly || (language || "python").toLowerCase() !== "python") {
        setDiagnostics([]);
        setCheckUnavailable(false);
        applyMarkers([]);
        return;
      }
      setChecking(true);
      try {
        const { data } = await api.post<
          ApiEnvelope<{ ok: boolean; diagnostics: SyntaxDiagnostic[] }>
        >("/coding-assessments/syntax-check", { code, language: "python" });
        const diags = data.data.diagnostics || [];
        setDiagnostics(diags);
        setCheckUnavailable(false);
        applyMarkers(diags);
      } catch {
        setCheckUnavailable(true);
        // Keep prior markers; still allow typing if API is briefly down
      } finally {
        setChecking(false);
      }
    },
    [applyMarkers, language, liveSyntax, readOnly],
  );

  useEffect(() => {
    if (timerRef.current) window.clearTimeout(timerRef.current);
    timerRef.current = window.setTimeout(() => {
      void runSyntaxCheck(value);
    }, 450);
    return () => {
      if (timerRef.current) window.clearTimeout(timerRef.current);
    };
  }, [value, runSyntaxCheck]);

  const onMount: OnMount = (editor, monaco) => {
    editorRef.current = editor;
    monacoRef.current = monaco;
    monaco.editor.defineTheme("fde-dark", {
      base: "vs-dark",
      inherit: true,
      rules: [
        { token: "comment", foreground: "6b7c8f", fontStyle: "italic" },
        { token: "string", foreground: "7dd3a7" },
        { token: "keyword", foreground: "7ec8f0" },
        { token: "number", foreground: "e8b84a" },
      ],
      colors: {
        "editor.background": "#0a0d14",
        "editor.foreground": "#d7e2ef",
        "editorLineNumber.foreground": "#5b6b7c",
        "editorCursor.foreground": "#5ec8f2",
        "editor.selectionBackground": "#1c3a4d",
        "editor.lineHighlightBackground": "#121821",
        "editorBracketMatch.background": "#234056",
        "editorBracketMatch.border": "#5ec8f2",
      },
    });
    monaco.editor.setTheme("fde-dark");
    void runSyntaxCheck(value);
  };

  const errorCount = diagnostics.filter((d) => d.severity === "error").length;
  const warnCount = diagnostics.filter((d) => d.severity === "warning").length;

  return (
    <Box
      sx={{
        borderRadius: 2,
        border: `1px solid ${cx.borderStrong}`,
        overflow: "hidden",
        bgcolor: "#0a0d14",
      }}
    >
      <Stack
        direction="row"
        justifyContent="space-between"
        alignItems="center"
        sx={{
          px: 1.5,
          py: 0.75,
          borderBottom: `1px solid ${cx.border}`,
        }}
      >
        <Typography
          sx={{
            color: cx.fgDim,
            fontSize: "0.72rem",
            letterSpacing: "0.04em",
            textTransform: "uppercase",
          }}
        >
          {language} playground · live syntax
        </Typography>
        <Typography sx={{ color: checkUnavailable ? cx.warn : cx.fgDim, fontSize: "0.72rem" }}>
          {checking
            ? "Checking syntax…"
            : checkUnavailable
              ? "Syntax service unreachable"
              : errorCount || warnCount
                ? `${errorCount} error(s) · ${warnCount} warning(s)`
                : "No syntax issues"}
        </Typography>
      </Stack>

      <Editor
        height={height}
        language={language === "py" ? "python" : language}
        value={value}
        onChange={(next) => onChange?.(next ?? "")}
        onMount={onMount}
        theme="fde-dark"
        options={{
          readOnly: !!readOnly,
          minimap: { enabled: false },
          fontSize: 13,
          fontFamily:
            'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace',
          lineNumbers: "on",
          scrollBeyondLastLine: false,
          automaticLayout: true,
          tabSize: 4,
          insertSpaces: true,
          wordWrap: "on",
          renderLineHighlight: "line",
          bracketPairColorization: { enabled: true },
          autoClosingBrackets: "languageDefined",
          matchBrackets: "always",
          padding: { top: 8, bottom: 8 },
          scrollbar: { verticalScrollbarSize: 10 },
        }}
        loading={
          <Box sx={{ p: 2, color: cx.fgDim, fontSize: "0.85rem" }}>Loading editor…</Box>
        }
      />

      <Box
        sx={{
          borderTop: `1px solid ${cx.border}`,
          bgcolor: "rgba(8,10,16,0.92)",
          maxHeight: 140,
          overflow: "auto",
          px: 1.5,
          py: 1,
        }}
      >
        <Typography
          sx={{
            color: cx.fgDim,
            fontSize: "0.68rem",
            letterSpacing: "0.05em",
            textTransform: "uppercase",
            mb: 0.75,
          }}
        >
          Problems
        </Typography>
        {!diagnostics.length ? (
          <Typography sx={{ color: checkUnavailable ? cx.warn : cx.success, fontSize: "0.8rem" }}>
            {checkUnavailable
              ? "Could not reach syntax-check API. Editor still works; retry by continuing to type."
              : "Syntax OK (compile check only — code is not executed)."}
          </Typography>
        ) : (
          <Stack spacing={0.5}>
            {diagnostics.map((d, i) => (
              <Box
                key={`${d.line}-${d.column}-${i}`}
                component="button"
                type="button"
                onClick={() => {
                  editorRef.current?.revealLineInCenter(d.line);
                  editorRef.current?.setPosition({ lineNumber: d.line, column: d.column });
                  editorRef.current?.focus();
                }}
                sx={{
                  appearance: "none",
                  border: 0,
                  background: "transparent",
                  textAlign: "left",
                  cursor: "pointer",
                  color: d.severity === "warning" ? cx.warn : cx.danger,
                  fontFamily: "ui-monospace, Menlo, Monaco, Consolas, monospace",
                  fontSize: "0.78rem",
                  p: 0,
                  "&:hover": { textDecoration: "underline" },
                }}
              >
                [{d.severity}] line {d.line}:{d.column} — {d.message}
              </Box>
            ))}
          </Stack>
        )}
      </Box>
    </Box>
  );
}
