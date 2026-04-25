import { Command } from "cmdk";
import { useEffect } from "react";
import { FileText } from "lucide-react";

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  files: Array<{ name: string; path: string }>;
  onSelect: (path: string) => void;
};

export function Palette({ open, onOpenChange, files, onSelect }: Props) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        onOpenChange(!open);
      } else if (e.key === "Escape" && open) {
        onOpenChange(false);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onOpenChange]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 grid place-items-start justify-center bg-black/60 pt-[14vh] backdrop-blur-sm fade-up"
      onClick={() => onOpenChange(false)}
    >
      <div className="w-[min(640px,92vw)]" onClick={(e) => e.stopPropagation()}>
        <Command label="File jumper" loop>
          <Command.Input placeholder="Jump to a file..." autoFocus />
          <Command.List>
            <Command.Empty>No matches.</Command.Empty>
            {files.map((f) => (
              <Command.Item
                key={f.path}
                value={f.path}
                onSelect={() => {
                  onSelect(f.path);
                  onOpenChange(false);
                }}
              >
                <FileText className="h-3.5 w-3.5 text-[var(--color-fg-dim)]" />
                <span className="text-[var(--color-fg)]">{f.name.replace(/\.md$/, "")}</span>
                <span className="ml-auto truncate text-[11px] text-[var(--color-fg-dim)]">
                  {f.path}
                </span>
              </Command.Item>
            ))}
          </Command.List>
        </Command>
      </div>
    </div>
  );
}
