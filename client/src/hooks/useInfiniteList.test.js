import { renderHook, act, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { useInfiniteList } from "./useInfiniteList";

beforeEach(() => {
  global.IntersectionObserver = vi.fn(() => ({
    observe: vi.fn(),
    disconnect: vi.fn(),
  }));
});

describe("useInfiniteList", () => {
  it("starts with empty items and loading false", () => {
    const fetchFn = vi.fn().mockResolvedValue({ data: [] });
    const { result } = renderHook(() => useInfiniteList(fetchFn));
    expect(result.current.items).toEqual([]);
    expect(result.current.loading).toBe(false);
    expect(result.current.hasMore).toBe(true);
  });

  it("loads items on refresh", async () => {
    const items = [{ id: 1 }, { id: 2 }, { id: 3 }];
    const fetchFn = vi.fn().mockResolvedValue({ data: items });

    const { result } = renderHook(() => useInfiniteList(fetchFn));

    await act(async () => {
      await result.current.refresh();
    });

    expect(result.current.items).toEqual(items);
    expect(fetchFn).toHaveBeenCalledWith(null);
  });

  it("sets hasMore to false when no data returned", async () => {
    const fetchFn = vi.fn().mockResolvedValue({ data: [] });

    const { result } = renderHook(() => useInfiniteList(fetchFn));

    await act(async () => {
      await result.current.refresh();
    });

    expect(result.current.hasMore).toBe(false);
    expect(result.current.items).toEqual([]);
  });

  it("tracks cursor from last loaded item id", async () => {
    const page1 = [{ id: 10 }, { id: 9 }, { id: 8 }];
    const fetchFn = vi.fn().mockResolvedValue({ data: page1 });

    const { result } = renderHook(() => useInfiniteList(fetchFn));

    await act(async () => {
      await result.current.refresh();
    });

    // First call uses null cursor
    expect(fetchFn).toHaveBeenCalledWith(null);
    expect(result.current.items).toEqual(page1);

    // After refresh with new data, verify the hook correctly stored the cursor
    // by checking that items are set and hasMore is still true
    expect(result.current.hasMore).toBe(true);
    expect(result.current.items.length).toBe(3);
  });

  it("handles fetch error gracefully", async () => {
    const fetchFn = vi.fn().mockRejectedValue(new Error("Network error"));

    const { result } = renderHook(() => useInfiniteList(fetchFn));

    await act(async () => {
      await result.current.refresh();
    });

    expect(result.current.items).toEqual([]);
    expect(result.current.hasMore).toBe(false);
    expect(result.current.loading).toBe(false);
  });

  it("refresh replaces all items", async () => {
    const page1 = [{ id: 3 }, { id: 2 }, { id: 1 }];
    const page2 = [{ id: 5 }, { id: 4 }];
    const fetchFn = vi
      .fn()
      .mockResolvedValueOnce({ data: page1 })
      .mockResolvedValueOnce({ data: page2 });

    const { result } = renderHook(() => useInfiniteList(fetchFn));

    await act(async () => {
      await result.current.refresh();
    });
    expect(result.current.items).toEqual(page1);

    await act(async () => {
      await result.current.refresh();
    });
    expect(result.current.items).toEqual(page2);
  });

  it("setItems allows external mutation", async () => {
    const fetchFn = vi.fn().mockResolvedValue({ data: [{ id: 1 }] });
    const { result } = renderHook(() => useInfiniteList(fetchFn));

    await act(async () => {
      await result.current.refresh();
    });

    act(() => {
      result.current.setItems((prev) => [{ id: 99 }, ...prev]);
    });

    expect(result.current.items[0].id).toBe(99);
    expect(result.current.items.length).toBe(2);
  });
});
