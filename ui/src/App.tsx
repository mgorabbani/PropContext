import { useEffect, useMemo, useRef, useState } from "react";
import { X } from "lucide-react";
import type { PanelImperativeHandle } from "react-resizable-panels";
import { Group, Panel, Separator } from "react-resizable-panels";
import { TopBar } from "./components/TopBar";
import { Tree } from "./components/Tree";
import { Viewer } from "./components/Viewer";
import { Query } from "./components/Query";
import { Palette } from "./components/Palette";
import { McpSettings } from "./components/McpSettings";
import { fetchFile, fetchProperties, fetchTree } from "./api";
import type { TreeNode } from "./api";
import { flattenTree } from "./lib/markdown";

const ASK_ENABLED = false;

export default function App() {
  const [properties, setProperties] = useState<string[]>([]);
  const [lie, setLie] = useState<string>("");
  const [tree, setTree] = useState<TreeNode | null>(null);
  const [path, setPath] = useState<string | null>(null);
  const [content, setContent] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [mcpSettingsOpen, setMcpSettingsOpen] = useState(false);
  const [askCollapsed, setAskCollapsed] = useState(false);
  const [treeCollapsed, setTreeCollapsed] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [mobileTreeOpen, setMobileTreeOpen] = useState(false);
  const [mobileAskOpen, setMobileAskOpen] = useState(false);
  const askPanelRef = useRef<PanelImperativeHandle | null>(null);
  const treePanelRef = useRef<PanelImperativeHandle | null>(null);

  useEffect(() => {
    const mq = window.matchMedia("(max-width: 768px)");
    const update = () => setIsMobile(mq.matches);
    update();
    mq.addEventListener("change", update);
    return () => mq.removeEventListener("change", update);
  }, []);

  useEffect(() => {
    fetchProperties()
      .then((ps) => {
        setProperties(ps);
        if (ps.length > 0) setLie(ps[0]);
      })
      .catch((e) => setError(String(e)));
  }, []);

  useEffect(() => {
    if (!lie) return;
    setTree(null);
    setPath(null);
    setContent("");
    fetchTree(lie)
      .then((t) => {
        setTree(t);
        setPath(`${lie}/index.md`);
      })
      .catch((e) => setError(String(e)));
  }, [lie]);

  useEffect(() => {
    if (!path) return;
    setLoading(true);
    setError(null);
    fetchFile(path)
      .then((c) => setContent(c))
      .catch((e) => {
        setError(String(e));
        setContent("");
      })
      .finally(() => setLoading(false));
  }, [path]);

  const flatFiles = useMemo(() => (tree ? flattenTree(tree) : []), [tree]);

  function toggleAsk() {
    if (isMobile) {
      setMobileAskOpen((v) => !v);
      return;
    }
    const panel = askPanelRef.current;
    if (!panel) return;
    if (panel.isCollapsed()) panel.expand();
    else panel.collapse();
  }

  function toggleTree() {
    if (isMobile) {
      setMobileTreeOpen((v) => !v);
      return;
    }
    const panel = treePanelRef.current;
    if (!panel) return;
    if (panel.isCollapsed()) panel.expand();
    else panel.collapse();
  }

  function selectPath(p: string) {
    setPath(p);
    if (isMobile) {
      setMobileTreeOpen(false);
      setMobileAskOpen(false);
    }
  }

  const treeButtonActive = isMobile ? mobileTreeOpen : !treeCollapsed;
  const askButtonActive = isMobile ? mobileAskOpen : !askCollapsed;

  const treeSidebar = (
    <aside className="flex h-full flex-col border-r border-[var(--color-border)] bg-[var(--color-bg)]/40">
      <div className="flex flex-col gap-2 border-b border-[var(--color-border)] px-3 py-2">
        <div className="flex items-center justify-between">
          <span className="font-mono text-[10.5px] uppercase tracking-[0.2em] text-[var(--color-fg-dim)]">
            Property
          </span>
          {tree && (
            <span className="font-mono text-[10.5px] text-[var(--color-fg-dim)]">
              {flatFiles.length} files
            </span>
          )}
        </div>
        <div className="relative">
          <select
            value={lie}
            onChange={(e) => setLie(e.target.value)}
            disabled={properties.length === 0}
            className="h-7 w-full cursor-pointer appearance-none rounded-md border border-[var(--color-border-2)] bg-[var(--color-surface)] px-2.5 pr-7 font-mono text-[12px] font-medium text-[var(--color-fg)] outline-none transition-colors hover:border-[var(--color-accent-dim)] focus:border-[var(--color-accent)]"
          >
            {properties.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
          <span className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 text-[var(--color-fg-muted)]">
            <svg width="8" height="6" viewBox="0 0 8 6" fill="none">
              <path
                d="M1 1.5L4 4.5L7 1.5"
                stroke="currentColor"
                strokeWidth="1.4"
                strokeLinecap="round"
              />
            </svg>
          </span>
        </div>
      </div>
      <div className="flex-1 overflow-auto px-1.5 py-2">
        {tree ? (
          <Tree node={tree} selectedPath={path} onSelect={selectPath} isRoot />
        ) : (
          <TreeSkeleton />
        )}
      </div>
    </aside>
  );

  return (
    <div className="flex h-screen flex-col overflow-hidden">
      <TopBar
        onOpenPalette={() => setPaletteOpen(true)}
        onOpenMcpSettings={() => setMcpSettingsOpen(true)}
        askEnabled={ASK_ENABLED}
        askActive={askButtonActive}
        onToggleAsk={toggleAsk}
        treeActive={treeButtonActive}
        onToggleTree={toggleTree}
      />

      <div className="min-h-0 flex-1">
        {isMobile ? (
          <main className="flex h-full min-w-0 flex-col">
            <div className="min-h-0 flex-1">
              <Viewer
                path={path}
                content={content}
                loading={loading}
                error={error}
                onNavigate={selectPath}
              />
            </div>
          </main>
        ) : (
          <Group orientation="horizontal" className="h-full">
            <Panel
              panelRef={treePanelRef}
              defaultSize="20%"
              minSize="14%"
              maxSize="32%"
              collapsible
              collapsedSize="0%"
              onResize={(size) => setTreeCollapsed(size.asPercentage < 1)}
              className="tree-panel overflow-hidden"
            >
              {!treeCollapsed && treeSidebar}
            </Panel>

            <Separator />

            <Panel
              defaultSize={ASK_ENABLED ? "56%" : "80%"}
              minSize="32%"
              className="overflow-hidden"
            >
              <main className="flex h-full min-w-0 flex-col">
                <div className="min-h-0 flex-1">
                  <Viewer
                    path={path}
                    content={content}
                    loading={loading}
                    error={error}
                    onNavigate={selectPath}
                  />
                </div>
              </main>
            </Panel>

            {ASK_ENABLED && (
              <>
                <Separator />
                <Panel
                  panelRef={askPanelRef}
                  defaultSize="24%"
                  minSize="18%"
                  maxSize="42%"
                  collapsible
                  collapsedSize="0%"
                  onResize={(size) => setAskCollapsed(size.asPercentage < 1)}
                  className="ask-panel overflow-hidden"
                >
                  {!askCollapsed && <Query lie={lie} onResolved={selectPath} />}
                </Panel>
              </>
            )}
          </Group>
        )}
      </div>

      {isMobile && (
        <div
          className={`fixed inset-0 z-50 flex transform flex-col bg-[var(--color-bg)] transition-transform duration-200 ${
            mobileTreeOpen ? "translate-x-0" : "-translate-x-full"
          }`}
        >
          <MobileDrawerHeader
            label="Tree"
            onClose={() => setMobileTreeOpen(false)}
          />
          <div className="min-h-0 flex-1">{treeSidebar}</div>
        </div>
      )}

      {ASK_ENABLED && isMobile && (
        <div
          className={`fixed inset-0 z-50 flex transform flex-col bg-[var(--color-bg)] transition-transform duration-200 ${
            mobileAskOpen ? "translate-x-0" : "translate-x-full"
          }`}
        >
          <MobileDrawerHeader
            label="Ask"
            onClose={() => setMobileAskOpen(false)}
          />
          <div className="min-h-0 flex-1">
            <Query lie={lie} onResolved={selectPath} />
          </div>
        </div>
      )}

      <Palette
        open={paletteOpen}
        onOpenChange={setPaletteOpen}
        files={flatFiles}
        onSelect={selectPath}
      />
      <McpSettings open={mcpSettingsOpen} onClose={() => setMcpSettingsOpen(false)} />
    </div>
  );
}

function MobileDrawerHeader({
  label,
  onClose,
}: {
  label: string;
  onClose: () => void;
}) {
  return (
    <div className="flex h-12 shrink-0 items-center justify-between border-b border-[var(--color-border)] bg-[var(--color-surface)]/60 px-3">
      <span className="font-mono text-[10.5px] uppercase tracking-[0.2em] text-[var(--color-fg-muted)]">
        {label}
      </span>
      <button
        aria-label={`Close ${label} panel`}
        onClick={onClose}
        className="grid h-8 w-8 place-items-center rounded-md border border-[var(--color-border-2)] bg-[var(--color-surface)] text-[var(--color-fg-muted)] transition-colors hover:border-[var(--color-accent-dim)] hover:text-[var(--color-fg)]"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}

function TreeSkeleton() {
  return (
    <div className="space-y-1.5 px-2 py-2">
      {Array.from({ length: 10 }).map((_, i) => (
        <div
          key={i}
          className="h-3 animate-pulse rounded bg-[var(--color-surface)]"
          style={{ width: `${50 + ((i * 13) % 40)}%` }}
        />
      ))}
    </div>
  );
}
