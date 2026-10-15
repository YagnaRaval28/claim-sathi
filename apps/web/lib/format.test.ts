import { describe, expect, it } from "vitest";
import { formatDateDmy, formatInr, parseRupeesToPaise } from "./format";
import en from "../messages/en.json";
import gu from "../messages/gu.json";
import hi from "../messages/hi.json";

describe("formatInr", () => {
  it.each([
    [26482000, "₹2,64,820"],
    [125000, "₹1,250"],
    [99, "₹0.99"],
    [1234567800, "₹1,23,45,678"],
  ])("%i -> %s", (paise, text) => expect(formatInr(paise)).toBe(text));
});

describe("dates and parsing", () => {
  it("formats DD/MM/YYYY", () => expect(formatDateDmy("2026-09-10")).toBe("10/09/2026"));
  it("parses rupee text", () => {
    expect(parseRupeesToPaise("Rs. 2,10,500")).toBe(21050000);
    expect(parseRupeesToPaise("₹18,400.5")).toBe(1840050);
    expect(parseRupeesToPaise("abc")).toBeNull();
  });
});

// NFR-021: every key exists in en, gu and hi.
function keys(obj: Record<string, unknown>, prefix = ""): string[] {
  return Object.entries(obj).flatMap(([k, v]) =>
    v && typeof v === "object" ? keys(v as Record<string, unknown>, `${prefix}${k}.`) : [`${prefix}${k}`],
  );
}

describe("translations", () => {
  const base = keys(en).sort();
  it("gu has every en key", () => expect(keys(gu).sort()).toEqual(base));
  it("hi has every en key", () => expect(keys(hi).sort()).toEqual(base));
});
