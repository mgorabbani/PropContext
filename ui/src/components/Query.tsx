import { useEffect, useRef, useState } from "react";
import { Send, Sparkles } from "lucide-react";
import { ask } from "../api";
import { cn } from "../lib/cn";

type Props = {
  lie: string;
  onResolved: (path: string) => void;
};

type Entry = {
  id: number;
  question: string;
  answer: string;
  path?: string;
  status: "ok" | "empty" | "error";
};

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
    setBusy(true);
    const res = await ask(question, lie);
    setBusy(false);
    const id = ++idRef.current;
    if (!res.ok) {
      if (res.status === 404) {
        setUnavailable(true);
        setEntries((e) => [
          ...e,
          {
            id,
            question,
            answer: "Ask endpoint not available on this server.",
            status: "error",
          },
        ]);
      } else {
        setEntries((e) => [
          ...e,
          {
            id,
            question,
            answer: `Request failed (${res.status}).`,
            status: "error",
          },
        ]);
      }
      return;
    }
    const { answer, path } = res.data;
    if (path) onResolved(path);
    if (answer) {
      setEntries((e) => [
        ...e,
        { id, question, answer, path: path ?? undefined, status: "ok" },
      ]);
    } else if (path) {
      setEntries((e) => [
        ...e,
        { id, question, answer: `Opened ${path}`, path, status: "ok" },
      ]);
    } else {
      setEntries((e) => [
        ...e,
        {
          id,
          question,
          answer:
            "The model didn't find an answer in this property's wiki. Try rephrasing or asking about a specific page.",
          status: "empty",
        },
      ]);
    }
  }

  async function submit() {
    await run(q.trim());
  }

  async function pickSuggestion(s: string) {
    await run(s);
  }

  const hasEntries = entries.length > 0;

  return (
    <aside className="flex h-full min-w-0 flex-col border-l border-[var(--color-border)] bg-[var(--color-bg)]/40">
      <div className="glass sticky top-0 z-10 flex h-11 items-center justify-between gap-2 border-b border-[var(--color-border)] px-4">
        <div className="flex items-center gap-2">
          <Sparkles className="h-3.5 w-3.5 text-[var(--color-accent)]" />
          <span className="font-mono text-[10.5px] uppercase tracking-[0.2em] text-[var(--color-fg-muted)]">
            Ask the wiki
          </span>
        </div>
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

      <div ref={scrollRef} className="min-h-0 flex-1 overflow-auto px-4 py-5">
        {!hasEntries && !busy && (
          <EmptyAsk
            onPick={(s) => void pickSuggestion(s)}
            disabled={busy || unavailable}
          />
        )}
        {hasEntries && (
          <div className="space-y-4">
            {entries.map((e) => (
              <div key={e.id} className="space-y-2 fade-up">
                <div className="rounded-md border border-[var(--color-border-2)] bg-[var(--color-surface)]/60 px-3 py-2">
                  <div className="font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--color-fg-dim)]">
                    You
                  </div>
                  <div className="mt-1 text-[13.5px] leading-relaxed text-[var(--color-fg)]">
                    {e.question}
                  </div>
                </div>
                <div
                  className={cn(
                    "rounded-md border px-3 py-2",
                    e.status === "ok" &&
                      "border-[var(--color-accent-dim)]/40 bg-[var(--color-surface)]/40",
                    e.status === "empty" &&
                      "border-[var(--color-border-2)] bg-[var(--color-surface)]/30",
                    e.status === "error" &&
                      "border-red-500/30 bg-red-500/5",
                  )}
                >
                  <div
                    className={cn(
                      "font-mono text-[10px] uppercase tracking-[0.2em]",
                      e.status === "ok" && "text-[var(--color-accent-dim)]",
                      e.status === "empty" && "text-[var(--color-fg-dim)]",
                      e.status === "error" && "text-red-500",
                    )}
                  >
                    {e.status === "error" ? "Error" : "Wiki"}
                  </div>
                  <div className="mt-1 whitespace-pre-wrap text-[13.5px] leading-relaxed text-[var(--color-fg)]">
                    {e.answer}
                  </div>
                  {e.path && (
                    <button
                      onClick={() => onResolved(e.path!)}
                      className="mt-2 font-mono text-[11px] text-[var(--color-accent)] hover:underline"
                    >
                      → {e.path}
                    </button>
                  )}
                </div>
              </div>
            ))}
            {busy && (
              <div className="rounded-md border border-[var(--color-border-2)] bg-[var(--color-surface)]/30 px-3 py-2">
                <div className="font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--color-fg-dim)]">
                  Wiki
                </div>
                <div className="mt-1 flex items-center gap-1.5 text-[13.5px] text-[var(--color-fg-muted)]">
                  <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-[var(--color-accent)]" />
                  thinking...
                </div>
              </div>
            )}
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
            className="flex-1 bg-transparent px-2 py-1 text-[13.5px] text-[var(--color-fg)] placeholder:text-[var(--color-fg-dim)] outline-none"
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
        <p className="text-[13px] leading-relaxed text-[var(--color-fg-muted)]">
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
                "group rounded-md border border-[var(--color-border-2)] bg-[var(--color-bg)] px-3 py-2 text-left text-[12.5px] leading-snug text-[var(--color-fg)] transition-colors",
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
