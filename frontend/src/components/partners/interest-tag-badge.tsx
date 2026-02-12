"use client";

import { useTranslations } from "next-intl";

interface InterestTagBadgeProps {
  tag: string;
}

export function InterestTagBadge({ tag }: InterestTagBadgeProps) {
  const t = useTranslations("partners");

  return (
    <span className="inline-flex items-center rounded-full border border-border bg-muted/50 px-2 py-0.5 text-xs text-muted-foreground">
      {t(`tags.${tag}`)}
    </span>
  );
}
