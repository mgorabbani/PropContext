import { ChevronRight, Hash } from "lucide-react";

type Props = {
  path: string | null;
};

export function Breadcrumb({ path }: Props) {
  if (!path) return null;
  const segments = path.split("/").filter(Boolean);
  return (
    <nav
      aria-label="breadcrumb"
      className="flex min-w-0 items-center gap-1 overflow-hidden font-mono text-[12px]"
    >
      <Hash className="h-3 w-3 shrink-0 text-[var(--color-accent)]" />
      {segments.map((seg, i) => {
        const isLast = i === segments.length - 1;
        return (
          <span key={i} className="flex min-w-0 items-center gap-1">
            <span
              className={
                isLast
                  ? "truncate text-[var(--color-ink-50)]"
                  : "shrink-0 text-[var(--color-fg-muted)]"
              }
            >
              {seg.replace(/\.md$/, "")}
            </span>
            {!isLast && (
              <ChevronRight className="h-3 w-3 shrink-0 text-[var(--color-fg-dim)]" />
            )}
          </span>
        );
      })}
    </nav>
  );
}
