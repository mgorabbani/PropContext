import { useEffect, useMemo, useRef, useState } from "react";
import { ChevronRight, Send, Sparkles } from "lucide-react";
import { askStream } from "../api";
import type { AskStep, AskUsage } from "../api";
import { cn } from "../lib/cn";

type Props = {
  lie: string;
  onResolved: (path: string) => void;
};

type Entry = {
  id: number;
  question: string;
  answer: string | null;
  path?: string;
  status: "pending" | "ok" | "empty" | "error";
  usage?: AskUsage;
  steps?: AskStep[];
};

function fmt(n: number): string {
  if (n >= 1000) return `${(n / 1000).toFixed(n >= 10000 ? 0 : 1)}k`;
  return String(n);
}

function isUsefulPath(path: string | undefined): path is string {
  if (!path) return false;
  const tail = path.split("/").pop() ?? path;
  return tail !== "index.md";
}

const SUGGESTIONS = [
  "Wer ist der aktuelle Hausmeister?",
  "Welche offenen Rechnungen gibt es?",
  "List all Dienstleister with active contracts",
  "Show the last 5 events on the timeline",
  "Any pending Mahnungen or overdue payments?",
];

export function Query({ lie, onResolved }: Props) {
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const [entries, setEntries] = useState<Entry[]>([]);
  const [unavailable, setUnavailable] = useState(false);
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const idRef = useRef(0);

  useEffect(() => {
    setEntries([]);
  }, [lie]);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [entries, busy]);

  async function run(question: string) {
    if (!question || busy) return;
    setQ("");
    const history = entries
      .filter((x) => x.status === "ok" && x.answer)
      .map((x) => ({ question: x.question, answer: x.answer as string }));
    const id = ++idRef.current;
    setEntries((e) => [
      ...e,
      { id, question, answer: null, status: "pending", steps: [] },
    ]);
    setBusy(true);
    await askStream(question, lie, history, {
      onStep: (step) => {
        setEntries((e) =>
          e.map((x) =>
            x.id === id ? { ...x, steps: [...(x.steps ?? []), step] } : x,
          ),
        );
      },
      onResponse: (data) => {
        const { answer, path, usage, steps } = data;
        const usefulPath = isUsefulPath(path) ? path : undefined;
        const fullPath = usefulPath ? `${lie}/${usefulPath}` : undefined;
        if (fullPath) onResolved(fullPath);
        setEntries((e) =>
          e.map((x) => {
            if (x.id !== id) return x;
            const base = { ...x, usage, steps: steps ?? x.steps } as Entry;
            if (answer) {
              return { ...base, answer, path: fullPath, status: "ok" };
            }
            if (fullPath) {
              return {
                ...base,
                answer: `Opened ${fullPath}`,
                path: fullPath,
                status: "ok",
              };
            }
            return {
              ...base,
              answer:
                "The model didn't find an answer in this property's wiki. Try rephrasing or asking about a specific page.",
              status: "empty",
            };
          }),
        );
      },
      onError: (err) => {
        const isMissing = err.status === 404;
        if (isMissing) setUnavailable(true);
        setEntries((e) =>
          e.map((x) =>
            x.id === id
              ? {
                  ...x,
                  answer: isMissing
                    ? "Ask endpoint not available on this server."
                    : `Request failed (${err.status}).`,
                  status: "error",
                }
              : x,
          ),
        );
      },
    });
    setBusy(false);
  }

  async function submit() {
    await run(q.trim());
  }

  async function pickSuggestion(s: string) {
    await run(s);
  }

  const hasEntries = entries.length > 0;
  const totals = useMemo(() => {
    return entries.reduce(
      (acc, e) => {
        if (!e.usage) return acc;
        return {
          input: acc.input + e.usage.input_tokens,
          output: acc.output + e.usage.output_tokens,
          cache_read: acc.cache_read + e.usage.cache_read_input_tokens,
          cache_create: acc.cache_create + e.usage.cache_creation_input_tokens,
        };
      },
      { input: 0, output: 0, cache_read: 0, cache_create: 0 },
    );
  }, [entries]);

  return (
    <aside className="flex h-full min-w-0 flex-col border-l border-[var(--color-border)] bg-[var(--color-bg)]/40">
      <div className="glass sticky top-0 z-10 flex h-11 items-center justify-between gap-2 border-b border-[var(--color-border)] px-4">
        <div className="flex items-center gap-2">
          <Sparkles className="h-3.5 w-3.5 text-[var(--color-accent)]" />
          <span className="font-mono text-[10.5px] uppercase tracking-[0.2em] text-[var(--color-fg-muted)]">
            Ask the wiki
          </span>
        </div>
        <div className="flex items-center gap-2">
          {hasEntries && (totals.input > 0 || totals.output > 0) && (
            <span
              title={`session totals — in ${totals.input} (cache read ${totals.cache_read}, write ${totals.cache_create}) · out ${totals.output}`}
              className="rounded border border-[var(--color-border-2)] bg-[var(--color-surface)]/40 px-1.5 py-px font-mono text-[9.5px] uppercase tracking-wider text-[var(--color-fg-dim)]"
            >
              {fmt(totals.input)} in · {fmt(totals.output)} out
            </span>
          )}
          {unavailable ? (
            <span className="rounded border border-[var(--color-border)] px-1.5 py-px font-mono text-[9.5px] uppercase tracking-wider text-[var(--color-fg-dim)]">
              soon
            </span>
          ) : hasEntries ? (
            <button
              onClick={() => setEntries([])}
              className="font-mono text-[10px] uppercase tracking-[0.18em] text-[var(--color-fg-dim)] hover:text-[var(--color-fg)]"
            >
              Clear
            </button>
          ) : null}
        </div>
      </div>

      <div ref={scrollRef} className="min-h-0 flex-1 overflow-auto px-4 py-5">
        {!hasEntries && !busy && (
          <EmptyAsk
            onPick={(s) => void pickSuggestion(s)}
            disabled={busy || unavailable}
          />
        )}
        {hasEntries && (
          <div className="space-y-6">
            {entries.map((e) => (
              <div key={e.id} className="space-y-4 fade-up">
                <div className="flex justify-end">
                  <div className="max-w-[85%] rounded-2xl border border-[var(--color-border-2)] bg-[var(--color-surface)]/70 px-3.5 py-2 text-[16px] leading-relaxed text-[var(--color-fg)]">
                    {e.question}
                  </div>
                </div>
                {e.status === "pending" ? (
                  <div className="space-y-2">
                    {e.steps && e.steps.length > 0 && (
                      <LiveTrace
                        steps={e.steps}
                        onPickPath={(p) => onResolved(`${lie}/${p}`)}
                      />
                    )}
                    <div className="flex items-center gap-1.5 text-[16px] text-[var(--color-fg-muted)]">
                      <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-[var(--color-accent)]" />
                      thinking...
                    </div>
                  </div>
                ) : (
                  <div className="space-y-2">
                    {e.steps && e.steps.length > 0 && (
                      <ThinkingTrace
                        steps={e.steps}
                        onPickPath={(p) => onResolved(`${lie}/${p}`)}
                      />
                    )}
                    <div
                      className={cn(
                        "whitespace-pre-wrap text-[16px] leading-relaxed",
                        e.status === "ok" && "text-[var(--color-fg)]",
                        e.status === "empty" && "text-[var(--color-fg-muted)]",
                        e.status === "error" && "text-red-500",
                      )}
                    >
                      {e.answer}
                      {e.path && (
                        <div className="mt-2">
                          <button
                            onClick={() => onResolved(e.path!)}
                            className="font-mono text-[11px] text-[var(--color-accent)] hover:underline"
                          >
                            → {e.path.split("/").slice(1).join("/") || e.path}
                          </button>
                        </div>
                      )}
                    </div>
                    {e.usage && <UsageBadge usage={e.usage} />}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="sticky bottom-0 border-t border-[var(--color-border)] bg-[var(--color-surface)]/60 backdrop-blur-sm px-3 py-3">
        <div
          className={cn(
            "flex items-center gap-2 rounded-lg border bg-[var(--color-bg)] p-1.5 transition-colors",
            "border-[var(--color-border-2)] focus-within:border-[var(--color-accent-dim)]",
            unavailable && "opacity-60",
          )}
        >
          <input
            className="flex-1 bg-transparent px-2 py-1 text-[14px] text-[var(--color-fg)] placeholder:text-[var(--color-fg-dim)] outline-none"
            value={q}
            placeholder={
              unavailable
                ? "Ask endpoint coming soon..."
                : "Ask about this property..."
            }
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") void submit();
            }}
            disabled={busy || unavailable}
          />
          <button
            onClick={() => void submit()}
            disabled={busy || unavailable || !q.trim()}
            className={cn(
              "flex h-7 items-center gap-1.5 rounded-md px-3 text-[12px] font-medium transition-colors",
              "bg-[#d4ff3c] text-[#0b0b0a]",
              "hover:bg-[var(--color-accent-soft)] disabled:opacity-40 disabled:cursor-not-allowed disabled:bg-[var(--color-surface)] disabled:text-[var(--color-fg-muted)]",
            )}
          >
            <Send className="h-3 w-3" strokeWidth={2.4} />
            {busy ? "..." : "Send"}
          </button>
        </div>
      </div>
    </aside>
  );
}

function LiveTrace({
  steps,
  onPickPath,
}: {
  steps: AskStep[];
  onPickPath: (path: string) => void;
}) {
  return (
    <ol className="space-y-1 overflow-x-auto rounded-md border border-[var(--color-border-2)]/60 bg-[var(--color-surface)]/30 px-3 py-2 font-mono text-[11.5px] text-[var(--color-fg-muted)]">
      {steps.map((s, i) => {
        const isLast = i === steps.length - 1;
        return (
          <li key={i} className="space-y-0.5">
            <div
              className={cn(
                "flex items-baseline gap-1.5 whitespace-nowrap",
                isLast ? "text-[var(--color-accent)]" : "text-[var(--color-fg)]",
              )}
            >
              <span className="text-[var(--color-fg-dim)]">{i + 1}.</span>
              <span>{s.label}</span>
              {s.detail && (
                <span className="text-[var(--color-fg-dim)]">— {s.detail}</span>
              )}
            </div>
            {s.paths && s.paths.length > 0 && (
              <ul className="ml-4 space-y-0.5">
                {s.paths.map((p) => (
                  <li key={p} className="whitespace-nowrap">
                    <button
                      onClick={() => onPickPath(p)}
                      className="text-left text-[var(--color-accent-dim)] hover:text-[var(--color-accent)] hover:underline"
                    >
                      → {p}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </li>
        );
      })}
    </ol>
  );
}

function ThinkingTrace({
  steps,
  onPickPath,
}: {
  steps: AskStep[];
  onPickPath: (path: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const fileCount = steps.reduce((n, s) => n + (s.paths?.length ?? 0), 0);
  const summary =
    fileCount > 0
      ? `Read ${fileCount} file${fileCount === 1 ? "" : "s"} across ${steps.length} step${steps.length === 1 ? "" : "s"}`
      : `${steps.length} step${steps.length === 1 ? "" : "s"}`;
  return (
    <div className="rounded-md border border-[var(--color-border-2)]/60 bg-[var(--color-surface)]/30">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-1.5 px-2.5 py-1.5 text-left font-mono text-[10.5px] uppercase tracking-[0.16em] text-[var(--color-fg-dim)] hover:text-[var(--color-fg)]"
      >
        <ChevronRight
          className={cn("h-3 w-3 transition-transform", open && "rotate-90")}
        />
        <span>Thinking · {summary}</span>
      </button>
      {open && (
        <ol className="space-y-1.5 overflow-x-auto border-t border-[var(--color-border-2)]/60 px-3 py-2 font-mono text-[11.5px] text-[var(--color-fg-muted)]">
          {steps.map((s, i) => (
            <li key={i} className="space-y-1">
              <div className="flex items-baseline gap-1.5 whitespace-nowrap text-[var(--color-fg)]">
                <span className="text-[var(--color-fg-dim)]">{i + 1}.</span>
                <span>{s.label}</span>
                {s.detail && (
                  <span className="text-[var(--color-fg-dim)]">— {s.detail}</span>
                )}
              </div>
              {s.paths && s.paths.length > 0 && (
                <ul className="ml-4 space-y-0.5">
                  {s.paths.map((p) => (
                    <li key={p} className="whitespace-nowrap">
                      <button
                        onClick={() => onPickPath(p)}
                        className="text-left text-[var(--color-accent-dim)] hover:text-[var(--color-accent)] hover:underline"
                      >
                        → {p}
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

function UsageBadge({ usage }: { usage: AskUsage }) {
  const sectionEntries = Object.entries(usage.sections).filter(([, v]) => v > 0);
  return (
    <details className="group rounded-md border border-[var(--color-border-2)]/60 bg-[var(--color-surface)]/20">
      <summary className="flex cursor-pointer items-center gap-1.5 px-2.5 py-1 font-mono text-[10.5px] uppercase tracking-[0.16em] text-[var(--color-fg-dim)] hover:text-[var(--color-fg)]">
        <ChevronRight className="h-3 w-3 transition-transform group-open:rotate-90" />
        <span>
          {fmt(usage.input_tokens)} in · {fmt(usage.output_tokens)} out
          {usage.cache_read_input_tokens > 0 &&
            ` · ${fmt(usage.cache_read_input_tokens)} cached`}
        </span>
      </summary>
      <div className="border-t border-[var(--color-border-2)]/60 px-3 py-2 font-mono text-[11px] text-[var(--color-fg-muted)]">
        <div className="grid grid-cols-2 gap-x-3 gap-y-0.5">
          <span>input</span>
          <span className="text-right text-[var(--color-fg)]">
            {usage.input_tokens.toLocaleString()}
          </span>
          <span>output</span>
          <span className="text-right text-[var(--color-fg)]">
            {usage.output_tokens.toLocaleString()}
          </span>
          {usage.cache_read_input_tokens > 0 && (
            <>
              <span>cache read</span>
              <span className="text-right text-[var(--color-fg)]">
                {usage.cache_read_input_tokens.toLocaleString()}
              </span>
            </>
          )}
          {usage.cache_creation_input_tokens > 0 && (
            <>
              <span>cache write</span>
              <span className="text-right text-[var(--color-fg)]">
                {usage.cache_creation_input_tokens.toLocaleString()}
              </span>
            </>
          )}
        </div>
        {sectionEntries.length > 0 && (
          <>
            <div className="mt-2 text-[10px] uppercase tracking-[0.16em] text-[var(--color-fg-dim)]">
              Section approx.
            </div>
            <div className="grid grid-cols-2 gap-x-3 gap-y-0.5">
              {sectionEntries.map(([k, v]) => (
                <div key={k} className="contents">
                  <span>{k}</span>
                  <span className="text-right text-[var(--color-fg)]">
                    {v.toLocaleString()}
                  </span>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </details>
  );
}

function EmptyAsk({
  onPick,
  disabled,
}: {
  onPick: (q: string) => void;
  disabled: boolean;
}) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-4">
      <div className="w-full max-w-[300px] rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)]/40 px-4 py-5 text-center">
        <div className="mx-auto mb-3 grid h-9 w-9 place-items-center rounded-md border border-[var(--color-border-2)] bg-[var(--color-bg)]">
          <Sparkles className="h-4 w-4 text-[var(--color-accent)]" />
        </div>
        <p className="text-[14px] leading-relaxed text-[var(--color-fg-muted)]">
          Ask anything about this property. Pin answers as topics.
        </p>
      </div>
      <div className="w-full max-w-[300px] space-y-2">
        <div className="font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--color-fg-dim)]">
          Try one
        </div>
        <div className="flex flex-col gap-1.5">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              onClick={() => onPick(s)}
              disabled={disabled}
              className={cn(
                "group rounded-md border border-[var(--color-border-2)] bg-[var(--color-bg)] px-3 py-2 text-left text-[14px] leading-snug text-[var(--color-fg)] transition-colors",
                "hover:border-[var(--color-accent-dim)] hover:bg-[var(--color-surface)] hover:text-[var(--color-accent)]",
                "disabled:cursor-not-allowed disabled:opacity-40",
              )}
            >
              {s}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
