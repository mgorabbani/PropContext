import { Building2, Command, MessageSquare, Moon, PanelLeft, Sun, Sparkles } from "lucide-react";
import { useEffect, useState } from "react";
import { cn } from "../lib/cn";

type Props = {
  onOpenPalette: () => void;
  askActive: boolean;
  onToggleAsk: () => void;
  treeActive: boolean;
  onToggleTree: () => void;
};

export function TopBar({
  onOpenPalette,
  askActive,
  onToggleAsk,
  treeActive,
  onToggleTree,
}: Props) {
  const [theme, setTheme] = useState<"dark" | "light">(() => {
    if (typeof window === "undefined") return "dark";
    const stored = window.localStorage.getItem("theme");
    if (stored === "light" || stored === "dark") return stored;
    return window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
  });

  useEffect(() => {
    const root = document.documentElement;
    root.classList.toggle("dark", theme === "dark");
    root.classList.toggle("light", theme === "light");
    window.localStorage.setItem("theme", theme);
  }, [theme]);

  return (
    <header className="glass sticky top-0 z-40 flex h-12 items-center justify-between gap-4 border-b border-[var(--color-border)] px-4">
      <div className="flex items-center gap-3">
        <button
          onClick={onToggleTree}
          aria-label={treeActive ? "Close Tree panel" : "Open Tree panel"}
          title={treeActive ? "Close Tree panel" : "Open Tree panel"}
          className={cn(
            "grid h-7 w-7 place-items-center rounded-md border transition-colors",
            treeActive
              ? "border-[var(--color-accent-dim)] bg-[var(--color-surface)] text-[var(--color-accent)]"
              : "border-[var(--color-border-2)] bg-[var(--color-surface)] text-[var(--color-fg-muted)] hover:border-[var(--color-accent-dim)] hover:text-[var(--color-fg)]",
          )}
        >
          <PanelLeft className="h-3.5 w-3.5" />
        </button>
        <div className="flex items-center gap-2">
          <div className="grid h-6 w-6 place-items-center rounded-md bg-[var(--color-accent)] text-[#0b0b0a]">
            <Building2 className="h-3.5 w-3.5" strokeWidth={2.5} />
          </div>
          <span className="font-display text-[15px] font-medium tracking-tight text-[var(--color-ink-50)]">
            Buena
          </span>
          <span className="hidden text-[11px] uppercase tracking-[0.18em] text-[var(--color-fg-muted)] sm:inline">
            Context
          </span>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <button
          onClick={onOpenPalette}
          className={cn(
            "group flex h-7 shrink-0 items-center gap-2 whitespace-nowrap rounded-md border border-[var(--color-border-2)]",
            "bg-[var(--color-surface)] px-2.5 text-[12px] text-[var(--color-fg-muted)]",
            "transition-colors hover:border-[var(--color-accent-dim)] hover:text-[var(--color-fg)]",
          )}
        >
          <Sparkles className="h-3 w-3 shrink-0 text-[var(--color-accent)]" />
          <span className="hidden sm:inline">Jump to file</span>
          <kbd className="ml-1 hidden items-center gap-0.5 rounded border border-[var(--color-border)] bg-[var(--color-bg)] px-1 py-0 font-mono text-[10px] tracking-tight text-[var(--color-fg-dim)] sm:flex">
            <Command className="h-2.5 w-2.5" />K
          </kbd>
        </button>

        <button
          onClick={onToggleAsk}
          aria-label={askActive ? "Close Ask panel" : "Open Ask panel"}
          title={askActive ? "Close Ask panel" : "Open Ask panel"}
          className={cn(
            "grid h-7 w-7 place-items-center rounded-md border transition-colors",
            askActive
              ? "border-[var(--color-accent-dim)] bg-[var(--color-surface)] text-[var(--color-accent)]"
              : "border-[var(--color-border-2)] bg-[var(--color-surface)] text-[var(--color-fg-muted)] hover:border-[var(--color-accent-dim)] hover:text-[var(--color-fg)]",
          )}
        >
          <MessageSquare className="h-3.5 w-3.5" />
        </button>

        <button
          onClick={() => setTheme((t) => (t === "dark" ? "light" : "dark"))}
          aria-label="Toggle theme"
          className={cn(
            "grid h-7 w-7 place-items-center rounded-md border border-[var(--color-border-2)]",
            "bg-[var(--color-surface)] text-[var(--color-fg-muted)]",
            "transition-colors hover:border-[var(--color-accent-dim)] hover:text-[var(--color-fg)]",
          )}
        >
          {theme === "dark" ? (
            <Sun className="h-3.5 w-3.5" />
          ) : (
            <Moon className="h-3.5 w-3.5" />
          )}
        </button>
      </div>
    </header>
  );
}
