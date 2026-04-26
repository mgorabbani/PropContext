import { useState } from "react";
import { X, Check, Copy } from "lucide-react";

type Props = {
  open: boolean;
  onClose: () => void;
};

const MCP_URL = `${window.location.origin}/mcp`;

const CLAUDE_DESKTOP_CONFIG = JSON.stringify(
  {
    mcpServers: {
      "buena-context": {
        type: "http",
        url: MCP_URL,
      },
    },
  },
  null,
  2,
);

const CURSOR_CONFIG = JSON.stringify(
  {
    mcpServers: {
      "buena-context": {
        url: MCP_URL,
      },
    },
  },
  null,
  2,
);

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  function copy() {
    void navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  }
  return (
    <button
      onClick={copy}
      className="flex items-center gap-1 rounded border border-[var(--color-border-2)] bg-[var(--color-bg)] px-2 py-0.5 font-mono text-[10px] text-[var(--color-fg-muted)] transition-colors hover:border-[var(--color-accent-dim)] hover:text-[var(--color-fg)]"
    >
      {copied ? (
        <Check className="h-3 w-3 text-[var(--color-accent)]" />
      ) : (
        <Copy className="h-3 w-3" />
      )}
      {copied ? "Copied" : "Copy"}
    </button>
  );
}

function ConfigBlock({ label, value }: { label: string; value: string }) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-[var(--color-fg-dim)]">
          {label}
        </span>
        <CopyButton text={value} />
      </div>
      <pre className="overflow-x-auto rounded-md border border-[var(--color-border)] bg-[var(--color-bg)] p-3 font-mono text-[11px] leading-relaxed text-[var(--color-fg)]">
        {value}
      </pre>
    </div>
  );
}

export function McpSettings({ open, onClose }: Props) {
  if (!open) return null;
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-lg rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-5 flex items-start justify-between">
          <div>
            <h2 className="font-display text-[15px] font-medium text-[var(--color-fg)]">
              Connect via MCP
            </h2>
            <p className="mt-0.5 text-[12px] text-[var(--color-fg-muted)]">
              Use any AI agent — Claude Desktop, Cursor, your own script.
            </p>
          </div>
          <button
            onClick={onClose}
            className="grid h-7 w-7 place-items-center rounded-md border border-[var(--color-border-2)] bg-[var(--color-bg)] text-[var(--color-fg-muted)] transition-colors hover:text-[var(--color-fg)]"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>

        <div className="space-y-4">
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-[var(--color-fg-dim)]">
                MCP Endpoint
              </span>
              <CopyButton text={MCP_URL} />
            </div>
            <div className="flex items-center gap-2 rounded-md border border-[var(--color-border)] bg-[var(--color-bg)] px-3 py-2">
              <span className="flex-1 font-mono text-[12px] text-[var(--color-fg)]">
                {MCP_URL}
              </span>
            </div>
          </div>

          <ConfigBlock label="Claude Desktop (claude_desktop_config.json)" value={CLAUDE_DESKTOP_CONFIG} />
          <ConfigBlock label="Cursor (.cursor/mcp.json)" value={CURSOR_CONFIG} />

          <div className="rounded-md border border-[var(--color-border)] bg-[var(--color-bg)]/60 px-3 py-2.5">
            <p className="font-mono text-[10.5px] leading-relaxed text-[var(--color-fg-muted)]">
              <span className="text-[var(--color-accent)]">Tools available:</span>{" "}
              list_properties · wiki_tree · get_property · get_building ·
              read_wiki_file · search_wiki · ask_wiki
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
