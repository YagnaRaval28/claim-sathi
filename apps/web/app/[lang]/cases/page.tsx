"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Disclaimer, PageTitle, ProblemNote } from "@/components/ui";
import { api } from "@/lib/api";
import { nextStep, type CaseSummary } from "@/lib/cases";
import { useI18n } from "@/lib/i18n";
import { useRequireUser } from "@/lib/use-session";

export default function Cases() {
  const { t, href } = useI18n();
  const { me, gate } = useRequireUser();
  const [cases, setCases] = useState<CaseSummary[] | null>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    if (me) api<{ items: CaseSummary[] }>("/cases").then((r) => setCases(r.items)).catch(setError);
  }, [me]);

  if (!me) return gate;
  return (
    <div className="page">
      <PageTitle>{t("cases.title")}</PageTitle>
      <ProblemNote error={error} />
      {cases === null && !error && <p>{t("common.loading")}</p>}
      {cases?.length === 0 && <div className="card"><p>{t("cases.empty")}</p></div>}
      {cases?.map((c) => (
        <div className="card" key={c.id}>
          <h3>{c.nickname}</h3>
          <p className="muted">{c.insurer_name ?? "—"} · {t("cases.documents", { count: c.documents.length })}</p>
          <Link className="btn btn-secondary" href={href(`/cases/${c.id}/${nextStep(c)}`)}>{t("cases.continue")} →</Link>
        </div>
      ))}
      <div className="action-bar">
        <Link className="btn btn-primary btn-block" href={href("/cases/new")}>+ {t("cases.new")}</Link>
      </div>
      <Disclaimer />
    </div>
  );
}
