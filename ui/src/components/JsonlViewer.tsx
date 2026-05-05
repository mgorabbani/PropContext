import { Fragment, useMemo, useState } from "react";
import { ChevronRight, Code2, Table2 } from "lucide-react";
import { cn } from "../lib/cn";

type Row = {
  raw: string;
  parsed: Record<string, unknown> | null;
  error?: string;
};

function parseLines(content: string): Row[] {
  return content
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter((l) => l.length > 0)
    .map<Row>((raw) => {
      try {
        const parsed = JSON.parse(raw) as Record<string, unknown>;
        return { raw, parsed };
      } catch (e) {
        return { raw, parsed: null, error: String(e) };
      }
    });
}

function eventTypeTone(t: unknown): string {
  switch (t) {
    case "email":
      return "border-sky-500/30 text-sky-600 bg-sky-500/8 dark:text-sky-300";
    case "invoice":
      return "border-violet-500/30 text-violet-600 bg-violet-500/8 dark:text-violet-300";
    case "bank":
      return "border-emerald-500/30 text-emerald-600 bg-emerald-500/8 dark:text-emerald-300";
    case "manual":
      return "border-amber-500/30 text-amber-600 bg-amber-500/8 dark:text-amber-300";
    default:
      return "border-[var(--color-border-2)] text-[var(--color-fg-muted)] bg-[var(--color-surface)]";
  }
}

function compactValue(v: unknown): string {
  if (v == null) return "—";
  if (typeof v === "string") return v;
  if (typeof v === "number" || typeof v === "boolean") return String(v);
  if (Array.isArray(v)) return `[${v.length}]`;
  return JSON.stringify(v);
}

function formatTs(ts: unknown): string {
  if (typeof ts !== "string") return "";
  const d = new Date(ts);
  if (isNaN(d.getTime())) return ts;
  return d.toISOString().replace("T", " ").replace(/\.\d+Z$/, "Z");
}

export function JsonlViewer({ content }: { content: string }) {
  const rows = useMemo(() => parseLines(content), [content]);
  const [view, setView] = useState<"table" | "raw">("table");
  const [expanded, setExpanded] = useState<Set<number>>(new Set());

  function toggle(i: number) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(i)) next.delete(i);
      else next.add(i);
      return next;
    });
  }

  const stats = useMemo(() => {
    const byType = new Map<string, number>();
    let parsedCount = 0;
    let errorCount = 0;
    for (const r of rows) {
      if (r.parsed) {
        parsedCount++;
        const t = String(r.parsed["event_type"] ?? "—");
        byType.set(t, (byType.get(t) ?? 0) + 1);
      } else {
        errorCount++;
      }
    }
    return { parsedCount, errorCount, byType };
  }, [rows]);

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="rounded-md border border-[var(--color-border-2)] bg-[var(--color-surface)] px-2 py-0.5 font-mono text-[11px] text-[var(--color-fg)]">
            {rows.length} {rows.length === 1 ? "line" : "lines"}
          </span>
          {stats.errorCount > 0 && (
            <span className="rounded-md border border-rose-500/30 bg-rose-500/8 px-2 py-0.5 font-mono text-[11px] text-rose-600 dark:text-rose-300">
              {stats.errorCount} parse error{stats.errorCount === 1 ? "" : "s"}
            </span>
          )}
          {Array.from(stats.byType.entries()).map(([t, n]) => (
            <span
              key={t}
              className={cn(
                "rounded-md border px-2 py-0.5 font-mono text-[11px]",
                eventTypeTone(t),
              )}
            >
              {t} <span className="opacity-70">×{n}</span>
            </span>
          ))}
        </div>

        <div className="flex items-center gap-1 rounded-md border border-[var(--color-border-2)] bg-[var(--color-surface)] p-0.5">
          <button
            onClick={() => setView("table")}
            className={cn(
              "flex items-center gap-1 rounded px-2 py-0.5 font-mono text-[11px] transition-colors",
              view === "table"
                ? "bg-[var(--color-bg)] text-[var(--color-accent)]"
                : "text-[var(--color-fg-muted)] hover:text-[var(--color-fg)]",
            )}
          >
            <Table2 className="h-3 w-3" />
            table
          </button>
          <button
            onClick={() => setView("raw")}
            className={cn(
              "flex items-center gap-1 rounded px-2 py-0.5 font-mono text-[11px] transition-colors",
              view === "raw"
                ? "bg-[var(--color-bg)] text-[var(--color-accent)]"
                : "text-[var(--color-fg-muted)] hover:text-[var(--color-fg)]",
            )}
          >
            <Code2 className="h-3 w-3" />
            raw
          </button>
        </div>
      </div>

      {view === "raw" ? (
        <pre className="overflow-auto rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)]/40 p-4 font-mono text-[11.5px] leading-relaxed text-[var(--color-fg)]">
          {rows.map((r) => r.raw).join("\n")}
        </pre>
      ) : (
        <div className="overflow-hidden rounded-lg border border-[var(--color-border)]">
          <table className="w-full border-collapse text-[11.5px]">
            <thead className="bg-[var(--color-surface)]/60">
              <tr className="font-mono uppercase tracking-[0.16em] text-[10px] text-[var(--color-fg-dim)]">
                <th className="w-6 border-b border-[var(--color-border)] px-2 py-2 text-left"></th>
                <th className="border-b border-[var(--color-border)] px-2 py-2 text-left">
                  ts
                </th>
                <th className="border-b border-[var(--color-border)] px-2 py-2 text-left">
                  type
                </th>
                <th className="border-b border-[var(--color-border)] px-2 py-2 text-left">
                  event_id
                </th>
                <th className="border-b border-[var(--color-border)] px-2 py-2 text-left">
                  summary / error
                </th>
                <th className="border-b border-[var(--color-border)] px-2 py-2 text-right">
                  ops
                </th>
              </tr>
            </thead>
            <tbody className="font-mono text-[11.5px]">
              {rows.map((r, i) => {
                const p = r.parsed ?? {};
                const isOpen = expanded.has(i);
                const evType = p["event_type"];
                const summary =
                  (p["summary"] as string | undefined) ??
                  (p["error"] as string | undefined) ??
                  (r.parsed ? "" : r.raw);
                const applied = p["applied_ops"];
                const deferred = p["deferred_ops"];
                return (
                  <Fragment key={i}>
                    <tr
                      onClick={() => toggle(i)}
                      className="cursor-pointer border-t border-[var(--color-border)] hover:bg-[var(--color-surface)]/40"
                    >
                      <td className="px-2 py-1.5 align-top text-[var(--color-fg-dim)]">
                        <ChevronRight
                          className={cn(
                            "h-3 w-3 transition-transform",
                            isOpen && "rotate-90",
                          )}
                        />
                      </td>
                      <td className="whitespace-nowrap px-2 py-1.5 align-top text-[var(--color-fg-muted)]">
                        {formatTs(p["ts"])}
                      </td>
                      <td className="whitespace-nowrap px-2 py-1.5 align-top">
                        {!r.parsed ? (
                          <span className="rounded border border-rose-500/30 bg-rose-500/8 px-1.5 py-0.5 text-[10.5px] text-rose-600 dark:text-rose-300">
                            error
                          </span>
                        ) : (
                          <span
                            className={cn(
                              "rounded border px-1.5 py-0.5 text-[10.5px]",
                              eventTypeTone(evType),
                            )}
                          >
                            {compactValue(evType)}
                          </span>
                        )}
                      </td>
                      <td className="whitespace-nowrap px-2 py-1.5 align-top text-[var(--color-fg)]">
                        {compactValue(p["event_id"])}
                      </td>
                      <td className="px-2 py-1.5 align-top text-[var(--color-fg-muted)]">
                        <div className="line-clamp-2">{summary}</div>
                      </td>
                      <td className="whitespace-nowrap px-2 py-1.5 text-right align-top tabular-nums text-[var(--color-fg)]">
                        {applied != null ? (
                          <>
                            {compactValue(applied)}
                            {Number(deferred) > 0 && (
                              <span className="ml-1 text-amber-600 dark:text-amber-400">
                                +{compactValue(deferred)}
                              </span>
                            )}
                          </>
                        ) : (
                          <span className="text-[var(--color-fg-dim)]">—</span>
                        )}
                      </td>
                    </tr>
                    {isOpen && (
                      <tr className="bg-[var(--color-bg)]/40">
                        <td colSpan={6} className="px-2 pb-3 pt-1">
                          <pre className="overflow-auto rounded border border-[var(--color-border)] bg-[var(--color-surface)]/40 p-3 text-[11px] leading-relaxed text-[var(--color-fg)]">
                            {r.parsed
                              ? JSON.stringify(r.parsed, null, 2)
                              : `${r.error ?? "parse failed"}\n\n${r.raw}`}
                          </pre>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
