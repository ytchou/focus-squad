import type { SessionPhase } from "@/stores/session-store";
import { formatTime } from "@/lib/session/phase-utils";
import {
  PHASE_BG_COLORS,
  PHASE_TEXT_COLORS,
  PHASE_LABELS,
  PRESENCE_BORDER_COLORS,
  PIP_BG_DARK,
  PIP_TEXT_LIGHT,
  PIP_TEXT_DIM,
  type PiPParticipant,
} from "./pip-colors";

const WIDTH = 320;
const HEIGHT = 180;
const TIMER_SECTION_HEIGHT = 100;
const AVATAR_SECTION_HEIGHT = HEIGHT - TIMER_SECTION_HEIGHT;
const AVATAR_RADIUS = 16;
const AVATAR_BORDER = 3;
const AVATAR_SPACING = WIDTH / 5; // 5 slots for 4 centered avatars

export interface PiPRenderState {
  phase: SessionPhase;
  timeRemaining: number;
  participants: PiPParticipant[];
}

export class PiPCanvasRenderer {
  private canvas: HTMLCanvasElement;
  private ctx: CanvasRenderingContext2D;

  constructor() {
    this.canvas = document.createElement("canvas");
    this.canvas.width = WIDTH;
    this.canvas.height = HEIGHT;
    const ctx = this.canvas.getContext("2d");
    if (!ctx) throw new Error("Canvas 2D context not available");
    this.ctx = ctx;
  }

  getCanvas(): HTMLCanvasElement {
    return this.canvas;
  }

  render(state: PiPRenderState): void {
    const { ctx } = this;
    const { phase, timeRemaining, participants } = state;

    // Timer section background
    ctx.fillStyle = PHASE_BG_COLORS[phase];
    ctx.fillRect(0, 0, WIDTH, TIMER_SECTION_HEIGHT);

    // Timer text
    const timerText = formatTime(timeRemaining);
    ctx.fillStyle = PHASE_TEXT_COLORS[phase];
    ctx.font = "bold 32px system-ui, -apple-system, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(timerText, WIDTH / 2, TIMER_SECTION_HEIGHT / 2 - 8);

    // Phase label
    ctx.font = "12px system-ui, -apple-system, sans-serif";
    ctx.fillStyle = PHASE_TEXT_COLORS[phase];
    ctx.globalAlpha = 0.7;
    ctx.fillText(PHASE_LABELS[phase], WIDTH / 2, TIMER_SECTION_HEIGHT / 2 + 18);
    ctx.globalAlpha = 1;

    // Avatar section background
    ctx.fillStyle = PIP_BG_DARK;
    ctx.fillRect(0, TIMER_SECTION_HEIGHT, WIDTH, AVATAR_SECTION_HEIGHT);

    // Draw up to 4 participant avatars
    const count = Math.min(participants.length, 4);
    for (let i = 0; i < count; i++) {
      const p = participants[i];
      const cx = AVATAR_SPACING * (i + 1);
      const cy = TIMER_SECTION_HEIGHT + AVATAR_SECTION_HEIGHT / 2 - 8;

      this.drawAvatar(ctx, cx, cy, p);
    }
  }

  private drawAvatar(
    ctx: CanvasRenderingContext2D,
    cx: number,
    cy: number,
    participant: PiPParticipant
  ): void {
    const borderColor = PRESENCE_BORDER_COLORS[participant.presenceState];
    const initial = (participant.displayName || "?")[0].toUpperCase();

    // Presence-colored border ring
    ctx.beginPath();
    ctx.arc(cx, cy, AVATAR_RADIUS + AVATAR_BORDER, 0, Math.PI * 2);
    ctx.fillStyle = borderColor;
    ctx.fill();

    // Inner circle
    ctx.beginPath();
    ctx.arc(cx, cy, AVATAR_RADIUS, 0, Math.PI * 2);
    ctx.fillStyle = "#5a5045";
    ctx.fill();

    // Initial letter
    ctx.fillStyle = PIP_TEXT_LIGHT;
    ctx.font = "bold 14px system-ui, -apple-system, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(initial, cx, cy);

    // Name label below
    const name = (participant.displayName || "?").slice(0, 8);
    ctx.fillStyle = PIP_TEXT_DIM;
    ctx.font = "10px system-ui, -apple-system, sans-serif";
    ctx.fillText(name, cx, cy + AVATAR_RADIUS + AVATAR_BORDER + 12);
  }

  destroy(): void {
    // Allow GC
    (this as Record<string, unknown>).canvas = null;
    (this as Record<string, unknown>).ctx = null;
  }
}
