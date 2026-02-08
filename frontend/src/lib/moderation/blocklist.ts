/**
 * Client-side keyword blocklist for chat moderation.
 *
 * MVP approach: block obvious offensive words before sending.
 * The peer review system (Green/Red/Skip) acts as the primary
 * social accountability mechanism.
 */

const BLOCKED_PATTERNS: RegExp[] = [
  // Slurs and hate speech (case-insensitive)
  /\bn[i1]gg[ae3]r?\b/i,
  /\bf[a@]gg?[o0]t\b/i,
  /\br[e3]t[a@]rd\b/i,
  /\bk[i1]ke\b/i,
  /\bch[i1]nk\b/i,
  /\bsp[i1]c\b/i,
  // Sexual harassment
  /\bsend\s*nudes?\b/i,
  /\bd[i1]ck\s*pic\b/i,
  // Spam patterns
  /(.)\1{9,}/, // 10+ repeated characters
  /https?:\/\/\S+/i, // URLs (prevent link spam)
];

/**
 * Check if a message contains blocked content.
 * Returns true if the message should be blocked.
 */
export function isBlocked(text: string): boolean {
  return BLOCKED_PATTERNS.some((pattern) => pattern.test(text));
}
