// Indian digit grouping and DD/MM/YYYY (design §5.2.3; DD-03: Western Arabic numerals in every language).

export function formatInr(paise: number): string {
  const rupees = Math.floor(paise / 100);
  const p = paise % 100;
  const s = String(rupees);
  let out = s;
  if (s.length > 3) {
    let head = s.slice(0, -3);
    const tail = s.slice(-3);
    const groups: string[] = [];
    while (head.length > 2) {
      groups.unshift(head.slice(-2));
      head = head.slice(0, -2);
    }
    if (head) groups.unshift(head);
    out = [...groups, tail].join(",");
  }
  return `₹${out}${p ? "." + String(p).padStart(2, "0") : ""}`;
}

export function formatDateDmy(iso: string): string {
  const [y, m, d] = iso.split("-");
  return `${d}/${m}/${y}`;
}

export function parseRupeesToPaise(text: string): number | null {
  const m = text.replace(/[₹\s]|rs\.?|inr/gi, "").replace(/,/g, "").match(/^(\d+)(?:\.(\d{1,2}))?$/);
  if (!m) return null;
  return Number(m[1]) * 100 + Number((m[2] ?? "0").padEnd(2, "0"));
}
