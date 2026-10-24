import { describe, expect, it } from "vitest";
import { BANNED_PHRASES, explanation, type ExplainInput } from "./explain";
import en from "../messages/en.json";
import gu from "../messages/gu.json";
import hi from "../messages/hi.json";

type Dict = Record<string, unknown>;
const DICTS = { en, gu, hi } as Record<string, Dict>;

function translator(dict: Dict) {
  return (key: string, vars: Record<string, string | number> = {}) => {
    const v = key.split(".").reduce<unknown>((o, k) => (o as Dict)[k], dict);
    if (typeof v !== "string") throw new Error(`missing ${key}`);
    return v.replace(/\{(\w+)\}/g, (_, k: string) => String(vars[k]));
  };
}

const PARTIAL: ExplainInput = {
  decisionType: "partial", claimedPaise: 26482000, paidPaise: 21050000, noClause: { count: 3, paise: 2590000 },
  reasonsNoClause: 0, categories: ["non_payable_items", "room_rent_proportionate", "other_unknown"], canWrite: true,
};
const REJECTED: ExplainInput = {
  decisionType: "repudiation", claimedPaise: 18500000, paidPaise: null, noClause: { count: 0, paise: 0 },
  reasonsNoClause: 1, categories: ["non_disclosure"], canWrite: true,
};

describe("FR-017 explanation", () => {
  it.each(["en", "gu", "hi"])("uses only confirmed figures and stays within 150 words (%s)", (lang) => {
    for (const input of [PARTIAL, REJECTED]) {
      const text = explanation(input, translator(DICTS[lang])).join(" ");
      const numbers = text.match(/[\d][\d,]*/g) ?? [];
      // AC1: every number is a confirmed amount, a sum of confirmed deductions, or the count of items.
      const allowed = new Set(["2,64,820", "2,10,500", "25,900", "3", "1,85,000", "1"]);
      expect(numbers.filter((n) => !allowed.has(n))).toEqual([]);
      expect(text.split(/\s+/).length).toBeLessThanOrEqual(150);
    }
  });

  it("states the decision, the reasons in plain words and the next step", () => {
    const lines = explanation(PARTIAL, translator(en as Dict));
    expect(lines[0]).toBe("Your insurer paid ₹2,10,500 of ₹2,64,820.");
    expect(lines.join(" ")).toContain("Items the policy doesn't pay for");
    expect(lines.join(" ")).not.toContain("not sure");
    expect(lines.at(-1)).toMatch(/^Next step: write to the insurer's grievance officer/);
    expect(explanation({ ...REJECTED, canWrite: false }, translator(en as Dict)).at(-1)).toMatch(/^Next step: ask/);
  });

  it.each(["en", "gu", "hi"])("contains no banned predictive phrase (%s)", (lang) => {
    const all = JSON.stringify((DICTS[lang].findings as Dict).explain).toLowerCase();
    for (const phrase of BANNED_PHRASES) expect(all).not.toContain(phrase);
    for (const input of [PARTIAL, REJECTED]) {
      const text = explanation(input, translator(DICTS[lang])).join(" ").toLowerCase();
      for (const phrase of BANNED_PHRASES) expect(text).not.toContain(phrase);
    }
  });
});

describe("PUB-06 glossary", () => {
  it("has the same terms, in the same order, in every language", () => {
    const ids = (lang: string) => ((DICTS[lang].glossary as Dict).terms as string[][]).map(([id]) => id);
    expect(ids("gu")).toEqual(ids("en"));
    expect(ids("hi")).toEqual(ids("en"));
  });
});
