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

export type SimItem = {
  id: string;
  kind: "email" | "invoice" | "bank";
  label: string;
  detail: string;
  source_path: string | null;
  month: string | null;
};

export type SimDay = {
  day: number;
  content_date: string | null;
  emails: SimItem[];
  invoices: SimItem[];
  bank: SimItem[];
};

export type SimTouched = { path: string; content: string };

export type SimIngestResponse = {
  status: string;
  workspace: string;
  wiki_dir: string;
  provider: string;
  fast_model: string;
  smart_model: string;
  duration_ms: number;
  classification: {
    signal: boolean;
    category: string;
    priority: string;
    confidence: number;
  } | null;
  applied_ops: number;
  commit_sha: string | null;
  idempotent: boolean;
  touched: string[];
  files: SimTouched[];
  normalized_text: string | null;
  git_log: string[];
};

export async function fetchIncremental(): Promise<SimDay[]> {
  const r = await fetch(`${base}/sim/incremental`);
  if (!r.ok) throw new Error(`incremental ${r.status}`);
  return r.json();
}

export async function runSimIngest(body: {
  day: number;
  kind: "email" | "invoice" | "bank";
  id: string;
  mode: "isolated" | "live";
  property_id?: string;
}): Promise<SimIngestResponse> {
  const r = await fetch(`${base}/sim/ingest`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    const detail = await r.text();
    throw new Error(`sim/ingest ${r.status}: ${detail}`);
  }
  return r.json();
}

export type HumanNotes = { path: string; body: string };

export async function fetchHumanNotes(path: string): Promise<HumanNotes> {
  const r = await fetch(
    `${base}/wiki/human-notes?path=${encodeURIComponent(path)}`,
  );
  if (!r.ok) throw new Error(`human-notes ${r.status}`);
  return r.json();
}

export async function saveHumanNotes(
  path: string,
  body: string,
  pmUser: string,
): Promise<{ path: string; bytes_written: number; commit_sha: string | null }> {
  const r = await fetch(
    `${base}/wiki/human-notes?path=${encodeURIComponent(path)}`,
    {
      method: "PUT",
      headers: {
        "content-type": "application/json",
        "x-pm-user": pmUser,
      },
      body: JSON.stringify({ body }),
    },
  );
  if (!r.ok) {
    const detail = await r.text();
    throw new Error(`human-notes save ${r.status}: ${detail}`);
  }
  return r.json();
}
