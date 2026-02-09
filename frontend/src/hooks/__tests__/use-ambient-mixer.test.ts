import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { AMBIENT_STORAGE_KEY } from "@/config/ambient-tracks";

// ---------------------------------------------------------------------------
// WebAudio API mocks
// ---------------------------------------------------------------------------

function createMockGainNode() {
  return {
    gain: {
      value: 1,
      setValueAtTime: vi.fn(),
      linearRampToValueAtTime: vi.fn(),
    },
    connect: vi.fn(),
    disconnect: vi.fn(),
  };
}

function createMockSourceNode() {
  return {
    buffer: null as AudioBuffer | null,
    loop: false,
    connect: vi.fn(),
    disconnect: vi.fn(),
    start: vi.fn(),
    stop: vi.fn(),
  };
}

function createMockAudioContext() {
  return {
    state: "running" as AudioContextState,
    currentTime: 0,
    destination: {} as AudioDestinationNode,
    resume: vi.fn().mockResolvedValue(undefined),
    close: vi.fn().mockResolvedValue(undefined),
    createBufferSource: vi.fn(() => createMockSourceNode()),
    createGain: vi.fn(() => createMockGainNode()),
    decodeAudioData: vi.fn().mockResolvedValue({
      duration: 60,
      length: 2646000,
      numberOfChannels: 2,
      sampleRate: 44100,
      getChannelData: vi.fn(),
    } as unknown as AudioBuffer),
  };
}

let mockAudioContext: ReturnType<typeof createMockAudioContext>;

// ---------------------------------------------------------------------------
// Setup / Teardown
// ---------------------------------------------------------------------------

beforeEach(() => {
  localStorage.clear();

  mockAudioContext = createMockAudioContext();

  // Use a regular function (not arrow) so it can be called with `new`
  const MockAudioContext = vi.fn(function (this: unknown) {
    Object.assign(this as object, mockAudioContext);
    return this;
  });
  vi.stubGlobal("AudioContext", MockAudioContext);

  // Mock fetch to return a minimal ArrayBuffer for audio loading
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      arrayBuffer: vi.fn().mockResolvedValue(new ArrayBuffer(8)),
    })
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  localStorage.clear();
});

// ---------------------------------------------------------------------------
// Helper to dynamically import the hook (avoids module-level side effects)
// ---------------------------------------------------------------------------

async function importHook() {
  vi.resetModules();
  const mod = await import("../use-ambient-mixer");
  return mod.useAmbientMixer;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("useAmbientMixer", () => {
  // -----------------------------------------------------------------------
  // 1. Default initialization (no localStorage)
  // -----------------------------------------------------------------------
  describe("default initialization", () => {
    it("initializes all tracks as disabled with default volumes", async () => {
      const useAmbientMixer = await importHook();
      const { result } = renderHook(() => useAmbientMixer());

      expect(result.current.tracks).toEqual({
        lofi: { enabled: false, volume: 0.5 },
        coffee: { enabled: false, volume: 0.3 },
        rain: { enabled: false, volume: 0.4 },
      });
    });

    it("starts with isReady = false", async () => {
      const useAmbientMixer = await importHook();
      const { result } = renderHook(() => useAmbientMixer());

      expect(result.current.isReady).toBe(false);
    });
  });

  // -----------------------------------------------------------------------
  // 2. Toggle on/off persists to localStorage
  // -----------------------------------------------------------------------
  describe("toggleTrack", () => {
    it("toggles a track on and persists to localStorage", async () => {
      const useAmbientMixer = await importHook();
      const { result } = renderHook(() => useAmbientMixer());

      expect(result.current.tracks.lofi.enabled).toBe(false);

      act(() => {
        result.current.toggleTrack("lofi");
      });

      expect(result.current.tracks.lofi.enabled).toBe(true);

      const persisted = JSON.parse(localStorage.getItem(AMBIENT_STORAGE_KEY) ?? "{}");
      expect(persisted.lofi.enabled).toBe(true);
    });

    it("toggles a track off and persists to localStorage", async () => {
      const useAmbientMixer = await importHook();
      const { result } = renderHook(() => useAmbientMixer());

      // Toggle on first
      act(() => {
        result.current.toggleTrack("rain");
      });
      expect(result.current.tracks.rain.enabled).toBe(true);

      // Toggle off
      act(() => {
        result.current.toggleTrack("rain");
      });
      expect(result.current.tracks.rain.enabled).toBe(false);

      const persisted = JSON.parse(localStorage.getItem(AMBIENT_STORAGE_KEY) ?? "{}");
      expect(persisted.rain.enabled).toBe(false);
    });

    it("does nothing for an unknown track id", async () => {
      const useAmbientMixer = await importHook();
      const { result } = renderHook(() => useAmbientMixer());

      const tracksBefore = { ...result.current.tracks };

      act(() => {
        result.current.toggleTrack("nonexistent");
      });

      expect(result.current.tracks).toEqual(tracksBefore);
    });
  });

  // -----------------------------------------------------------------------
  // 3. Volume changes update track state
  // -----------------------------------------------------------------------
  describe("setVolume", () => {
    it("updates volume and persists to localStorage", async () => {
      const useAmbientMixer = await importHook();
      const { result } = renderHook(() => useAmbientMixer());

      act(() => {
        result.current.setVolume("lofi", 0.8);
      });

      expect(result.current.tracks.lofi.volume).toBe(0.8);

      const persisted = JSON.parse(localStorage.getItem(AMBIENT_STORAGE_KEY) ?? "{}");
      expect(persisted.lofi.volume).toBe(0.8);
    });

    it("clamps volume to [0, 1] range - above 1", async () => {
      const useAmbientMixer = await importHook();
      const { result } = renderHook(() => useAmbientMixer());

      act(() => {
        result.current.setVolume("coffee", 1.5);
      });

      expect(result.current.tracks.coffee.volume).toBe(1);
    });

    it("clamps volume to [0, 1] range - below 0", async () => {
      const useAmbientMixer = await importHook();
      const { result } = renderHook(() => useAmbientMixer());

      act(() => {
        result.current.setVolume("coffee", -0.3);
      });

      expect(result.current.tracks.coffee.volume).toBe(0);
    });

    it("applies linearRampToValueAtTime on active track gain node", async () => {
      const useAmbientMixer = await importHook();
      const { result } = renderHook(() => useAmbientMixer());

      // Enable a track so it has active audio nodes
      await act(async () => {
        result.current.toggleTrack("lofi");
        await vi.waitFor(() => {
          expect(mockAudioContext.createBufferSource).toHaveBeenCalled();
        });
      });

      const gainNode = mockAudioContext.createGain.mock.results[0]?.value;

      act(() => {
        result.current.setVolume("lofi", 0.7);
      });

      expect(gainNode.gain.linearRampToValueAtTime).toHaveBeenCalledWith(0.7, expect.any(Number));
    });

    it("does nothing for an unknown track id", async () => {
      const useAmbientMixer = await importHook();
      const { result } = renderHook(() => useAmbientMixer());

      const tracksBefore = { ...result.current.tracks };

      act(() => {
        result.current.setVolume("nonexistent", 0.5);
      });

      expect(result.current.tracks).toEqual(tracksBefore);
    });
  });

  // -----------------------------------------------------------------------
  // 4. Multiple tracks can be enabled simultaneously
  // -----------------------------------------------------------------------
  describe("multiple tracks", () => {
    it("enables multiple tracks simultaneously", async () => {
      const useAmbientMixer = await importHook();
      const { result } = renderHook(() => useAmbientMixer());

      act(() => {
        result.current.toggleTrack("lofi");
      });
      act(() => {
        result.current.toggleTrack("rain");
      });

      expect(result.current.tracks.lofi.enabled).toBe(true);
      expect(result.current.tracks.rain.enabled).toBe(true);
      expect(result.current.tracks.coffee.enabled).toBe(false);
    });

    it("allows independent volume control per track", async () => {
      const useAmbientMixer = await importHook();
      const { result } = renderHook(() => useAmbientMixer());

      act(() => {
        result.current.setVolume("lofi", 0.9);
      });
      act(() => {
        result.current.setVolume("rain", 0.2);
      });

      expect(result.current.tracks.lofi.volume).toBe(0.9);
      expect(result.current.tracks.rain.volume).toBe(0.2);
      // coffee unchanged
      expect(result.current.tracks.coffee.volume).toBe(0.3);
    });
  });

  // -----------------------------------------------------------------------
  // 5. State initializes from localStorage
  // -----------------------------------------------------------------------
  describe("localStorage initialization", () => {
    it("restores enabled/volume state from localStorage", async () => {
      const persisted = {
        lofi: { enabled: true, volume: 0.7 },
        coffee: { enabled: false, volume: 0.1 },
        rain: { enabled: true, volume: 0.9 },
      };
      localStorage.setItem(AMBIENT_STORAGE_KEY, JSON.stringify(persisted));

      const useAmbientMixer = await importHook();
      const { result } = renderHook(() => useAmbientMixer());

      expect(result.current.tracks.lofi).toEqual({
        enabled: true,
        volume: 0.7,
      });
      expect(result.current.tracks.coffee).toEqual({
        enabled: false,
        volume: 0.1,
      });
      expect(result.current.tracks.rain).toEqual({
        enabled: true,
        volume: 0.9,
      });
    });

    it("clamps persisted volume to [0, 1]", async () => {
      const persisted = {
        lofi: { enabled: false, volume: 2.5 },
        rain: { enabled: false, volume: -1 },
      };
      localStorage.setItem(AMBIENT_STORAGE_KEY, JSON.stringify(persisted));

      const useAmbientMixer = await importHook();
      const { result } = renderHook(() => useAmbientMixer());

      expect(result.current.tracks.lofi.volume).toBe(1);
      expect(result.current.tracks.rain.volume).toBe(0);
    });

    it("falls back to defaults when localStorage contains invalid JSON", async () => {
      localStorage.setItem(AMBIENT_STORAGE_KEY, "not-valid-json");

      const useAmbientMixer = await importHook();
      const { result } = renderHook(() => useAmbientMixer());

      expect(result.current.tracks).toEqual({
        lofi: { enabled: false, volume: 0.5 },
        coffee: { enabled: false, volume: 0.3 },
        rain: { enabled: false, volume: 0.4 },
      });
    });

    it("fills in missing tracks with defaults when localStorage is partial", async () => {
      const persisted = {
        lofi: { enabled: true, volume: 0.6 },
      };
      localStorage.setItem(AMBIENT_STORAGE_KEY, JSON.stringify(persisted));

      const useAmbientMixer = await importHook();
      const { result } = renderHook(() => useAmbientMixer());

      expect(result.current.tracks.lofi).toEqual({
        enabled: true,
        volume: 0.6,
      });
      expect(result.current.tracks.coffee).toEqual({
        enabled: false,
        volume: 0.3,
      });
      expect(result.current.tracks.rain).toEqual({
        enabled: false,
        volume: 0.4,
      });
    });
  });

  // -----------------------------------------------------------------------
  // 6. AudioContext and WebAudio interactions
  // -----------------------------------------------------------------------
  describe("AudioContext integration", () => {
    it("creates AudioContext lazily on first toggleTrack", async () => {
      const useAmbientMixer = await importHook();
      const { result } = renderHook(() => useAmbientMixer());

      expect(AudioContext).not.toHaveBeenCalled();

      act(() => {
        result.current.toggleTrack("lofi");
      });

      expect(AudioContext).toHaveBeenCalledTimes(1);
    });

    it("sets isReady to true after AudioContext is created", async () => {
      const useAmbientMixer = await importHook();
      const { result } = renderHook(() => useAmbientMixer());

      expect(result.current.isReady).toBe(false);

      // toggleTrack triggers async startPlayback -> ensureAudioContext -> setIsReady(true)
      // We need to let the full async chain settle
      await act(async () => {
        result.current.toggleTrack("lofi");
      });

      // Wait for the async audio loading promise chain to resolve
      await act(async () => {
        await vi.waitFor(() => {
          expect(mockAudioContext.createBufferSource).toHaveBeenCalled();
        });
      });

      expect(result.current.isReady).toBe(true);
    });

    it("resumes suspended AudioContext", async () => {
      mockAudioContext.state = "suspended";
      const useAmbientMixer = await importHook();
      const { result } = renderHook(() => useAmbientMixer());

      await act(async () => {
        result.current.toggleTrack("lofi");
        await vi.waitFor(() => {
          expect(mockAudioContext.resume).toHaveBeenCalled();
        });
      });
    });

    it("fetches audio file and decodes it on track enable", async () => {
      const useAmbientMixer = await importHook();
      const { result } = renderHook(() => useAmbientMixer());

      await act(async () => {
        result.current.toggleTrack("lofi");
        await vi.waitFor(() => {
          expect(fetch).toHaveBeenCalledWith("/assets/audio/lofi-beats.mp3");
        });
      });

      expect(mockAudioContext.decodeAudioData).toHaveBeenCalled();
    });

    it("creates source and gain nodes, connects and starts playback", async () => {
      const useAmbientMixer = await importHook();
      const { result } = renderHook(() => useAmbientMixer());

      await act(async () => {
        result.current.toggleTrack("coffee");
        await vi.waitFor(() => {
          expect(mockAudioContext.createBufferSource).toHaveBeenCalled();
        });
      });

      const sourceNode = mockAudioContext.createBufferSource.mock.results[0]?.value;
      const gainNode = mockAudioContext.createGain.mock.results[0]?.value;

      expect(sourceNode.loop).toBe(true);
      expect(sourceNode.connect).toHaveBeenCalledWith(gainNode);
      expect(gainNode.connect).toHaveBeenCalledWith(mockAudioContext.destination);
      expect(gainNode.gain.setValueAtTime).toHaveBeenCalledWith(0.3, 0);
      expect(sourceNode.start).toHaveBeenCalled();
    });

    it("stops and disconnects source on track disable", async () => {
      const useAmbientMixer = await importHook();
      const { result } = renderHook(() => useAmbientMixer());

      // Enable track
      await act(async () => {
        result.current.toggleTrack("lofi");
        await vi.waitFor(() => {
          expect(mockAudioContext.createBufferSource).toHaveBeenCalled();
        });
      });

      const sourceNode = mockAudioContext.createBufferSource.mock.results[0]?.value;
      const gainNode = mockAudioContext.createGain.mock.results[0]?.value;

      // Disable track
      act(() => {
        result.current.toggleTrack("lofi");
      });

      expect(sourceNode.stop).toHaveBeenCalled();
      expect(sourceNode.disconnect).toHaveBeenCalled();
      expect(gainNode.disconnect).toHaveBeenCalled();
    });

    it("caches decoded audio buffer for subsequent enables", async () => {
      const useAmbientMixer = await importHook();
      const { result } = renderHook(() => useAmbientMixer());

      // Enable -> fetches and decodes
      await act(async () => {
        result.current.toggleTrack("rain");
      });
      await act(async () => {
        await vi.waitFor(() => {
          expect(mockAudioContext.decodeAudioData).toHaveBeenCalledTimes(1);
        });
      });

      // Disable
      act(() => {
        result.current.toggleTrack("rain");
      });

      // Enable again -> should reuse cached buffer
      await act(async () => {
        result.current.toggleTrack("rain");
      });
      await act(async () => {
        await vi.waitFor(() => {
          expect(mockAudioContext.createBufferSource).toHaveBeenCalledTimes(2);
        });
      });

      // decodeAudioData should still only have been called once (cached)
      expect(mockAudioContext.decodeAudioData).toHaveBeenCalledTimes(1);
      expect(fetch).toHaveBeenCalledTimes(1);
    });

    it("cleans up all audio nodes on unmount", async () => {
      const useAmbientMixer = await importHook();
      const { result, unmount } = renderHook(() => useAmbientMixer());

      // Enable a track so nodes exist
      await act(async () => {
        result.current.toggleTrack("lofi");
        await vi.waitFor(() => {
          expect(mockAudioContext.createBufferSource).toHaveBeenCalled();
        });
      });

      const sourceNode = mockAudioContext.createBufferSource.mock.results[0]?.value;

      unmount();

      expect(sourceNode.stop).toHaveBeenCalled();
      expect(sourceNode.disconnect).toHaveBeenCalled();
      expect(mockAudioContext.close).toHaveBeenCalled();
    });
  });
});
