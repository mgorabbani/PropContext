import { useState } from "react";
import { Send, Sparkles } from "lucide-react";
import { ask } from "../api";
import { cn } from "../lib/cn";

type Props = {
  lie: string;
  onResolved: (path: string) => void;
};

type Entry = { question: string; answer: string };

export function Query({ lie, onResolved }: Props) {
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const [entry, setEntry] = useState<Entry | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [unavailable, setUnavailable] = useState(false);

  async function submit() {
    const question = q.trim();
    if (!question || busy) return;
    setBusy(true);
    setMsg(null);
    const res = await ask(question, lie);
    setBusy(false);
    if (!res.ok) {
      if (res.status === 404) {
        setUnavailable(true);
        setMsg("ask endpoint coming soon");
      } else {
        setMsg(`ask failed (${res.status})`);
      }
      return;
    }
    if (res.data.path) {
      onResolved(res.data.path);
      setEntry({ question, answer: `Opened ${res.data.path}` });
      setQ("");
      setMsg(null);
    } else if (res.data.answer) {
      setEntry({ question, answer: res.data.answer });
      setQ("");
      setMsg(null);
    } else {
      setMsg("no result");
    }
  }

  return (
    <aside className="flex h-full min-w-0 flex-col border-l border-[var(--color-border)] bg-[var(--color-bg)]/40">
      <div className="glass sticky top-0 z-10 flex h-11 items-center justify-between gap-2 border-b border-[var(--color-border)] px-4">
        <div className="flex items-center gap-2">
          <Sparkles className="h-3.5 w-3.5 text-[var(--color-accent)]" />
          <span className="font-mono text-[10.5px] uppercase tracking-[0.2em] text-[var(--color-fg-muted)]">
            Ask the wiki
          </span>
        </div>
        {unavailable && (
          <span className="rounded border border-[var(--color-border)] px-1.5 py-px font-mono text-[9.5px] uppercase tracking-wider text-[var(--color-fg-dim)]">
            soon
          </span>
        )}
      </div>

      <div className="min-h-0 flex-1 overflow-auto px-4 py-5">
        {!entry && !msg && <EmptyAsk />}
        {entry && (
          <div className="space-y-3 fade-up">
            <div className="rounded-md border border-[var(--color-border-2)] bg-[var(--color-surface)]/60 px-3 py-2">
              <div className="font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--color-fg-dim)]">
                You
              </div>
              <div className="mt-1 text-[13.5px] leading-relaxed text-[var(--color-fg)]">
                {entry.question}
              </div>
            </div>
            <div className="rounded-md border border-[var(--color-accent-dim)]/40 bg-[var(--color-surface)]/40 px-3 py-2">
              <div className="font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--color-accent-dim)]">
                Wiki
              </div>
              <div className="mt-1 whitespace-pre-wrap text-[13.5px] leading-relaxed text-[var(--color-fg)]">
                {entry.answer}
              </div>
            </div>
          </div>
        )}
        {msg && (
          <div className="mt-3 font-mono text-[11.5px] text-[var(--color-fg-muted)]">
            {msg}
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
                : "What is the contact for MIE-006?"
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

function EmptyAsk() {
  return (
    <div className="grid h-full place-items-center">
      <div className="max-w-[260px] rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)]/40 px-4 py-5 text-center">
        <div className="mx-auto mb-3 grid h-9 w-9 place-items-center rounded-md border border-[var(--color-border-2)] bg-[var(--color-bg)]">
          <Sparkles className="h-4 w-4 text-[var(--color-accent)]" />
        </div>
        <p className="text-[13px] leading-relaxed text-[var(--color-fg-muted)]">
          Ask anything about this property — answers get filed back to{" "}
          <code className="rounded border border-[var(--color-border)] bg-[var(--color-bg)] px-1 py-0.5 font-mono text-[11px] text-[var(--color-fg)]">
            08_explorations/
          </code>
          .
        </p>
      </div>
    </div>
  );
}
