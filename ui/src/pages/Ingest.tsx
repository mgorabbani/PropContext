import { useEffect, useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  fetchIncremental,
  runSimIngest,
  type SimDay,
  type SimIngestResponse,
  type SimItem,
} from "../api";
import { cn } from "../lib/cn";

type Kind = "email" | "invoice" | "bank";
type Mode = "isolated" | "live";

const KIND_LABELS: Record<Kind, string> = {
  email: "Emails",
  invoice: "Invoices",
  bank: "Bank tx",
};

export function IngestPage() {
  const [days, setDays] = useState<SimDay[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [day, setDay] = useState<number | null>(null);
  const [kind, setKind] = useState<Kind>("email");
  const [itemId, setItemId] = useState<string | null>(null);
  const [mode, setMode] = useState<Mode>("isolated");
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<SimIngestResponse | null>(null);
  const [activeFile, setActiveFile] = useState<string | null>(null);

  useEffect(() => {
    fetchIncremental()
      .then((d) => {
        setDays(d);
        if (d.length > 0) setDay(d[d.length - 1].day);
      })
      .catch((e) => setError(String(e)));
  }, []);

  const currentDay = useMemo(
    () => days?.find((d) => d.day === day) ?? null,
    [days, day],
  );

  const items: SimItem[] = useMemo(() => {
    if (!currentDay) return [];
    if (kind === "email") return currentDay.emails;
    if (kind === "invoice") return currentDay.invoices;
    return currentDay.bank;
  }, [currentDay, kind]);

  useEffect(() => {
    if (items.length === 0) {
      setItemId(null);
      return;
    }
    if (!itemId || !items.some((i) => i.id === itemId)) {
      setItemId(items[0].id);
    }
  }, [items, itemId]);

  useEffect(() => {
    if (!result) {
      setActiveFile(null);
      return;
    }
    setActiveFile(result.files[0]?.path ?? null);
  }, [result]);

  async function handleRun() {
    if (!day || !itemId) return;
    setRunning(true);
    setError(null);
    setResult(null);
    try {
      const res = await runSimIngest({ day, kind, id: itemId, mode });
      setResult(res);
    } catch (e) {
      setError(String(e));
    } finally {
      setRunning(false);
    }
  }

  const activeContent =
    result?.files.find((f) => f.path === activeFile)?.content ?? "";

  return (
    <div className="flex h-screen flex-col bg-[var(--color-bg)] text-[var(--color-fg)]">
      <header className="glass flex h-12 shrink-0 items-center gap-3 border-b border-[var(--color-border)] px-4">
        <a
          href="/"
          className="font-display text-[14px] font-medium text-[var(--color-ink-50)] hover:text-[var(--color-accent)]"
        >
          ← Buena Wiki
        </a>
        <span className="text-[11px] uppercase tracking-[0.18em] text-[var(--color-fg-muted)]">
          Simulate ingest
        </span>
      </header>

      <div className="flex min-h-0 flex-1">
        <aside className="flex w-[360px] shrink-0 flex-col border-r border-[var(--color-border)] bg-[var(--color-bg)]/40">
          <div className="border-b border-[var(--color-border)] px-3 py-3">
            <Field label="Day">
              <select
                value={day ?? ""}
                onChange={(e) => setDay(Number(e.target.value))}
                disabled={!days || days.length === 0}
                className="h-7 w-full appearance-none rounded-md border border-[var(--color-border-2)] bg-[var(--color-surface)] px-2 font-mono text-[12px] text-[var(--color-fg)]"
              >
                {(days ?? []).map((d) => (
                  <option key={d.day} value={d.day}>
                    day-{String(d.day).padStart(2, "0")}
                    {d.content_date ? `  ·  ${d.content_date}` : ""}
                  </option>
                ))}
              </select>
            </Field>
            <div className="mt-2 flex gap-1">
              {(Object.keys(KIND_LABELS) as Kind[]).map((k) => (
                <button
                  key={k}
                  onClick={() => setKind(k)}
                  className={cn(
                    "flex-1 rounded-md border px-2 py-1 font-mono text-[11px] uppercase tracking-wide transition-colors",
                    kind === k
                      ? "border-[var(--color-accent-dim)] bg-[var(--color-surface)] text-[var(--color-accent)]"
                      : "border-[var(--color-border-2)] bg-[var(--color-bg)] text-[var(--color-fg-muted)] hover:text-[var(--color-fg)]",
                  )}
                >
                  {KIND_LABELS[k]} ({currentDay ? currentDay[k === "bank" ? "bank" : k === "invoice" ? "invoices" : "emails"].length : 0})
                </button>
              ))}
            </div>
          </div>

          <div className="min-h-0 flex-1 overflow-auto px-1.5 py-2">
            {items.length === 0 ? (
              <p className="px-3 py-6 text-center text-[12px] text-[var(--color-fg-muted)]">
                No items.
              </p>
            ) : (
              items.map((it) => (
                <button
                  key={it.id}
                  onClick={() => setItemId(it.id)}
                  className={cn(
                    "mb-1 block w-full rounded-md border px-2.5 py-2 text-left transition-colors",
                    itemId === it.id
                      ? "border-[var(--color-accent-dim)] bg-[var(--color-surface)]"
                      : "border-transparent hover:border-[var(--color-border-2)] hover:bg-[var(--color-surface)]/60",
                  )}
                >
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-[10.5px] text-[var(--color-accent)]">
                      {it.id}
                    </span>
                  </div>
                  <div className="mt-0.5 line-clamp-1 text-[12.5px] font-medium text-[var(--color-fg)]">
                    {it.label}
                  </div>
                  <div className="mt-0.5 line-clamp-2 text-[11px] text-[var(--color-fg-muted)]">
                    {it.detail}
                  </div>
                </button>
              ))
            )}
          </div>

          <div className="border-t border-[var(--color-border)] px-3 py-3">
            <Field label="Mode">
              <div className="flex gap-1">
                {(["isolated", "live"] as Mode[]).map((m) => (
                  <button
                    key={m}
                    onClick={() => setMode(m)}
                    className={cn(
                      "flex-1 rounded-md border px-2 py-1 font-mono text-[11px] transition-colors",
                      mode === m
                        ? "border-[var(--color-accent-dim)] bg-[var(--color-surface)] text-[var(--color-accent)]"
                        : "border-[var(--color-border-2)] bg-[var(--color-bg)] text-[var(--color-fg-muted)] hover:text-[var(--color-fg)]",
                    )}
                  >
                    {m}
                  </button>
                ))}
              </div>
              <p className="mt-1 text-[10.5px] text-[var(--color-fg-muted)]">
                {mode === "isolated"
                  ? "Fresh tmp wiki per run. Real Gemini, no live mutation."
                  : "Writes to wiki/LIE-001 + commits."}
              </p>
            </Field>
            <button
              onClick={handleRun}
              disabled={!itemId || running}
              className={cn(
                "mt-3 w-full rounded-md border px-3 py-2 font-mono text-[12px] font-medium transition-colors",
                running
                  ? "border-[var(--color-border-2)] bg-[var(--color-surface)] text-[var(--color-fg-muted)]"
                  : "border-[var(--color-accent)] bg-[var(--color-accent)] text-[#0b0b0a] hover:opacity-90",
                !itemId && "cursor-not-allowed opacity-50",
              )}
            >
              {running ? "Running…" : `▶ Run ingest (${itemId ?? "—"})`}
            </button>
          </div>
        </aside>

        <main className="flex min-w-0 flex-1 flex-col">
          {error && (
            <div className="border-b border-red-500/40 bg-red-500/10 px-4 py-2 text-[12px] text-red-400">
              {error}
            </div>
          )}
          {!result && !running && !error && (
            <div className="grid flex-1 place-items-center text-[12.5px] text-[var(--color-fg-muted)]">
              Pick a day + item, then run. Uses real Gemini ({"gemini-2.5-flash-lite"} → {"gemini-2.5-pro"}).
            </div>
          )}
          {running && (
            <div className="grid flex-1 place-items-center text-[12.5px] text-[var(--color-fg-muted)]">
              Calling supervisor → classify → resolve → extract → patch → commit…
            </div>
          )}
          {result && (
            <ResultView
              result={result}
              activeFile={activeFile}
              onActiveFile={setActiveFile}
              activeContent={activeContent}
            />
          )}
        </main>
      </div>
    </div>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span className="block pb-1 font-mono text-[10.5px] uppercase tracking-[0.2em] text-[var(--color-fg-dim)]">
        {label}
      </span>
      {children}
    </label>
  );
}

function ResultView({
  result,
  activeFile,
  onActiveFile,
  activeContent,
}: {
  result: SimIngestResponse;
  activeFile: string | null;
  onActiveFile: (p: string) => void;
  activeContent: string;
}) {
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="grid grid-cols-2 gap-x-6 gap-y-1 border-b border-[var(--color-border)] px-4 py-3 font-mono text-[11.5px]">
        <Stat label="status" value={result.status} accent />
        <Stat label="duration" value={`${result.duration_ms} ms`} />
        <Stat label="applied_ops" value={String(result.applied_ops)} />
        <Stat
          label="provider"
          value={`${result.provider} (${result.fast_model} → ${result.smart_model})`}
        />
        <Stat
          label="commit"
          value={result.commit_sha ? result.commit_sha.slice(0, 10) : "—"}
        />
        <Stat label="idempotent" value={String(result.idempotent)} />
        {result.classification && (
          <>
            <Stat
              label="classify.signal"
              value={String(result.classification.signal)}
              accent={result.classification.signal}
            />
            <Stat
              label="classify"
              value={`${result.classification.category}  ·  ${result.classification.priority}  ·  conf=${result.classification.confidence}`}
            />
          </>
        )}
        <Stat label="workspace" value={result.workspace} colSpan={2} mono />
      </div>

      <div className="flex min-h-0 flex-1">
        <aside className="flex w-[260px] shrink-0 flex-col border-r border-[var(--color-border)]">
          <div className="border-b border-[var(--color-border)] px-3 py-2 font-mono text-[10.5px] uppercase tracking-[0.2em] text-[var(--color-fg-dim)]">
            Touched files ({result.files.length})
          </div>
          <div className="min-h-0 flex-1 overflow-auto px-1.5 py-1.5">
            {result.files.map((f) => (
              <button
                key={f.path}
                onClick={() => onActiveFile(f.path)}
                className={cn(
                  "block w-full truncate rounded px-2 py-1 text-left font-mono text-[11.5px]",
                  activeFile === f.path
                    ? "bg-[var(--color-surface)] text-[var(--color-accent)]"
                    : "text-[var(--color-fg-muted)] hover:bg-[var(--color-surface)]/60 hover:text-[var(--color-fg)]",
                )}
              >
                {f.path}
              </button>
            ))}
          </div>
          {result.git_log.length > 0 && (
            <div className="border-t border-[var(--color-border)] px-3 py-2">
              <div className="pb-1 font-mono text-[10.5px] uppercase tracking-[0.2em] text-[var(--color-fg-dim)]">
                git log
              </div>
              <ul className="space-y-0.5 font-mono text-[10.5px] text-[var(--color-fg-muted)]">
                {result.git_log.map((ln) => (
                  <li key={ln} className="truncate">
                    {ln}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </aside>

        <section className="prose min-w-0 flex-1 overflow-auto px-6 py-4 text-[13.5px] dark:prose-invert">
          {activeFile ? (
            <>
              <div className="mb-3 font-mono text-[10.5px] uppercase tracking-[0.2em] text-[var(--color-fg-dim)]">
                {activeFile}
              </div>
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {activeContent}
              </ReactMarkdown>
            </>
          ) : (
            <p className="text-[var(--color-fg-muted)]">No files touched.</p>
          )}
        </section>
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
  accent,
  mono,
  colSpan,
}: {
  label: string;
  value: string;
  accent?: boolean;
  mono?: boolean;
  colSpan?: number;
}) {
  return (
    <div className={colSpan === 2 ? "col-span-2" : ""}>
      <span className="text-[var(--color-fg-dim)]">{label}</span>{" "}
      <span
        className={cn(
          accent && "text-[var(--color-accent)]",
          mono && "break-all",
        )}
      >
        {value}
      </span>
    </div>
  );
}
