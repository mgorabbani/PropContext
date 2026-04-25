import { FileBadge } from "lucide-react";
import type { Frontmatter } from "../lib/markdown";

type Props = {
  data: Frontmatter;
};

function formatValue(v: unknown): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "string") return v;
  if (typeof v === "number" || typeof v === "boolean") return String(v);
  if (Array.isArray(v)) return v.map((x) => formatValue(x)).join(", ");
  return JSON.stringify(v);
}

export function FrontmatterCard({ data }: Props) {
  const entries = Object.entries(data);
  if (entries.length === 0) return null;

  const primary = entries.filter(([k]) => ["name", "title", "description"].includes(k));
  const rest = entries.filter(([k]) => !["name", "title", "description"].includes(k));

  return (
    <aside className="not-prose mb-8 overflow-hidden rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)]/60">
      <div className="flex items-center gap-2 border-b border-[var(--color-border)] bg-[var(--color-surface-2)]/60 px-4 py-2">
        <FileBadge className="h-3.5 w-3.5 text-[var(--color-accent)]" />
        <span className="font-mono text-[10.5px] uppercase tracking-[0.2em] text-[var(--color-fg-muted)]">
          Frontmatter
        </span>
        <span className="ml-auto font-mono text-[10.5px] text-[var(--color-fg-dim)]">
          {entries.length} fields
        </span>
      </div>

      {primary.length > 0 && (
        <div className="space-y-1 px-4 pt-3 pb-2">
          {primary.map(([k, v]) => (
            <div key={k} className="flex items-baseline gap-3">
              <span className="font-mono text-[10.5px] uppercase tracking-[0.16em] text-[var(--color-fg-dim)]">
                {k}
              </span>
              <span
                className={
                  k === "name" || k === "title"
                    ? "font-display text-[17px] font-medium leading-snug text-[var(--color-ink-50)]"
                    : "text-[13.5px] leading-relaxed text-[var(--color-fg)]"
                }
              >
                {formatValue(v)}
              </span>
            </div>
          ))}
        </div>
      )}

      {rest.length > 0 && (
        <dl className="grid grid-cols-1 gap-x-6 gap-y-1.5 border-t border-[var(--color-border)] px-4 py-3 sm:grid-cols-2">
          {rest.map(([k, v]) => (
            <div key={k} className="flex min-w-0 items-baseline gap-2">
              <dt className="font-mono text-[10.5px] uppercase tracking-[0.16em] text-[var(--color-fg-dim)]">
                {k}
              </dt>
              <dd className="min-w-0 truncate font-mono text-[12px] text-[var(--color-fg)]">
                {formatValue(v)}
              </dd>
            </div>
          ))}
        </dl>
      )}
    </aside>
  );
}
