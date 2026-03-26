import { createContext, useCallback, useContext, useEffect, useRef } from "react";
import { useAuth } from "./AuthContext";

const WSContext = createContext(null);

export function WSProvider({ children }) {
  const { user } = useAuth();
  const wsRef = useRef(null);
  const listenersRef = useRef(new Map());
  const attemptRef = useRef(0);
  const intentionalCloseRef = useRef(false);

  const dispatch = useCallback((type, data) => {
    const handlers = listenersRef.current.get(type);
    if (handlers) handlers.forEach((fn) => fn(data));
  }, []);

  const connect = useCallback(() => {
    const token = localStorage.getItem("access_token");
    if (!token) return;

    const isNative = window.Capacitor?.isNativePlatform?.();
    const wsUrl = isNative
      ? `ws://192.168.1.34:8000/ws?token=${token}`
      : `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}/ws?token=${token}`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      attemptRef.current = 0;
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        dispatch(msg.type, msg.data);
      } catch {
        // ignore malformed messages
      }
    };

    ws.onclose = () => {
      wsRef.current = null;
      if (!intentionalCloseRef.current) {
        const delay = Math.min(1000 * 2 ** attemptRef.current, 60000);
        const jitter = Math.random() * 1000;
        attemptRef.current += 1;
        setTimeout(connect, delay + jitter);
      }
    };

    ws.onerror = () => {
      ws.close();
    };

    wsRef.current = ws;
  }, [dispatch]);

  useEffect(() => {
    if (user) {
      intentionalCloseRef.current = false;
      connect();
    }
    return () => {
      intentionalCloseRef.current = true;
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [user, connect]);

  const subscribe = useCallback((eventType, handler) => {
    const map = listenersRef.current;
    if (!map.has(eventType)) map.set(eventType, new Set());
    map.get(eventType).add(handler);
    return () => {
      map.get(eventType)?.delete(handler);
    };
  }, []);

  const send = useCallback((message) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    }
  }, []);

  return (
    <WSContext.Provider value={{ subscribe, send }}>
      {children}
    </WSContext.Provider>
  );
}

export function useWS(eventType, handler) {
  const { subscribe } = useContext(WSContext) || {};
  useEffect(() => {
    if (!subscribe || !handler) return;
    return subscribe(eventType, handler);
  }, [subscribe, eventType, handler]);
}

export function useWSSend() {
  const ctx = useContext(WSContext);
  return ctx?.send;
}
