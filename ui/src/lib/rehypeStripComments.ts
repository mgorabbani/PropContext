import type { Plugin } from "unified";

type AnyNode = {
  type: string;
  value?: string;
  tagName?: string;
  properties?: Record<string, unknown>;
  children?: AnyNode[];
};

export const rehypeStripComments: Plugin<[], AnyNode> = () => {
  return (tree) => {
    const visit = (node: AnyNode) => {
      if (!node.children) return;
      const next: AnyNode[] = [];
      for (const child of node.children) {
        if (child.type === "comment") {
          const text = (child.value ?? "").trim();
          next.push({
            type: "element",
            tagName: "span",
            properties: {
              className: ["wiki-ghost-comment"],
              "data-comment": "1",
              title: text,
            },
            children: [{ type: "text", value: `i ${text}` }],
          });
          continue;
        }
        if (child.type === "element") {
          visit(child);
        }
        next.push(child);
      }
      node.children = next;
    };
    visit(tree);
  };
};
