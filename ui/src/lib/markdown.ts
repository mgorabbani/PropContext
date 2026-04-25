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
