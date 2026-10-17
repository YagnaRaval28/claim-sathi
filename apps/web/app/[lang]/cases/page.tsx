"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Disclaimer, PageTitle, ProblemNote } from "@/components/ui";
import { api } from "@/lib/api";
import { nextStep, type CaseSummary } from "@/lib/cases";
import { formatDateDmy } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import { useRequireUser } from "@/lib/use-session";

type Note = { id: string; case_id: string; case_nickname: string; kind: string; read: boolean; email_failed: boolean;
  path: string };

export default function Cases() {
  const { t, href } = useI18n();
  const { me, gate } = useRequireUser();
  const [cases, setCases] = useState<CaseSummary[] | null>(null);
  const [notes, setNotes] = useState<Note[]>([]);
  const [error, setError] = useState<unknown>(null);

  const loadNotes = useCallback(
    () => api<{ items: Note[] }>("/notifications").then((r) => setNotes(r.items.filter((n) => !n.read))).catch(() => undefined),
    [],
  );
  useEffect(() => {
    if (!me) return;
    api<{ items: CaseSummary[] }>("/cases").then((r) => setCases(r.items)).catch(setError);
    void loadNotes();
  }, [me, loadNotes]);

  async function markRead(id: string) {
    await api(`/notifications/${id}/read`, { body: {} }).catch(() => undefined);
    await loadNotes();
  }

  const noteText = (kind: string) => kind.startsWith("limitation_")
    ? t("notifications.kinds.limitation", { days: kind.split("_")[1] }) : t(`notifications.kinds.${kind}`);

  if (!me) return gate;
  return (
    <div className="page">
      <PageTitle>{t("cases.title")}</PageTitle>
      <ProblemNote error={error} />
      {notes.length > 0 && (
        <section aria-labelledby="notes-title">
          <h2 id="notes-title">{t("notifications.title")}</h2>
          {notes.map((n) => (
            <div className="card ledger-row" key={n.id}>
              <div>
                <strong>{n.case_nickname}</strong>
                <p style={{ margin: 0 }}>{noteText(n.kind)}</p>
                {n.email_failed && <span className="pill pill-warning">⚠ {t("notifications.emailFailed")}</span>}
              </div>
              <div>
                <Link className="btn btn-secondary" href={href(n.path)} onClick={() => void markRead(n.id)}>
                  {t("notifications.open")}
                </Link>{" "}
                <button className="btn btn-ghost" onClick={() => markRead(n.id)}>{t("notifications.markRead")}</button>
              </div>
            </div>
          ))}
        </section>
      )}
      {cases === null && !error && <p>{t("common.loading")}</p>}
      {cases?.length === 0 && <div className="card"><p>{t("cases.empty")}</p></div>}
      {cases?.map((c) => (
        <div className="card" key={c.id}>
          <h3>{c.nickname}</h3>
          <p className="muted">
            {c.insurer_name ?? "—"} · {t(`cases.stage.${c.stage}`)} · {t("cases.documents", { count: c.documents.length })}
          </p>
          {c.next_deadline && (
            <p>{t("cases.nextDeadline", { what: t(`track.deadlineKinds.${c.next_deadline.kind}`),
              date: formatDateDmy(c.next_deadline.due_date) })}</p>
          )}
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
