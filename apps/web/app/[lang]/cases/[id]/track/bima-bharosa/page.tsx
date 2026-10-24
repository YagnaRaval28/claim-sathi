"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { ExternalLink } from "@/components/content-page";
import { CaseSteps, Disclaimer, PageTitle, ProblemNote, ProvenanceTag } from "@/components/ui";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { useRequireUser } from "@/lib/use-session";

type Field = { key: string; value: string; length: number };
type Content = { fields: Field[]; portal_url: string; toll_free: string };

/** CopyField (design CASE-08): label, read-only value, character count (no truncation, OQ-04) and Copy. */
function CopyField({ field }: { field: Field }) {
  const { t } = useI18n();
  const [copied, setCopied] = useState(false);
  const box = useRef<HTMLTextAreaElement>(null);
  async function copy() {
    try {
      await navigator.clipboard.writeText(field.value);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      box.current?.select(); // clipboard unavailable: select the text so the user can copy it
    }
  }
  const id = `bb-${field.key}`;
  return (
    <div className="field">
      <label htmlFor={id}>{t(`bima.fields.${field.key}`)}</label>
      <textarea id={id} ref={box} className="input" readOnly value={field.value} lang="en"
                rows={field.key === "grounds" || field.key === "summary" ? 6 : 1} />
      <div className="ledger-row">
        <span className="muted">{t("bima.count", { n: field.length })}</span>
        <button type="button" className="btn btn-secondary" onClick={copy} aria-live="polite">
          {copied ? `${t("bima.copied")} ✓` : t("bima.copy")}
        </button>
      </div>
    </div>
  );
}

// FR-025 (P1): copy-ready content for a Bima Bharosa complaint, built from confirmed facts and verified grounds.
export default function BimaBharosa() {
  const { t, href } = useI18n();
  const { id } = useParams<{ id: string }>();
  const { me, gate } = useRequireUser();
  const [content, setContent] = useState<Content | null>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    if (!me) return;
    api<Content>(`/cases/${id}/packs/bima-bharosa`).then(setContent).catch(setError);
  }, [me, id]);

  if (!me) return gate;
  return (
    <div className="page">
      <CaseSteps caseId={id} current="track" />
      <PageTitle>{t("bima.title")}</PageTitle>
      <p>{t("bima.intro")}</p>
      <ProblemNote error={error} />
      {content && (
        <>
          <div className="card">
            <p style={{ marginTop: 0 }}>
              <ExternalLink href={content.portal_url}>bimabharosa.irdai.gov.in</ExternalLink>
              {" · "}<a href={`tel:${content.toll_free}`}>{t("bima.call", { number: content.toll_free })}</a>
            </p>
            <p className="muted" style={{ marginBottom: 0 }}>{t("bima.free")}</p>
          </div>
          <div className="card">
            {content.fields.map((f) => <CopyField key={f.key} field={f} />)}
            <ProvenanceTag kind="rule" /> <ProvenanceTag kind="document" />
            <p className="muted">{t("bima.english")}</p>
          </div>
        </>
      )}
      <Link className="btn btn-secondary" href={href(`/cases/${id}/track`)}>← {t("bima.back")}</Link>
      <Disclaimer />
    </div>
  );
}
