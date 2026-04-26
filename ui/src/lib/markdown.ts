export type Frontmatter = Record<string, string>;

export type ParsedDoc = {
  data: Frontmatter;
  content: string;
};

const FM_RE = /^---\r?\n([\s\S]*?)\r?\n---\r?\n?/;

export function parseMarkdown(raw: string): ParsedDoc {
  const m = raw.match(FM_RE);
  if (!m) return { data: {}, content: raw };
  const yaml = m[1];
  const content = raw.slice(m[0].length);
  const data: Record<string, string> = {};
  let key = "";
  for (const line of yaml.split(/\r?\n/)) {
    const kv = /^([A-Za-z_][\w-]*)\s*:\s*(.*)$/.exec(line);
    if (kv) {
      key = kv[1];
      data[key] = kv[2].trim();
    } else if (key && /^\s+/.test(line)) {
      data[key] = (data[key] + " " + line.trim()).trim();
    }
  }
  return { data, content };
}

const HUMAN_NOTES_HEADING = "# Human Notes";

export function splitAtHumanNotes(content: string): {
  above: string;
  hasBoundary: boolean;
  body: string;
} {
  const idx = content.indexOf(HUMAN_NOTES_HEADING);
  if (idx === -1) return { above: content, hasBoundary: false, body: "" };
  const headingEnd = idx + HUMAN_NOTES_HEADING.length;
  const above = content.slice(0, idx).replace(/\n+$/, "\n");
  const body = content.slice(headingEnd).replace(/^\n+/, "").replace(/\s+$/, "");
  return { above, hasBoundary: true, body };
}

export function resolveRelativePath(currentPath: string, href: string): string {
  const baseSegs = currentPath.split("/").slice(0, -1);
  const hrefSegs = href.split("/");
  for (const seg of hrefSegs) {
    if (seg === "" || seg === ".") continue;
    if (seg === "..") {
      if (baseSegs.length > 0) baseSegs.pop();
      continue;
    }
    baseSegs.push(seg);
  }
  return baseSegs.join("/");
}

export function flattenTree(
  node: { name: string; path: string; type: "file" | "dir"; children?: Array<unknown> | null },
  out: Array<{ name: string; path: string }> = [],
): Array<{ name: string; path: string }> {
  if (node.type === "file") {
    out.push({ name: node.name, path: node.path });
  } else if (node.children) {
    for (const c of node.children as Array<{
      name: string;
      path: string;
      type: "file" | "dir";
      children?: Array<unknown> | null;
    }>) {
      flattenTree(c, out);
    }
  }
  return out;
}
