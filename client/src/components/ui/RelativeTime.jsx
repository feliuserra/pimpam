import { useEffect, useState } from "react";

const UNITS = [
  { unit: "year", ms: 31536000000 },
  { unit: "month", ms: 2592000000 },
  { unit: "week", ms: 604800000 },
  { unit: "day", ms: 86400000 },
  { unit: "hour", ms: 3600000 },
  { unit: "minute", ms: 60000 },
  { unit: "second", ms: 1000 },
];

const rtf = new Intl.RelativeTimeFormat("en", { numeric: "auto" });

function formatRelative(dateStr) {
  const diff = new Date(dateStr) - Date.now();
  for (const { unit, ms } of UNITS) {
    if (Math.abs(diff) >= ms || unit === "second") {
      return rtf.format(Math.round(diff / ms), unit);
    }
  }
  return "just now";
}

export default function RelativeTime({ date }) {
  const [text, setText] = useState(() => formatRelative(date));

  useEffect(() => {
    setText(formatRelative(date));
    const id = setInterval(() => setText(formatRelative(date)), 60000);
    return () => clearInterval(id);
  }, [date]);

  return <time dateTime={date}>{text}</time>;
}
