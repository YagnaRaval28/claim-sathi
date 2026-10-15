import { Suspense } from "react";

// Case pages read the case id from the URL at runtime; with Cache Components that must stream inside Suspense.
export default function CaseLayout({ children }: LayoutProps<"/[lang]/cases/[id]">) {
  return <Suspense fallback={<div className="page" aria-busy="true" />}>{children}</Suspense>;
}
