import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import * as authApi from "../api/auth";
import { getMe } from "../api/users";
import { ensureKeysExist } from "../crypto/setup";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isNewDevice, setIsNewDevice] = useState(false);

  const hydrate = useCallback(async () => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      setLoading(false);
      return;
    }
    try {
      const { data } = await getMe();
      setUser(data);
      // Ensure E2EE keys exist on this device
      const newKeys = await ensureKeysExist();
      if (newKeys) setIsNewDevice(true);
    } catch {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  const login = useCallback(async (username, password, totpCode) => {
    const { data } = await authApi.login(username, password, totpCode);
    localStorage.setItem("access_token", data.access_token);
    localStorage.setItem("refresh_token", data.refresh_token);
    const { data: profile } = await getMe();
    setUser(profile);
    // Ensure E2EE keys exist on this device
    const newKeys = await ensureKeysExist();
    if (newKeys) setIsNewDevice(true);
    return data;
  }, []);

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } catch {
      // fire-and-forget — clear local state regardless
    }
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    setUser(null);
  }, []);

  const updateUser = useCallback((fields) => {
    setUser((prev) => (prev ? { ...prev, ...fields } : prev));
  }, []);

  const dismissNewDevice = useCallback(() => setIsNewDevice(false), []);

  const value = useMemo(
    () => ({ user, loading, login, logout, updateUser, isNewDevice, dismissNewDevice }),
    [user, loading, login, logout, updateUser, isNewDevice, dismissNewDevice],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
