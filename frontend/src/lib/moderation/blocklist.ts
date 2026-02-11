/**
 * Client-side keyword blocklist for chat moderation.
 *
 * MVP approach: block obvious offensive words before sending.
 * The peer review system (Green/Red/Skip) acts as the primary
 * social accountability mechanism.
 */

type BlockCategory = "slur" | "sexual" | "spam";

interface CategorizedPattern {
  pattern: RegExp;
  category: BlockCategory;
}

const CATEGORIZED_PATTERNS: CategorizedPattern[] = [
  // Slurs and hate speech (case-insensitive)
  { pattern: /\bn[i1]gg[ae3]r?\b/i, category: "slur" },
  { pattern: /\bf[a@]gg?[o0]t\b/i, category: "slur" },
  { pattern: /\br[e3]t[a@]rd\b/i, category: "slur" },
  { pattern: /\bk[i1]ke\b/i, category: "slur" },
  { pattern: /\bch[i1]nk\b/i, category: "slur" },
  { pattern: /\bsp[i1]c\b/i, category: "slur" },
  // Sexual harassment
  { pattern: /\bsend\s*nudes?\b/i, category: "sexual" },
  { pattern: /\bd[i1]ck\s*pic\b/i, category: "sexual" },
  // Spam patterns
  { pattern: /(.)\1{9,}/, category: "spam" }, // 10+ repeated characters
  { pattern: /https?:\/\/\S+/i, category: "spam" }, // URLs (prevent link spam)
];

/**
 * Check if a message contains blocked content.
 * Returns true if the message should be blocked.
 */
export function isBlocked(text: string): boolean {
  return CATEGORIZED_PATTERNS.some(({ pattern }) => pattern.test(text));
}

/**
 * Returns the category of the first matched blocked pattern,
 * or null if no patterns match.
 */
export function getMatchedCategory(text: string): string | null {
  const match = CATEGORIZED_PATTERNS.find(({ pattern }) => pattern.test(text));
  return match?.category ?? null;
}
