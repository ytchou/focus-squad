import { createClient } from "@/lib/supabase/client";

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
