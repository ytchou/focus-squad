"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Edit3, Save, X } from "lucide-react";
import { DiaryTagPicker } from "./diary-tag-picker";
import { cn } from "@/lib/utils";

interface DiaryJournalEditorProps {
  initialNote: string;
  initialTags: string[];
  onSave: (note: string, tags: string[]) => Promise<void>;
  isSaving?: boolean;
}

export function DiaryJournalEditor({
  initialNote,
  initialTags,
  onSave,
  isSaving = false,
}: DiaryJournalEditorProps) {
  const t = useTranslations("diary");
  const tc = useTranslations("common");
  const [isEditing, setIsEditing] = useState(false);
  const [note, setNote] = useState(initialNote);
  const [tags, setTags] = useState<string[]>(initialTags);

  const handleSave = async () => {
    await onSave(note, tags);
    setIsEditing(false);
  };

  const handleCancel = () => {
    setNote(initialNote);
    setTags(initialTags);
    setIsEditing(false);
  };

  if (!isEditing) {
    return (
      <button
        type="button"
        onClick={() => setIsEditing(true)}
        className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        <Edit3 className="h-4 w-4" />
        {initialNote ? t("editNote") : t("addNote")}
      </button>
    );
  }

  return (
    <div className="space-y-3 rounded-lg border border-border bg-muted/30 p-4">
      <DiaryTagPicker selectedTags={tags} onChange={setTags} />

      <div>
        <label className="text-sm font-medium text-foreground">{t("journalNoteOptional")}</label>
        <textarea
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder={t("journalPlaceholder")}
          maxLength={2000}
          rows={4}
          className="mt-1 w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary resize-none"
        />
        <p className="mt-1 text-xs text-muted-foreground text-right">{note.length} / 2000</p>
      </div>

      <div className="flex gap-2">
        <button
          type="button"
          onClick={handleSave}
          disabled={isSaving}
          className={cn(
            "flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors",
            "bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          )}
        >
          <Save className="h-4 w-4" />
          {isSaving ? t("saving") : tc("save")}
        </button>
        <button
          type="button"
          onClick={handleCancel}
          disabled={isSaving}
          className="flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium bg-muted text-muted-foreground hover:bg-muted/80 transition-colors disabled:opacity-50"
        >
          <X className="h-4 w-4" />
          {tc("cancel")}
        </button>
      </div>
    </div>
  );
}
