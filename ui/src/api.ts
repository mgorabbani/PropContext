export type TreeNode = {
  name: string;
  path: string;
  type: "file" | "dir";
  children?: TreeNode[] | null;
};

export type AskResponse = {
  path?: string;
  answer?: string;
};

const base = "/api/v1";

export async function fetchProperties(): Promise<string[]> {
  const r = await fetch(`${base}/wiki/properties`);
  if (!r.ok) throw new Error(`properties ${r.status}`);
  return r.json();
}

export async function fetchTree(lie: string): Promise<TreeNode> {
  const r = await fetch(`${base}/wiki/tree?lie=${encodeURIComponent(lie)}`);
  if (!r.ok) throw new Error(`tree ${r.status}`);
  return r.json();
}

export async function fetchFile(path: string): Promise<string> {
  const r = await fetch(`${base}/wiki/file?path=${encodeURIComponent(path)}`);
  if (!r.ok) throw new Error(`file ${r.status}`);
  return r.text();
}

export async function ask(
  question: string,
  lie: string,
): Promise<{ ok: true; data: AskResponse } | { ok: false; status: number }> {
  const r = await fetch(`${base}/ask`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ question, lie }),
  });
  if (!r.ok) return { ok: false, status: r.status };
  return { ok: true, data: await r.json() };
}
