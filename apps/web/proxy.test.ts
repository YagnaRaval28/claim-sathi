import { describe, expect, it } from "vitest";
import { pickLang } from "./proxy";

describe("pickLang (Accept-Language)", () => {
  it.each([
    ["hi-IN,hi;q=0.9,en-US;q=0.8,en;q=0.7", "hi"],
    ["en-US,en;q=0.9,gu;q=0.8", "en"],
    ["gu-IN", "gu"],
    ["fr-FR,fr;q=0.9", "en"],
    ["en;q=0.5,hi;q=0.8", "hi"],
    ["hi;q=0", "en"],
    ["", "en"],
  ])("%s -> %s", (header, lang) => expect(pickLang(header)).toBe(lang));
});
