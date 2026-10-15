"""Money and date parsing/formatting (paise integers; DD/MM/YYYY; Indian digit grouping)."""

from __future__ import annotations

import re
from datetime import date

from claimsathi.verify.numbers import to_ascii_digits

_AMOUNT = re.compile(r"^\s*(?:₹|rs\.?|inr)?\s*([0-9][0-9,]*)(?:\.([0-9]{1,2}))?\s*(?:/-)?\s*$", re.IGNORECASE)
_DMY = re.compile(r"^\s*(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})\s*$")
_ISO = re.compile(r"^\s*(\d{4})-(\d{2})-(\d{2})\s*$")


def parse_amount_paise(text: str) -> int | None:
    m = _AMOUNT.match(to_ascii_digits(text))
    if not m:
        return None
    rupees = int(m.group(1).replace(",", ""))
    paise = int((m.group(2) or "0").ljust(2, "0"))
    return rupees * 100 + paise


def parse_date(text: str) -> date | None:
    t = to_ascii_digits(text)
    m = _DMY.match(t)
    try:
        if m:
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        m = _ISO.match(t)
        if m:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None
    return None


def format_inr(paise: int) -> str:
    """₹ with Indian grouping: 26482000 -> '₹2,64,820'; paise shown only when non-zero."""
    rupees, p = divmod(paise, 100)
    s = str(rupees)
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        groups: list[str] = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        s = ",".join([*groups, tail])
    return f"₹{s}" + (f".{p:02d}" if p else "")


def format_date_dmy(d: date) -> str:
    return d.strftime("%d/%m/%Y")
