export interface AmbientTrack {
  id: string;
  name: string;
  icon: string;
  audioSrc: string;
  defaultVolume: number;
}

export const AMBIENT_TRACKS: AmbientTrack[] = [
  {
    id: "lofi",
    name: "Lo-Fi",
    icon: "Music",
    audioSrc: "/assets/audio/lofi-beats.mp3",
    defaultVolume: 0.5,
  },
  {
    id: "coffee",
    name: "Cafe",
    icon: "Coffee",
    audioSrc: "/assets/audio/coffee-shop.mp3",
    defaultVolume: 0.3,
  },
  {
    id: "rain",
    name: "Rain",
    icon: "CloudRain",
    audioSrc: "/assets/audio/rain.mp3",
    defaultVolume: 0.4,
  },
];

export const AMBIENT_STORAGE_KEY = "focus-squad-ambient-mixer";
