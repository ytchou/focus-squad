export type PresenceState = "active" | "grace" | "away" | "ghosting";

export interface PresenceMessage {
  type: "presence";
  userId: string;
  presenceState: PresenceState;
  timestamp: number;
}
