import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { readDoc } from "@/lib/docs";

export const metadata = {
  title: "Sources — Denver Homelessness Dollar Tracker",
};

export default function SourcesPage() {
  const md = readDoc("source-inventory.md");
  return (
    <article className="prose-civic">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{md}</ReactMarkdown>
    </article>
  );
}
