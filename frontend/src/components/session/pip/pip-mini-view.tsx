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

interface PiPMiniViewProps {
  phase: SessionPhase;
  timeRemaining: number;
  participants: PiPParticipant[];
}

function ParticipantDot({ participant }: { participant: PiPParticipant }) {
  const initial = (participant.displayName || "?")[0].toUpperCase();
  const name = (participant.displayName || "?").slice(0, 8);
  const borderColor = PRESENCE_BORDER_COLORS[participant.presenceState];

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
      <div
        style={{
          width: 38,
          height: 38,
          borderRadius: "50%",
          border: `3px solid ${borderColor}`,
          backgroundColor: "#5a5045",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <span style={{ color: PIP_TEXT_LIGHT, fontSize: 14, fontWeight: "bold" }}>{initial}</span>
      </div>
      <span
        style={{
          color: PIP_TEXT_DIM,
          fontSize: 10,
          maxWidth: 56,
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap",
          textAlign: "center",
        }}
      >
        {name}
      </span>
    </div>
  );
}

export function PiPMiniView({ phase, timeRemaining, participants }: PiPMiniViewProps) {
  const timerText = formatTime(timeRemaining);
  const phaseBg = PHASE_BG_COLORS[phase];
  const phaseText = PHASE_TEXT_COLORS[phase];

  return (
    <div
      style={{
        width: 320,
        height: 180,
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
        fontFamily: "system-ui, -apple-system, sans-serif",
        margin: 0,
        padding: 0,
      }}
    >
      {/* Timer section */}
      <div
        style={{
          flex: 1,
          background: phaseBg,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <div style={{ fontSize: 32, fontWeight: "bold", color: phaseText, letterSpacing: 2 }}>
          {timerText}
        </div>
        <div style={{ fontSize: 12, color: phaseText, opacity: 0.7, marginTop: 2 }}>
          {PHASE_LABELS[phase]}
        </div>
      </div>

      {/* Participants section */}
      <div
        style={{
          height: 80,
          background: PIP_BG_DARK,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-evenly",
          padding: "0 12px",
        }}
      >
        {participants.slice(0, 4).map((p, i) => (
          <ParticipantDot key={i} participant={p} />
        ))}
      </div>
    </div>
  );
}
