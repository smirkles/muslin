/**
 * Pure utility functions for the Iris Tailor frontend.
 */

/**
 * Returns `s` reversed by Unicode codepoint.
 *
 * Uses `.split("").reverse().join("")`, which operates on UTF-16 code units
 * (BMP codepoints). Surrogate pairs (astral codepoints) and multi-codepoint
 * grapheme clusters (e.g. ZWJ emoji sequences, combining characters) are NOT
 * handled correctly — this is intentional and matches the spec scope.
 */
export function reverseString(s: string): string {
  return s.split("").reverse().join("");
}
