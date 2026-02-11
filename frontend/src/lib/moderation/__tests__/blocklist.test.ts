import { describe, it, expect } from "vitest";
import { isBlocked, getMatchedCategory } from "../blocklist";

describe("blocklist", () => {
  describe("isBlocked", () => {
    it("blocks slur patterns", () => {
      expect(isBlocked("you n1gger")).toBe(true);
      expect(isBlocked("f@ggot")).toBe(true);
    });

    it("blocks sexual harassment patterns", () => {
      expect(isBlocked("send nudes")).toBe(true);
      expect(isBlocked("d1ck pic")).toBe(true);
    });

    it("blocks spam patterns", () => {
      expect(isBlocked("aaaaaaaaaa")).toBe(true); // 10+ repeated chars
      expect(isBlocked("visit https://spam.com")).toBe(true);
    });

    it("allows clean messages", () => {
      expect(isBlocked("I'm working on my essay")).toBe(false);
      expect(isBlocked("great session today!")).toBe(false);
      expect(isBlocked("let's focus")).toBe(false);
    });

    it("allows short repeated characters (below threshold)", () => {
      expect(isBlocked("hahaha")).toBe(false);
      expect(isBlocked("noooo")).toBe(false);
    });
  });

  describe("getMatchedCategory", () => {
    it("returns 'slur' for slur patterns", () => {
      expect(getMatchedCategory("you r3tard")).toBe("slur");
      expect(getMatchedCategory("k1ke")).toBe("slur");
    });

    it("returns 'sexual' for sexual harassment patterns", () => {
      expect(getMatchedCategory("send nude")).toBe("sexual");
    });

    it("returns 'spam' for spam patterns", () => {
      expect(getMatchedCategory("aaaaaaaaaaaa")).toBe("spam");
      expect(getMatchedCategory("check https://example.com")).toBe("spam");
    });

    it("returns null for clean messages", () => {
      expect(getMatchedCategory("hello world")).toBeNull();
      expect(getMatchedCategory("keep working!")).toBeNull();
    });

    it("returns first matching category when multiple match", () => {
      // If a message matches multiple categories, returns the first one found
      const result = getMatchedCategory("n1gger https://spam.com");
      expect(result).toBe("slur"); // slur patterns are checked first
    });
  });
});
