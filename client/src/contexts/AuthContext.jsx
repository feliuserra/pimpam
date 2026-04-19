import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import * as authApi from "../api/auth";
import { getMe } from "../api/users";
import { ensureKeysExist } from "../crypto/setup";
import { useIdleTimer } from "../hooks/useIdleTimer";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isNewDevice, setIsNewDevice] = useState(false);
  const [deviceId, setDeviceId] = useState(null);
  const [needsRecovery, setNeedsRecovery] = useState(false);
  const [recoveryBackupDeviceId, setRecoveryBackupDeviceId] = useState(null);
  const [extractablePrivateKey, setExtractablePrivateKey] = useState(null);
  const [e2eeError, setE2eeError] = useState(false);

  const handleKeySetup = useCallback((result) => {
    setE2eeError(false);
    if (result.needsRecovery) {
      setNeedsRecovery(true);
      setRecoveryBackupDeviceId(result.backupDeviceId);
    } else {
      setDeviceId(result.deviceId);
      if (result.isNewDevice) {
        setIsNewDevice(true);
        if (result.extractablePrivateKey) {
          setExtractablePrivateKey(result.extractablePrivateKey);
        }
      }
    }
  }, []);

  const hydrate = useCallback(async () => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      setLoading(false);
      return;
    }
    try {
      const { data } = await getMe();
      setUser(data);
      try {
        const result = await ensureKeysExist();
        handleKeySetup(result);
      } catch {
        setE2eeError(true);
      }
    } catch {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, [handleKeySetup]);

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  const login = useCallback(async (username, password, totpCode) => {
    const { data } = await authApi.login(username, password, totpCode);
    localStorage.setItem("access_token", data.access_token);
    localStorage.setItem("refresh_token", data.refresh_token);
    const { data: profile } = await getMe();
    setUser(profile);
    try {
      const result = await ensureKeysExist();
      handleKeySetup(result);
    } catch {
      setE2eeError(true);
    }
    return data;
  }, [handleKeySetup]);

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } catch {
      // fire-and-forget — clear local state regardless
    }
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    setUser(null);
    setDeviceId(null);
    setNeedsRecovery(false);
    setExtractablePrivateKey(null);
  }, []);

  const updateUser = useCallback((fields) => {
    setUser((prev) => (prev ? { ...prev, ...fields } : prev));
  }, []);

  const dismissNewDevice = useCallback(() => {
    setIsNewDevice(false);
    setExtractablePrivateKey(null);
  }, []);

  const dismissRecovery = useCallback(() => {
    setNeedsRecovery(false);
    setRecoveryBackupDeviceId(null);
  }, []);

  const retryE2eeSetup = useCallback(async () => {
    try {
      const result = await ensureKeysExist();
      handleKeySetup(result);
    } catch {
      setE2eeError(true);
    }
  }, [handleKeySetup]);

  // Auto-logout after 30 minutes of inactivity
  useIdleTimer({
    timeoutMs: 30 * 60 * 1000,
    onIdle: logout,
    enabled: !!user,
  });

  const value = useMemo(
    () => ({
      user, loading, login, logout, updateUser,
      isNewDevice, dismissNewDevice,
      deviceId, setDeviceId,
      needsRecovery, recoveryBackupDeviceId, dismissRecovery,
      extractablePrivateKey,
      e2eeError, retryE2eeSetup,
    }),
    [
      user, loading, login, logout, updateUser,
      isNewDevice, dismissNewDevice,
      deviceId,
      needsRecovery, recoveryBackupDeviceId, dismissRecovery,
      extractablePrivateKey,
      e2eeError, retryE2eeSetup,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
