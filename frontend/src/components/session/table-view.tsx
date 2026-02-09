"use client";

import { ParticipantSeat, type ParticipantSeatProps } from "./participant-seat";

interface TableViewProps {
  participants: (Omit<ParticipantSeatProps, "isSpeaking"> & { livekitIdentity: string | null })[];
  speakingParticipantIds: Set<string>;
  currentUserId: string | null;
}

/**
 * 2x2 grid layout for 4 participant seats.
 * Seats are numbered 1-4 in reading order:
 * [1] [2]
 * [3] [4]
 */
export function TableView({ participants, speakingParticipantIds, currentUserId }: TableViewProps) {
  // Create a map of seat number to participant
  const seatMap = new Map<number, (typeof participants)[0]>();
  for (const p of participants) {
    seatMap.set(p.seatNumber, p);
  }

  // Generate all 4 seats
  const seats = [1, 2, 3, 4].map((seatNumber) => {
    const participant = seatMap.get(seatNumber);

    if (!participant) {
      return (
        <ParticipantSeat
          key={seatNumber}
          id={`empty-${seatNumber}`}
          seatNumber={seatNumber}
          username={null}
          displayName={null}
          isAI={false}
          isMuted={true}
          presenceState="active"
          isSpeaking={false}
          isCurrentUser={false}
          isEmpty={true}
        />
      );
    }

    // Use livekitIdentity (LiveKit identity = user_id) for speaking detection
    const isSpeaking = participant.livekitIdentity
      ? speakingParticipantIds.has(participant.livekitIdentity)
      : false;

    return (
      <ParticipantSeat
        key={participant.id}
        {...participant}
        isSpeaking={isSpeaking}
        isCurrentUser={participant.id === currentUserId}
      />
    );
  });

  return <div className="grid grid-cols-2 gap-4 w-full max-w-md">{seats}</div>;
}
