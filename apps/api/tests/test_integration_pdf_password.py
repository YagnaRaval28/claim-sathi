"""Password-protected PDFs (PRD FR-008 AC3): processed after the right password, which is never stored or logged."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Text, cast, func, literal_column, select, table, text

from claimsathi.context import AppContext
from tests.conftest import sign_in
from tests.test_integration_vs1 import _new_case

pytestmark = pytest.mark.integration
PASSWORD = "01011980"  # a date of birth, the usual pattern for insurer letters (SYNTHETIC fixture)
PROTECTED = (Path(__file__).resolve().parents[3] / "eval/fixtures/documents/SYN-001-password-01011980.pdf").read_bytes()


def _protected_case(client: TestClient, ctx: AppContext, email: str) -> tuple[dict[str, str], str, dict[str, Any]]:
    h = sign_in(client, ctx, email)
    cid = _new_case(client, h)["id"]
    r = client.post(
        f"/api/v1/cases/{cid}/documents",
        headers=h,
        data={"type": "decision_letter"},
        files={"file": ("letter.pdf", PROTECTED, "application/pdf")},
    )
    assert r.status_code == 202, r.text
    doc = client.get(f"/api/v1/cases/{cid}").json()["documents"][0]
    return h, cid, doc


def _unlock(client: TestClient, h: dict[str, str], cid: str, doc_id: str, password: str) -> Any:
    return client.post(f"/api/v1/cases/{cid}/documents/{doc_id}/unlock", json={"password": password}, headers=h)


@pytest.mark.req("FR-008")
def test_protected_pdf_is_read_after_the_right_password(
    client: TestClient, ctx: AppContext, capsys: pytest.CaptureFixture[str]
) -> None:
    h, cid, doc = _protected_case(client, ctx, "protected@example.com")
    assert doc["status"] == "needs_attention" and doc["status_reason"] == "password_required"

    r = _unlock(client, h, cid, doc["id"], "31121999")
    assert r.status_code == 422 and r.json()["code"] == "pdf_password_incorrect"
    assert client.get(f"/api/v1/cases/{cid}").json()["documents"][0]["status_reason"] == "password_required"

    r = _unlock(client, h, cid, doc["id"], PASSWORD)
    assert r.status_code == 202, r.text
    assert client.get(f"/api/v1/cases/{cid}").json()["documents"][0]["status"] == "ready"
    facts = {f["name"]: f for f in client.get(f"/api/v1/cases/{cid}/facts").json()["fields"]}
    assert facts["claimed_paise"]["display"] == "₹2,64,820"  # read from the unlocked text

    # AC3: the password is in no database row and no log line.
    assert PASSWORD not in capsys.readouterr().out
    with ctx.session_factory() as s:
        tables = s.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename <> 'alembic_version'")
        ).scalars()
        for t in tables:
            row = cast(literal_column("x"), Text)  # the whole row as text
            q = select(func.count()).select_from(table(t).alias("x")).where(row.like(f"%{PASSWORD}%"))
            assert s.execute(q).scalar_one() == 0, t


def test_unlock_only_applies_to_a_protected_pdf_and_is_rate_limited(client: TestClient, ctx: AppContext) -> None:
    h, cid, doc = _protected_case(client, ctx, "protected-limit@example.com")
    for _ in range(10):
        assert _unlock(client, h, cid, doc["id"], "wrong").status_code == 422
    assert _unlock(client, h, cid, doc["id"], PASSWORD).status_code == 429  # even the right one waits
    plain = sign_in(client, ctx, "plain-unlock@example.com")
    other = _new_case(client, plain)["id"]
    from tests.test_integration_vs1 import _upload_syn001

    _upload_syn001(client, plain, other)
    plain_doc = client.get(f"/api/v1/cases/{other}").json()["documents"][0]
    r = _unlock(client, plain, other, plain_doc["id"], PASSWORD)
    assert r.status_code == 409 and r.json()["code"] == "not_password_protected"
