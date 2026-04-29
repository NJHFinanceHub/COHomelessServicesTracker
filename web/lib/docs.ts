import fs from "node:fs";
import path from "node:path";

const DOCS_DIR = path.join(process.cwd(), "..", "docs");

export function readDoc(name: string): string {
  const filePath = path.join(DOCS_DIR, name);
  return fs.readFileSync(filePath, "utf8");
}
