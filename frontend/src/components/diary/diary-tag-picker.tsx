"use client";

import { cn } from "@/lib/utils";

const PREDEFINED_TAGS = [
  "productive",
  "distracted",
  "breakthrough",
  "tired",
  "energized",
  "social",
  "deep-focus",
  "struggled",
] as const;

interface DiaryTagPickerProps {
  selectedTags: string[];
  onChange: (tags: string[]) => void;
}

export function DiaryTagPicker({ selectedTags, onChange }: DiaryTagPickerProps) {
  const toggleTag = (tag: string) => {
    if (selectedTags.includes(tag)) {
      onChange(selectedTags.filter((t) => t !== tag));
    } else {
      onChange([...selectedTags, tag]);
    }
  };

  return (
    <div className="space-y-2">
      <p className="text-sm font-medium text-foreground">Session tags</p>
      <div className="flex flex-wrap gap-2">
        {PREDEFINED_TAGS.map((tag) => {
          const isSelected = selectedTags.includes(tag);
          return (
            <button
              key={tag}
              type="button"
              onClick={() => toggleTag(tag)}
              className={cn(
                "rounded-full px-3 py-1 text-xs font-medium transition-colors",
                isSelected
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted text-muted-foreground hover:bg-muted/80"
              )}
            >
              {tag}
            </button>
          );
        })}
      </div>
    </div>
  );
}
