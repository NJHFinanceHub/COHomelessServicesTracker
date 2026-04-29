import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { readDoc } from "@/lib/docs";

export const metadata = {
  title: "Methodology — Denver Homelessness Dollar Tracker",
};

export default function MethodologyPage() {
  const md = readDoc("methodology.md");
  return (
    <article className="prose-civic">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{md}</ReactMarkdown>
    </article>
  );
}
