"use client";

import { useState, useRef, useEffect } from "react";

const REACTIONS = [
  { emoji: "\u{1F44D}", label: "thumbs up" },
  { emoji: "\u2764\uFE0F", label: "heart" },
  { emoji: "\u{1F525}", label: "fire" },
  { emoji: "\u{1F44F}", label: "clap" },
  { emoji: "\u{1F602}", label: "laugh" },
  { emoji: "\u{1F4AF}", label: "100" },
];

interface ReactionPickerProps {
  onSelect: (emoji: string) => void;
  selectedEmojis: string[];
}

export function ReactionPicker({ onSelect, selectedEmojis }: ReactionPickerProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    if (open) {
      document.addEventListener("mousedown", handleClickOutside);
      return () => document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [open]);

  return (
    <div ref={ref} className="relative inline-block">
      <button
        onClick={() => setOpen(!open)}
        className="text-muted-foreground hover:text-foreground text-xs px-1 py-0.5 rounded transition-colors"
        aria-label="Add reaction"
      >
        +
      </button>

      {open && (
        <div className="absolute bottom-full left-0 mb-1 z-50 flex gap-1 bg-card border border-border rounded-xl px-2 py-1.5 shadow-sm">
          {REACTIONS.map(({ emoji, label }) => {
            const isSelected = selectedEmojis.includes(emoji);
            return (
              <button
                key={emoji}
                onClick={() => {
                  onSelect(emoji);
                  setOpen(false);
                }}
                className={`text-base hover:scale-125 transition-transform rounded px-0.5 ${
                  isSelected ? "bg-accent" : ""
                }`}
                aria-label={`React with ${label}`}
              >
                {emoji}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
