/**
 * Pixel art room configuration.
 *
 * Maps each room type to its background image path and 4 desk positions.
 * Desk positions are percentage-based relative to the room image dimensions.
 * Positions will be tuned once actual room art is placed.
 */

export interface DeskPosition {
  top: string;
  left: string;
}

export interface RoomConfig {
  id: string;
  name: string;
  backgroundImage: string;
  deskPositions: [DeskPosition, DeskPosition, DeskPosition, DeskPosition];
}

export const PIXEL_ROOMS: Record<string, RoomConfig> = {
  "cozy-study": {
    id: "cozy-study",
    name: "Cozy Study",
    backgroundImage: "/assets/pixel-art/rooms/cozy-study.png",
    deskPositions: [
      { top: "40%", left: "18%" },
      { top: "40%", left: "55%" },
      { top: "62%", left: "12%" },
      { top: "62%", left: "60%" },
    ],
  },
  "coffee-shop": {
    id: "coffee-shop",
    name: "Coffee Shop",
    backgroundImage: "/assets/pixel-art/rooms/coffee-shop.png",
    deskPositions: [
      { top: "38%", left: "15%" },
      { top: "38%", left: "52%" },
      { top: "60%", left: "20%" },
      { top: "60%", left: "58%" },
    ],
  },
  library: {
    id: "library",
    name: "Library",
    backgroundImage: "/assets/pixel-art/rooms/library.png",
    deskPositions: [
      { top: "42%", left: "20%" },
      { top: "42%", left: "58%" },
      { top: "64%", left: "15%" },
      { top: "64%", left: "55%" },
    ],
  },
};

export const DEFAULT_ROOM = "cozy-study";

/**
 * Character sprite configuration.
 */
export interface CharacterConfig {
  id: string;
  name: string;
  spriteSheet: string;
  frameWidth: number;
  frameHeight: number;
  states: {
    working: { frames: number; fps: number; row: number };
    speaking: { frames: number; fps: number; row: number };
    away: { frames: number; fps: number; row: number };
    typing: { frames: number; fps: number; row: number };
    ghosting: { frames: number; fps: number; row: number };
  };
}

export const PIXEL_CHARACTERS: Record<string, CharacterConfig> = {
  "char-1": {
    id: "char-1",
    name: "Scholar",
    spriteSheet: "/assets/pixel-art/characters/char-1-spritesheet.png",
    frameWidth: 64,
    frameHeight: 64,
    states: {
      working: { frames: 4, fps: 4, row: 0 },
      speaking: { frames: 4, fps: 6, row: 1 },
      away: { frames: 3, fps: 3, row: 2 },
      typing: { frames: 3, fps: 5, row: 3 },
      ghosting: { frames: 2, fps: 1, row: 4 },
    },
  },
  "char-2": {
    id: "char-2",
    name: "Artist",
    spriteSheet: "/assets/pixel-art/characters/char-2-spritesheet.png",
    frameWidth: 64,
    frameHeight: 64,
    states: {
      working: { frames: 4, fps: 4, row: 0 },
      speaking: { frames: 4, fps: 6, row: 1 },
      away: { frames: 3, fps: 3, row: 2 },
      typing: { frames: 3, fps: 5, row: 3 },
      ghosting: { frames: 2, fps: 1, row: 4 },
    },
  },
  "char-3": {
    id: "char-3",
    name: "Coder",
    spriteSheet: "/assets/pixel-art/characters/char-3-spritesheet.png",
    frameWidth: 64,
    frameHeight: 64,
    states: {
      working: { frames: 4, fps: 4, row: 0 },
      speaking: { frames: 4, fps: 6, row: 1 },
      away: { frames: 3, fps: 3, row: 2 },
      typing: { frames: 3, fps: 5, row: 3 },
      ghosting: { frames: 2, fps: 1, row: 4 },
    },
  },
  "char-4": {
    id: "char-4",
    name: "Reader",
    spriteSheet: "/assets/pixel-art/characters/char-4-spritesheet.png",
    frameWidth: 64,
    frameHeight: 64,
    states: {
      working: { frames: 4, fps: 4, row: 0 },
      speaking: { frames: 4, fps: 6, row: 1 },
      away: { frames: 3, fps: 3, row: 2 },
      typing: { frames: 3, fps: 5, row: 3 },
      ghosting: { frames: 2, fps: 1, row: 4 },
    },
  },
  "char-5": {
    id: "char-5",
    name: "Musician",
    spriteSheet: "/assets/pixel-art/characters/char-5-spritesheet.png",
    frameWidth: 64,
    frameHeight: 64,
    states: {
      working: { frames: 4, fps: 4, row: 0 },
      speaking: { frames: 4, fps: 6, row: 1 },
      away: { frames: 3, fps: 3, row: 2 },
      typing: { frames: 3, fps: 5, row: 3 },
      ghosting: { frames: 2, fps: 1, row: 4 },
    },
  },
  "char-6": {
    id: "char-6",
    name: "Writer",
    spriteSheet: "/assets/pixel-art/characters/char-6-spritesheet.png",
    frameWidth: 64,
    frameHeight: 64,
    states: {
      working: { frames: 4, fps: 4, row: 0 },
      speaking: { frames: 4, fps: 6, row: 1 },
      away: { frames: 3, fps: 3, row: 2 },
      typing: { frames: 3, fps: 5, row: 3 },
      ghosting: { frames: 2, fps: 1, row: 4 },
    },
  },
  "char-7": {
    id: "char-7",
    name: "Thinker",
    spriteSheet: "/assets/pixel-art/characters/char-7-spritesheet.png",
    frameWidth: 64,
    frameHeight: 64,
    states: {
      working: { frames: 4, fps: 4, row: 0 },
      speaking: { frames: 4, fps: 6, row: 1 },
      away: { frames: 3, fps: 3, row: 2 },
      typing: { frames: 3, fps: 5, row: 3 },
      ghosting: { frames: 2, fps: 1, row: 4 },
    },
  },
  "char-8": {
    id: "char-8",
    name: "Explorer",
    spriteSheet: "/assets/pixel-art/characters/char-8-spritesheet.png",
    frameWidth: 64,
    frameHeight: 64,
    states: {
      working: { frames: 4, fps: 4, row: 0 },
      speaking: { frames: 4, fps: 6, row: 1 },
      away: { frames: 3, fps: 3, row: 2 },
      typing: { frames: 3, fps: 5, row: 3 },
      ghosting: { frames: 2, fps: 1, row: 4 },
    },
  },
};

export const CHARACTER_IDS = Object.keys(PIXEL_CHARACTERS);
export const DEFAULT_CHARACTER = "char-1";
