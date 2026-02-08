"use client";

import { useRef, useEffect, useState } from "react";
import { cn } from "@/lib/utils";

const PRESET_REASONS = [
  { value: "absent_no_show", label: "Was absent / no-show" },
  { value: "disruptive_behavior", label: "Disruptive behavior" },
  { value: "left_early_no_notice", label: "Left early without notice" },
  { value: "not_actually_working", label: "Not actually working" },
  { value: "other", label: "Other" },
] as const;

interface RatingReasonsPickerProps {
  reasons: string[];
  otherText: string;
  onReasonsChange: (reasons: string[]) => void;
  onOtherTextChange: (text: string) => void;
}

export function RatingReasonsPicker({
  reasons,
  otherText,
  onReasonsChange,
  onOtherTextChange,
}: RatingReasonsPickerProps) {
  const contentRef = useRef<HTMLDivElement>(null);
  const [height, setHeight] = useState<number>(0);

  useEffect(() => {
    if (contentRef.current) {
      setHeight(contentRef.current.scrollHeight);
    }
  }, [reasons]);

  const toggleReason = (value: string) => {
    if (reasons.includes(value)) {
      onReasonsChange(reasons.filter((r) => r !== value));
    } else {
      onReasonsChange([...reasons, value]);
    }
  };

  const showOtherInput = reasons.includes("other");

  return (
    <div
      className="overflow-hidden transition-all duration-300 ease-in-out"
      style={{ height: height > 0 ? `${height}px` : "auto" }}
    >
      <div ref={contentRef} className="pt-3 space-y-2">
        <p className="text-xs text-muted-foreground font-medium">
          What happened? (select all that apply)
        </p>
        <div className="space-y-1.5">
          {PRESET_REASONS.map((reason) => (
            <label
              key={reason.value}
              className={cn(
                "flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm cursor-pointer",
                "border transition-colors duration-150",
                reasons.includes(reason.value)
                  ? "border-destructive/40 bg-destructive/10 text-foreground"
                  : "border-border bg-card hover:bg-muted"
              )}
            >
              <input
                type="checkbox"
                checked={reasons.includes(reason.value)}
                onChange={() => toggleReason(reason.value)}
                className="sr-only"
              />
              <span
                className={cn(
                  "flex h-4 w-4 shrink-0 items-center justify-center rounded border",
                  reasons.includes(reason.value)
                    ? "border-destructive bg-destructive text-destructive-foreground"
                    : "border-border bg-input"
                )}
              >
                {reasons.includes(reason.value) && (
                  <svg
                    className="h-3 w-3"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={3}
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                )}
              </span>
              <span>{reason.label}</span>
            </label>
          ))}
        </div>

        {showOtherInput && (
          <div className="pt-1">
            <textarea
              value={otherText}
              onChange={(e) => onOtherTextChange(e.target.value)}
              placeholder="Please describe what happened..."
              maxLength={500}
              rows={3}
              className={cn(
                "w-full rounded-lg border border-border bg-input px-3 py-2",
                "text-sm text-foreground placeholder:text-muted-foreground",
                "focus:outline-none focus:ring-2 focus:ring-ring/50 focus:border-ring",
                "resize-none"
              )}
            />
            <p className="text-xs text-muted-foreground text-right mt-1">{otherText.length}/500</p>
          </div>
        )}
      </div>
    </div>
  );
}
