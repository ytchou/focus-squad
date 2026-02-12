import { createClient } from "@/lib/supabase/client";
import { getAuthToken } from "@/lib/auth-token";

const API_URL = process.env.NEXT_PUBLIC_API_URL;

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

class ApiClient {
  private async getAuthHeaders(): Promise<HeadersInit> {
    // First check cached token (set by AuthProvider when auth state changes)
    // This avoids race condition where getSession() returns null before
    // Supabase finishes recovering session from storage
    const cachedToken = getAuthToken();
    if (cachedToken) {
      return {
        "Content-Type": "application/json",
        Authorization: `Bearer ${cachedToken}`,
      };
    }

    // Fallback to getSession for calls made outside of auth flow
    const supabase = createClient();
    const {
      data: { session },
    } = await supabase.auth.getSession();

    if (!session?.access_token) {
      throw new ApiError(401, "Not authenticated");
    }

    return {
      "Content-Type": "application/json",
      Authorization: `Bearer ${session.access_token}`,
    };
  }

  async get<T>(endpoint: string): Promise<T> {
    const headers = await this.getAuthHeaders();
    const response = await fetch(`${API_URL}${endpoint}`, { headers });

    if (!response.ok) {
      const text = await response.text();
      throw new ApiError(response.status, text);
    }

    return response.json();
  }

  async patch<T>(endpoint: string, data: unknown): Promise<T> {
    const headers = await this.getAuthHeaders();
    const response = await fetch(`${API_URL}${endpoint}`, {
      method: "PATCH",
      headers,
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const text = await response.text();
      throw new ApiError(response.status, text);
    }

    return response.json();
  }

  async post<T>(endpoint: string, data?: unknown): Promise<T> {
    const headers = await this.getAuthHeaders();
    const response = await fetch(`${API_URL}${endpoint}`, {
      method: "POST",
      headers,
      body: data ? JSON.stringify(data) : undefined,
    });

    if (!response.ok) {
      const text = await response.text();
      throw new ApiError(response.status, text);
    }

    return response.json();
  }

  async put<T>(endpoint: string, data?: unknown): Promise<T> {
    const headers = await this.getAuthHeaders();
    const response = await fetch(`${API_URL}${endpoint}`, {
      method: "PUT",
      headers,
      body: data ? JSON.stringify(data) : undefined,
    });

    if (!response.ok) {
      const text = await response.text();
      throw new ApiError(response.status, text);
    }

    return response.json();
  }

  async delete<T>(endpoint: string): Promise<T> {
    const headers = await this.getAuthHeaders();
    const response = await fetch(`${API_URL}${endpoint}`, {
      method: "DELETE",
      headers,
    });

    if (!response.ok) {
      const text = await response.text();
      throw new ApiError(response.status, text);
    }

    return response.json();
  }
}

export const api = new ApiClient();

// =============================================================================
// Diary Types
// =============================================================================

export interface DiaryReflection {
  phase: "setup" | "break" | "social";
  content: string;
  created_at: string;
}

export interface DiaryEntry {
  session_id: string;
  session_date: string;
  session_topic: string | null;
  focus_minutes: number;
  reflections: DiaryReflection[];
  note: string | null;
  tags: string[];
}

export interface DiaryResponse {
  items: DiaryEntry[];
  total: number;
  page: number;
  per_page: number;
}

export interface DiaryStats {
  current_streak: number;
  weekly_focus_minutes: number;
  total_sessions: number;
}

export interface SaveDiaryNoteRequest {
  note?: string;
  tags: string[];
}

export interface DiaryNoteCompanionReaction {
  companion_type: string;
  animation: string;
  tag: string;
}

export interface DiaryNoteMood {
  mood: "positive" | "neutral" | "tired";
  score: number;
  positive_count: number;
  negative_count: number;
  total_count: number;
}

export interface DiaryNoteWithReactionResponse {
  session_id: string;
  note: string;
  tags: string[];
  created_at: string;
  updated_at: string;
  companion_reaction: DiaryNoteCompanionReaction | null;
  mood: DiaryNoteMood | null;
}
