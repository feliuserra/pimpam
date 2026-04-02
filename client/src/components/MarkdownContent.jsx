import { useMemo } from "react";

/**
 * Lightweight inline-markdown renderer for post & comment content.
 *
 * Supported syntax:
 *   **bold**          → <strong>
 *   *italic*          → <em>
 *   ~~strikethrough~~ → <del>
 *   `code`            → <code>
 *   [text](url)       → <a href>   (only http/https links)
 *   bare URLs         → <a href>   (auto-linked)
 *   #hashtag          → <a href>   (links to /hashtag/:tag)
 *   newlines          → <br />
 *
 * All output is React elements — no dangerouslySetInnerHTML, no XSS risk.
 */

// Regex that matches all supported inline patterns, in priority order.
// Order matters: longer/more-specific patterns first.
const INLINE_RE =
  /(\*\*(.+?)\*\*)|(\*(.+?)\*)|(`(.+?)`)|(~~(.+?)~~)|(\[([^\]]+)\]\((https?:\/\/[^\s)]+)\))|(#([a-zA-Z]\w{0,49})(?=[\s,.:;!?)}\]"']|$))|(https?:\/\/[^\s<>)"']+)/g;

function parseInline(text) {
  const parts = [];
  let lastIndex = 0;
  let match;

  INLINE_RE.lastIndex = 0;

  while ((match = INLINE_RE.exec(text)) !== null) {
    // Push any plain text before this match
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }

    const key = `md-${match.index}`;

    if (match[1]) {
      // **bold**
      parts.push(<strong key={key}>{match[2]}</strong>);
    } else if (match[3]) {
      // *italic*
      parts.push(<em key={key}>{match[4]}</em>);
    } else if (match[5]) {
      // `code`
      parts.push(<code key={key}>{match[6]}</code>);
    } else if (match[7]) {
      // ~~strikethrough~~
      parts.push(<del key={key}>{match[8]}</del>);
    } else if (match[9]) {
      // [text](url) — only allow http/https
      parts.push(
        <a key={key} href={match[11]} target="_blank" rel="noopener noreferrer">
          {match[10]}
        </a>,
      );
    } else if (match[12]) {
      // #hashtag
      parts.push(
        <a key={key} href={`/hashtag/${match[13]}`}>
          #{match[13]}
        </a>,
      );
    } else if (match[14]) {
      // Bare URL
      parts.push(
        <a key={key} href={match[14]} target="_blank" rel="noopener noreferrer">
          {match[14]}
        </a>,
      );
    }

    lastIndex = INLINE_RE.lastIndex;
  }

  // Remaining text after last match
  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return parts.length ? parts : [text];
}

function parseLine(line, lineIdx) {
  const inline = parseInline(line);
  return inline.map((part, i) =>
    typeof part === "string" ? <span key={`${lineIdx}-${i}`}>{part}</span> : part,
  );
}

export default function MarkdownContent({ children, className, as: Tag = "div" }) {
  const rendered = useMemo(() => {
    if (!children || typeof children !== "string") return null;

    const lines = children.split("\n");

    return lines.flatMap((line, i) => {
      const elements = parseLine(line, i);
      // Add <br /> between lines (not after the last one)
      if (i < lines.length - 1) {
        return [...elements, <br key={`br-${i}`} />];
      }
      return elements;
    });
  }, [children]);

  if (!rendered) return null;

  return <Tag className={className}>{rendered}</Tag>;
}
