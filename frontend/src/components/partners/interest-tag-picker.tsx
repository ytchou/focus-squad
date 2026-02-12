"use client";

import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";

const AVAILABLE_TAGS = [
  "coding",
  "writing",
  "design",
  "language_learning",
  "exam_prep",
  "reading",
  "research",
  "music_practice",
  "art",
  "job_hunting",
  "data_science",
  "meditation",
] as const;

interface InterestTagPickerProps {
  selected: string[];
  onChange: (tags: string[]) => void;
  maxTags?: number;
}

export function InterestTagPicker({ selected, onChange, maxTags = 5 }: InterestTagPickerProps) {
  const t = useTranslations("partners");

  const toggleTag = (tag: string) => {
    if (selected.includes(tag)) {
      onChange(selected.filter((s) => s !== tag));
    } else if (selected.length < maxTags) {
      onChange([...selected, tag]);
    }
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-foreground">{t("interests")}</p>
        <span className="text-xs text-muted-foreground">
          {selected.length}/{maxTags}
        </span>
      </div>
      <div className="flex flex-wrap gap-2">
        {AVAILABLE_TAGS.map((tag) => {
          const isSelected = selected.includes(tag);
          const isDisabled = !isSelected && selected.length >= maxTags;
          return (
            <button
              key={tag}
              onClick={() => toggleTag(tag)}
              disabled={isDisabled}
              className={cn(
                "rounded-full border px-3 py-1 text-xs font-medium transition-colors",
                isSelected
                  ? "border-accent bg-accent text-accent-foreground"
                  : "border-border bg-card text-foreground hover:border-accent/50",
                isDisabled && "cursor-not-allowed opacity-40"
              )}
            >
              {t(`tags.${tag}`)}
            </button>
          );
        })}
      </div>
    </div>
  );
}
