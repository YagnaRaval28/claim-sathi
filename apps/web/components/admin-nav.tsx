"use client";

import Link from "next/link";

// Admin console navigation (English-only, product decision).
export function AdminNav({ current }: { current: "queue" | "sources" | "rules" | "accuracy" }) {
  const items = [["queue", "/en/admin", "Review queue"], ["sources", "/en/admin/sources", "Knowledge base"],
    ["rules", "/en/admin/rules", "Rules"], ["accuracy", "/en/admin/accuracy", "Accuracy audits"]] as const;
  return (
    <nav aria-label="Admin" style={{ display: "flex", gap: 16, marginBottom: 16 }}>
      {items.map(([key, href, label]) => (
        <Link key={key} href={href} aria-current={key === current ? "page" : undefined}
              style={{ fontWeight: key === current ? 700 : 400 }}>{label}</Link>
      ))}
    </nav>
  );
}
