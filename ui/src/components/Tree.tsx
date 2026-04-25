import { useEffect, useState } from "react";
import { ChevronRight, FileText, Folder, FolderOpen } from "lucide-react";
import type { TreeNode } from "../api";
import { cn } from "../lib/cn";

type Props = {
  node: TreeNode;
  selectedPath: string | null;
  onSelect: (path: string) => void;
  depth?: number;
  isRoot?: boolean;
};

export function Tree({ node, selectedPath, onSelect, depth = 0, isRoot }: Props) {
  const [open, setOpen] = useState(depth < 2);

  useEffect(() => {
    if (selectedPath && node.type === "dir" && selectedPath.startsWith(node.path + "/")) {
      setOpen(true);
    }
  }, [selectedPath, node]);

  if (node.type === "file") {
    const active = node.path === selectedPath;
    const displayName = node.name.replace(/\.md$/, "");
    return (
      <button
        type="button"
        onClick={() => onSelect(node.path)}
        className={cn(
          "group relative flex w-full items-center gap-2 rounded-md py-[3px] pr-2 text-left transition-colors",
          "font-mono text-[12.5px]",
          active
            ? "bg-[var(--color-surface-2)] text-[var(--color-accent)]"
            : "text-[var(--color-fg-muted)] hover:bg-[var(--color-surface)] hover:text-[var(--color-fg)]",
        )}
        style={{ paddingLeft: 8 + depth * 14 }}
      >
        {active && (
          <span className="absolute left-0 top-1/2 h-4 w-[2px] -translate-y-1/2 rounded-r bg-[var(--color-accent)]" />
        )}
        <FileText
          className={cn(
            "h-3.5 w-3.5 shrink-0",
            active ? "text-[var(--color-accent)]" : "text-[var(--color-fg-dim)]",
          )}
        />
        <span className="truncate">{displayName}</span>
      </button>
    );
  }

  const children = node.children ?? [];
  const label = isRoot ? node.name : node.name;

  return (
    <div className="select-none">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className={cn(
          "group flex w-full items-center gap-1.5 rounded-md py-[3px] pr-2 text-left transition-colors",
          "font-mono text-[12.5px] text-[var(--color-ink-100)]",
          "hover:bg-[var(--color-surface)]",
        )}
        style={{ paddingLeft: 8 + depth * 14 }}
      >
        <ChevronRight
          className={cn(
            "h-3 w-3 shrink-0 text-[var(--color-fg-dim)] transition-transform duration-150",
            open && "rotate-90",
          )}
          strokeWidth={2.4}
        />
        {open ? (
          <FolderOpen
            className={cn(
              "h-3.5 w-3.5 shrink-0",
              isRoot ? "text-[var(--color-accent)]" : "text-[var(--color-fg-muted)]",
            )}
            strokeWidth={1.8}
          />
        ) : (
          <Folder
            className={cn(
              "h-3.5 w-3.5 shrink-0",
              isRoot ? "text-[var(--color-accent)]" : "text-[var(--color-fg-muted)]",
            )}
            strokeWidth={1.8}
          />
        )}
        <span className={cn("truncate", isRoot && "font-medium tracking-tight")}>
          {label}
        </span>
      </button>
      {open && children.length > 0 && (
        <div className="relative fade-up">
          {depth >= 0 && (
            <span
              className="absolute top-0 bottom-1 w-px bg-[var(--color-border)]"
              style={{ left: 8 + depth * 14 + 5 }}
              aria-hidden
            />
          )}
          {children.map((c) => (
            <Tree
              key={c.path}
              node={c}
              selectedPath={selectedPath}
              onSelect={onSelect}
              depth={depth + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
}
