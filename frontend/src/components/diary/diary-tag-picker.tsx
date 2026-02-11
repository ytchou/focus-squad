"use client";

import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";

const PREDEFINED_TAGS = [
  { value: "productive", labelKey: "productiveTag" },
  { value: "distracted", labelKey: "distractedTag" },
  { value: "breakthrough", labelKey: "breakthroughTag" },
  { value: "tired", labelKey: "tiredTag" },
  { value: "energized", labelKey: "energizedTag" },
  { value: "social", labelKey: "socialTag" },
  { value: "deep-focus", labelKey: "deepFocusTag" },
  { value: "struggled", labelKey: "struggledTag" },
] as const;

interface DiaryTagPickerProps {
  selectedTags: string[];
  onChange: (tags: string[]) => void;
}

export function DiaryTagPicker({ selectedTags, onChange }: DiaryTagPickerProps) {
  const t = useTranslations("diary");

  const toggleTag = (tag: string) => {
    if (selectedTags.includes(tag)) {
      onChange(selectedTags.filter((tg) => tg !== tag));
    } else {
      onChange([...selectedTags, tag]);
    }
  };

  return (
    <div className="space-y-2">
      <p className="text-sm font-medium text-foreground">{t("sessionTags")}</p>
      <div className="flex flex-wrap gap-2">
        {PREDEFINED_TAGS.map((tag) => {
          const isSelected = selectedTags.includes(tag.value);
          return (
            <button
              key={tag.value}
              type="button"
              onClick={() => toggleTag(tag.value)}
              className={cn(
                "rounded-full px-3 py-1 text-xs font-medium transition-colors",
                isSelected
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted text-muted-foreground hover:bg-muted/80"
              )}
            >
              {t(tag.labelKey)}
            </button>
          );
        })}
      </div>
    </div>
  );
}
