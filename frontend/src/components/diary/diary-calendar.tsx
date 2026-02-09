"use client";

import { useState } from "react";
import { DayPicker } from "react-day-picker";
import { DiaryEntryCard } from "./diary-entry-card";
import type { DiaryEntry } from "@/lib/api/client";

interface DiaryCalendarProps {
  entries: DiaryEntry[];
  onSaveNote: (sessionId: string, note: string, tags: string[]) => Promise<void>;
}

export function DiaryCalendar({ entries, onSaveNote }: DiaryCalendarProps) {
  const [selectedDate, setSelectedDate] = useState<Date | undefined>();

  // Build set of dates that have sessions
  const sessionDateStrings = new Set(
    entries.map((entry) => new Date(entry.session_date).toDateString())
  );

  const hasSession = (date: Date) => sessionDateStrings.has(date.toDateString());

  // Filter entries for selected date
  const selectedEntries = selectedDate
    ? entries.filter(
        (entry) => new Date(entry.session_date).toDateString() === selectedDate.toDateString()
      )
    : [];

  return (
    <div className="grid gap-6 lg:grid-cols-[400px_1fr]">
      {/* Calendar */}
      <div className="rounded-2xl border border-border bg-card p-6">
        <DayPicker
          mode="single"
          selected={selectedDate}
          onSelect={setSelectedDate}
          modifiers={{ hasSession }}
          modifiersClassNames={{
            hasSession: "diary-calendar-session-day",
          }}
          className="diary-calendar"
        />
        <div className="mt-4 text-sm text-muted-foreground">
          <p className="mb-1 font-medium text-foreground">Legend</p>
          <div className="flex items-center gap-2">
            <div className="h-3 w-3 rounded bg-primary/20" />
            <span>Session completed</span>
          </div>
        </div>
      </div>

      {/* Selected date entries */}
      <div>
        {!selectedDate && (
          <div className="rounded-2xl border border-border bg-card p-12 text-center">
            <p className="text-foreground">Select a date to view sessions</p>
          </div>
        )}

        {selectedDate && selectedEntries.length === 0 && (
          <div className="rounded-2xl border border-border bg-card p-12 text-center">
            <p className="mb-2 text-foreground">No sessions on this date</p>
            <p className="text-sm text-muted-foreground">
              {selectedDate.toLocaleDateString(undefined, {
                weekday: "long",
                month: "long",
                day: "numeric",
                year: "numeric",
              })}
            </p>
          </div>
        )}

        {selectedDate && selectedEntries.length > 0 && (
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-foreground">
              {selectedDate.toLocaleDateString(undefined, {
                weekday: "long",
                month: "long",
                day: "numeric",
                year: "numeric",
              })}
            </h2>
            {selectedEntries.map((entry) => (
              <DiaryEntryCard key={entry.session_id} entry={entry} onSaveNote={onSaveNote} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
