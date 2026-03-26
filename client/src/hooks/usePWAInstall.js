import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Captures the `beforeinstallprompt` event so the app can show
 * its own "Add to home screen" button.
 *
 * Returns { canInstall, promptInstall }.
 */
export function usePWAInstall() {
  const [canInstall, setCanInstall] = useState(false);
  const deferredPromptRef = useRef(null);

  useEffect(() => {
    const handler = (e) => {
      e.preventDefault();
      deferredPromptRef.current = e;
      setCanInstall(true);
    };

    window.addEventListener("beforeinstallprompt", handler);
    return () => window.removeEventListener("beforeinstallprompt", handler);
  }, []);

  const promptInstall = useCallback(async () => {
    const prompt = deferredPromptRef.current;
    if (!prompt) return false;

    prompt.prompt();
    const result = await prompt.userChoice;
    deferredPromptRef.current = null;
    setCanInstall(false);
    return result.outcome === "accepted";
  }, []);

  return { canInstall, promptInstall };
}
