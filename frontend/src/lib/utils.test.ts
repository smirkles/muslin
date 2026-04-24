import { describe, expect, it } from "vitest";

import { reverseString } from "./utils";

describe("reverseString", () => {
  it("reverses a basic string", () => {
    expect(reverseString("hello")).toBe("olleh");
  });

  it("returns empty string for empty input", () => {
    expect(reverseString("")).toBe("");
  });

  it("reverses a Unicode string by codepoint", () => {
    // BMP codepoints: .split("") is codepoint-level for these characters.
    expect(reverseString("café")).toBe("éfac");
  });

  it("returns a single character unchanged", () => {
    expect(reverseString("a")).toBe("a");
  });

  it("returns a palindrome unchanged", () => {
    expect(reverseString("racecar")).toBe("racecar");
  });
});
