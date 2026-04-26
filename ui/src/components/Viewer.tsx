import { useMemo, useState, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";
import { FileQuestion, FileWarning } from "lucide-react";
import { Breadcrumb } from "./Breadcrumb";
import { FrontmatterCard } from "./FrontmatterCard";
import { HumanNotesEditor } from "./HumanNotesEditor";
import { parseMarkdown, resolveRelativePath, splitAtHumanNotes } from "../lib/markdown";
import { rehypeStripComments } from "../lib/rehypeStripComments";

type Props = {
  path: string | null;
  content: string;
  loading: boolean;
  error: string | null;
  onNavigate?: (path: string) => void;
};

const PM_USER = "pm";

function isExternalHref(href: string): boolean {
  return (
    /^[a-z][a-z0-9+.-]*:/i.test(href) ||
    href.startsWith("//") ||
    href.startsWith("#") ||
    href.startsWith("mailto:")
  );
}

export function Viewer({ path, content, loading, error, onNavigate }: Props) {
  const parsed = useMemo(() => parseMarkdown(content), [content]);
  const split = useMemo(
    () => splitAtHumanNotes(parsed.content),
    [parsed.content],
  );
  const [notesOverride, setNotesOverride] = useState<string | null>(null);

  useEffect(() => {
    setNotesOverride(null);
  }, [path, content]);

  const notesBody = notesOverride ?? split.body;

  return (
    <section className="flex h-full min-w-0 flex-col">
      <div className="glass sticky top-0 z-10 flex h-11 items-center justify-between gap-4 border-b border-[var(--color-border)] px-6">
        <Breadcrumb path={path} />
        <div className="flex shrink-0 items-center gap-2 font-mono text-[10.5px] uppercase tracking-[0.18em] text-[var(--color-fg-dim)]">
          <span className="h-1.5 w-1.5 rounded-full bg-[var(--color-accent)] shadow-[0_0_8px_rgba(212,255,60,0.6)]" />
          Live
        </div>
      </div>

      <div className="relative flex-1 overflow-auto">
        <div className="mx-auto w-full max-w-3xl px-8 py-10 lg:py-12">
          {loading && <ViewerSkeleton />}
          {error && !loading && <ViewerError message={error} />}
          {!loading && !error && !path && <EmptyState />}
          {!loading && !error && path && content && (
            <article>
              <FrontmatterCard data={parsed.data} />
              <div className="prose-wiki">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  rehypePlugins={[rehypeRaw, rehypeStripComments]}
                  components={{
                    a: ({ node: _node, href, children, ...props }) => {
                      void _node;
                      const hrefPath = href?.split(/[?#]/, 1)[0] ?? "";
                      const canNavigate =
                        Boolean(path && onNavigate && href) &&
                        !isExternalHref(href ?? "") &&
                        hrefPath.endsWith(".md");

                      return (
                        <a
                          {...props}
                          href={href}
                          onClick={
                            canNavigate
                              ? (event) => {
                                  event.preventDefault();
                                  onNavigate?.(resolveRelativePath(path, hrefPath));
                                }
                              : undefined
                          }
                        >
                          {children}
                        </a>
                      );
                    },
                    span: ({ node: _node, className, children, ...props }) => {
                      void _node;
                      const cls = Array.isArray(className)
                        ? className.join(" ")
                        : className;
                      if (cls?.includes("wiki-ghost-comment")) {
                        return (
                          <span
                            {...props}
                            className="my-2 mr-2 inline-flex items-center gap-1.5 rounded border border-dashed border-[var(--color-border-2)] bg-[var(--color-surface)]/60 px-2 py-[2px] font-mono text-[10.5px] italic text-[var(--color-fg-dim)]"
                          >
                            {children}
                          </span>
                        );
                      }
                      return (
                        <span {...props} className={cls}>
                          {children}
                        </span>
                      );
                    },
                  }}
                >
                  {split.above}
                </ReactMarkdown>
              </div>
              {split.hasBoundary && (
                <HumanNotesEditor
                  path={path}
                  initialBody={notesBody}
                  pmUser={PM_USER}
                  onSaved={(b) => setNotesOverride(b)}
                />
              )}
            </article>
          )}
        </div>
      </div>
    </section>
  );
}

function ViewerSkeleton() {
  return (
    <div className="space-y-4">
      <div className="h-24 animate-pulse rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)]/40" />
      <div className="h-7 w-2/3 animate-pulse rounded bg-[var(--color-surface)]" />
      <div className="space-y-2">
        <div className="h-4 w-full animate-pulse rounded bg-[var(--color-surface)]" />
        <div className="h-4 w-11/12 animate-pulse rounded bg-[var(--color-surface)]" />
        <div className="h-4 w-9/12 animate-pulse rounded bg-[var(--color-surface)]" />
      </div>
      <div className="h-5 w-1/3 animate-pulse rounded bg-[var(--color-surface)]" />
      <div className="space-y-2">
        <div className="h-4 w-full animate-pulse rounded bg-[var(--color-surface)]" />
        <div className="h-4 w-10/12 animate-pulse rounded bg-[var(--color-surface)]" />
      </div>
    </div>
  );
}

function ViewerError({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-3 rounded-lg border border-red-500/30 bg-red-500/5 px-4 py-3">
      <FileWarning className="mt-0.5 h-4 w-4 shrink-0 text-red-400" />
      <div className="font-mono text-[12.5px] text-red-300">{message}</div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="grid place-items-center py-24">
      <div className="max-w-md text-center">
        <div className="mx-auto mb-5 grid h-12 w-12 place-items-center rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)]">
          <FileQuestion className="h-5 w-5 text-[var(--color-fg-muted)]" />
        </div>
        <h2 className="font-display text-[22px] font-medium tracking-tight text-[var(--color-ink-50)]">
          Nothing selected
        </h2>
        <p className="mt-2 text-[13.5px] leading-relaxed text-[var(--color-fg-muted)]">
          Pick a file from the tree on the left, or press
          <kbd className="mx-1 rounded border border-[var(--color-border)] bg-[var(--color-surface)] px-1.5 py-0.5 font-mono text-[11px]">
            ⌘K
          </kbd>
          to jump to one.
        </p>
      </div>
    </div>
  );
}
