import { describe, it, expect, vi, beforeEach } from "vitest";

let store;

beforeEach(() => {
  store = {};
  vi.stubGlobal("localStorage", {
    getItem: vi.fn((key) => store[key] ?? null),
    setItem: vi.fn((key, val) => {
      store[key] = val;
    }),
    removeItem: vi.fn((key) => {
      delete store[key];
    }),
  });
});

// vi.mock must come before import of module under test
import { getSeenStories, markStoriesSeen } from "./seenStories";

describe("seenStories", () => {
  describe("getSeenStories", () => {
    it("returns empty Set when nothing stored", () => {
      const result = getSeenStories();
      expect(result).toBeInstanceOf(Set);
      expect(result.size).toBe(0);
    });

    it("returns Set from stored JSON array", () => {
      store.pimpam_seen_stories = JSON.stringify([1, 2, 3]);
      const result = getSeenStories();
      expect(result.size).toBe(3);
      expect(result.has(1)).toBe(true);
      expect(result.has(2)).toBe(true);
      expect(result.has(3)).toBe(true);
    });

    it("returns empty Set on invalid JSON", () => {
      store.pimpam_seen_stories = "not-json{{{";
      const result = getSeenStories();
      expect(result).toBeInstanceOf(Set);
      expect(result.size).toBe(0);
    });
  });

  describe("markStoriesSeen", () => {
    it("stores new story IDs", () => {
      markStoriesSeen([10, 20]);
      const stored = JSON.parse(store.pimpam_seen_stories);
      expect(stored).toContain(10);
      expect(stored).toContain(20);
    });

    it("merges with existing seen stories", () => {
      store.pimpam_seen_stories = JSON.stringify([1, 2]);
      markStoriesSeen([3, 4]);
      const stored = JSON.parse(store.pimpam_seen_stories);
      expect(stored).toEqual(expect.arrayContaining([1, 2, 3, 4]));
      expect(stored.length).toBe(4);
    });

    it("deduplicates IDs", () => {
      store.pimpam_seen_stories = JSON.stringify([1, 2]);
      markStoriesSeen([2, 3]);
      const stored = JSON.parse(store.pimpam_seen_stories);
      expect(stored.filter((x) => x === 2).length).toBe(1);
    });

    it("caps at 500 entries keeping newest", () => {
      const existingIds = Array.from({ length: 499 }, (_, i) => i);
      store.pimpam_seen_stories = JSON.stringify(existingIds);
      markStoriesSeen([500, 501]);
      const stored = JSON.parse(store.pimpam_seen_stories);
      expect(stored.length).toBe(500);
      // Should contain the newest IDs
      expect(stored).toContain(501);
      expect(stored).toContain(500);
      // Oldest should be trimmed
      expect(stored).not.toContain(0);
    });

    it("silently handles localStorage.setItem failure", () => {
      localStorage.setItem.mockImplementation(() => {
        throw new Error("QuotaExceeded");
      });
      // Should not throw
      expect(() => markStoriesSeen([1, 2])).not.toThrow();
    });
  });
});
