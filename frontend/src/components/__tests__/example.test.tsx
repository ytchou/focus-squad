import { describe, it, expect } from "vitest";

describe("Example Test Suite", () => {
  it("should pass basic assertion", () => {
    expect(1 + 1).toBe(2);
  });

  it("should validate string operations", () => {
    const greeting = "Hello, Focus Squad!";
    expect(greeting).toContain("Focus Squad");
  });
});
