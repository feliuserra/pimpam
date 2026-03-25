import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { render, screen } from "@testing-library/react";
import { useCallback, useRef } from "react";

// Mock AuthContext
const mockUser = { id: 1, username: "testuser" };
vi.mock("./AuthContext", () => ({
  useAuth: vi.fn(() => ({ user: mockUser })),
}));

import { WSProvider, useWS, useWSSend } from "./WSContext";
import { useAuth } from "./AuthContext";

// Mock WebSocket
class MockWebSocket {
  static OPEN = 1;
  static CLOSED = 3;

  constructor(url) {
    this.url = url;
    this.readyState = MockWebSocket.OPEN;
    this.onopen = null;
    this.onmessage = null;
    this.onclose = null;
    this.onerror = null;
    MockWebSocket._instances.push(this);
    // Simulate connection open async
    setTimeout(() => {
      if (this.onopen) this.onopen();
    }, 0);
  }

  send = vi.fn();
  close = vi.fn(() => {
    this.readyState = MockWebSocket.CLOSED;
  });

  static _instances = [];
  static _reset() {
    MockWebSocket._instances = [];
  }
}

describe("WSContext", () => {
  let store;

  beforeEach(() => {
    vi.clearAllMocks();
    MockWebSocket._reset();

    store = { access_token: "test-token" };
    vi.stubGlobal("localStorage", {
      getItem: vi.fn((key) => store[key] ?? null),
      setItem: vi.fn(),
      removeItem: vi.fn(),
    });

    vi.stubGlobal("WebSocket", MockWebSocket);

    // Reset user mock to default
    useAuth.mockReturnValue({ user: mockUser });
  });

  const wrapper = ({ children }) => <WSProvider>{children}</WSProvider>;

  it("creates WebSocket connection when user is present", () => {
    const handler = vi.fn();
    renderHook(() => useWS("test", handler), { wrapper });

    expect(MockWebSocket._instances.length).toBe(1);
    expect(MockWebSocket._instances[0].url).toContain("token=test-token");
  });

  it("does not create WebSocket when no token exists", () => {
    store = {};
    const handler = vi.fn();
    renderHook(() => useWS("test", handler), { wrapper });

    expect(MockWebSocket._instances.length).toBe(0);
  });

  it("does not create WebSocket when user is null", () => {
    useAuth.mockReturnValue({ user: null });
    const handler = vi.fn();
    renderHook(() => useWS("test", handler), { wrapper });

    expect(MockWebSocket._instances.length).toBe(0);
  });

  it("dispatches message to subscribed handlers", () => {
    const handler = vi.fn();
    renderHook(() => useWS("new_post", handler), { wrapper });

    const ws = MockWebSocket._instances[0];

    act(() => {
      ws.onmessage({ data: JSON.stringify({ type: "new_post", data: { id: 1 } }) });
    });

    expect(handler).toHaveBeenCalledWith({ id: 1 });
  });

  it("does not dispatch to unsubscribed event types", () => {
    const handler = vi.fn();
    renderHook(() => useWS("new_post", handler), { wrapper });

    const ws = MockWebSocket._instances[0];

    act(() => {
      ws.onmessage({
        data: JSON.stringify({ type: "new_comment", data: { id: 2 } }),
      });
    });

    expect(handler).not.toHaveBeenCalled();
  });

  it("ignores malformed messages", () => {
    const handler = vi.fn();
    renderHook(() => useWS("test", handler), { wrapper });

    const ws = MockWebSocket._instances[0];

    // Should not throw
    act(() => {
      ws.onmessage({ data: "not valid json" });
    });

    expect(handler).not.toHaveBeenCalled();
  });

  it("closes WebSocket on unmount", () => {
    const handler = vi.fn();
    const { unmount } = renderHook(() => useWS("test", handler), { wrapper });

    const ws = MockWebSocket._instances[0];
    unmount();

    expect(ws.close).toHaveBeenCalled();
  });

  it("useWSSend returns send function", () => {
    const { result } = renderHook(() => useWSSend(), { wrapper });
    expect(typeof result.current).toBe("function");
  });

  it("send function sends JSON message when WS is open", () => {
    const { result } = renderHook(() => useWSSend(), { wrapper });

    const ws = MockWebSocket._instances[0];
    ws.readyState = WebSocket.OPEN;

    act(() => {
      result.current({ type: "typing", data: { to: "alice" } });
    });

    expect(ws.send).toHaveBeenCalledWith(
      JSON.stringify({ type: "typing", data: { to: "alice" } }),
    );
  });

  it("send does not send when WS is not open", () => {
    const { result } = renderHook(() => useWSSend(), { wrapper });

    const ws = MockWebSocket._instances[0];
    ws.readyState = MockWebSocket.CLOSED;

    act(() => {
      result.current({ type: "test" });
    });

    expect(ws.send).not.toHaveBeenCalled();
  });

  it("multiple handlers for same event type all receive messages", () => {
    // Use a single component that subscribes two handlers within the same provider
    const handler1 = vi.fn();
    const handler2 = vi.fn();

    function MultiSubscriber() {
      const h1 = useCallback(handler1, []);
      const h2 = useCallback(handler2, []);
      useWS("notification", h1);
      useWS("notification", h2);
      return <div data-testid="multi">subscribed</div>;
    }

    render(
      <WSProvider>
        <MultiSubscriber />
      </WSProvider>,
    );

    expect(screen.getByTestId("multi")).toBeInTheDocument();

    const ws = MockWebSocket._instances[0];

    act(() => {
      ws.onmessage({
        data: JSON.stringify({ type: "notification", data: { id: 5 } }),
      });
    });

    expect(handler1).toHaveBeenCalledWith({ id: 5 });
    expect(handler2).toHaveBeenCalledWith({ id: 5 });
  });

  it("useWS returns undefined outside provider", () => {
    // Should not throw — useWS gracefully handles missing context
    const handler = vi.fn();
    expect(() => {
      renderHook(() => useWS("test", handler));
    }).not.toThrow();
  });

  it("useWSSend returns undefined outside provider", () => {
    const { result } = renderHook(() => useWSSend());
    expect(result.current).toBeUndefined();
  });

  it("reconnects on close with exponential backoff", () => {
    vi.useFakeTimers();

    const handler = vi.fn();
    renderHook(() => useWS("test", handler), { wrapper });

    const ws = MockWebSocket._instances[0];

    // Simulate close (non-intentional)
    act(() => {
      ws.onclose();
    });

    // Should try to reconnect after delay (1000ms base + up to 1000ms jitter)
    act(() => {
      vi.advanceTimersByTime(2100);
    });

    // A new WebSocket should have been created
    expect(MockWebSocket._instances.length).toBeGreaterThan(1);

    vi.useRealTimers();
  });

  it("resets attempt counter on successful connection", () => {
    vi.useFakeTimers();

    const handler = vi.fn();
    renderHook(() => useWS("test", handler), { wrapper });

    const ws = MockWebSocket._instances[0];

    // Trigger onopen to reset attempt counter
    act(() => {
      ws.onopen();
    });

    // Simulate close
    act(() => {
      ws.onclose();
    });

    // First reconnect should use base delay (1000ms * 2^0 = 1000ms + jitter)
    act(() => {
      vi.advanceTimersByTime(2100);
    });

    expect(MockWebSocket._instances.length).toBe(2);

    vi.useRealTimers();
  });

  it("closes on error", () => {
    const handler = vi.fn();
    renderHook(() => useWS("test", handler), { wrapper });

    const ws = MockWebSocket._instances[0];

    act(() => {
      ws.onerror();
    });

    expect(ws.close).toHaveBeenCalled();
  });
});
