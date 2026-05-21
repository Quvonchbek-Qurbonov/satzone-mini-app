import { useEffect, useMemo, useState } from "react";

// Telegram WebApp shape — we type only what we use.
type ThemeParams = {
  bg_color?: string;
  text_color?: string;
  hint_color?: string;
  link_color?: string;
  button_color?: string;
  button_text_color?: string;
  secondary_bg_color?: string;
};

export type TelegramContact = {
  user_id: number;
  phone_number: string;
  first_name?: string;
  last_name?: string;
};

export type TelegramWebApp = {
  initData: string;
  initDataUnsafe: {
    user?: {
      id: number;
      first_name?: string;
      last_name?: string;
      username?: string;
    };
  };
  ready: () => void;
  expand: () => void;
  close: () => void;
  themeParams: ThemeParams;
  BackButton: {
    show: () => void;
    hide: () => void;
    onClick: (cb: () => void) => void;
    offClick: (cb: () => void) => void;
  };
  MainButton: {
    setText: (t: string) => void;
    show: () => void;
    hide: () => void;
    enable: () => void;
    disable: () => void;
    onClick: (cb: () => void) => void;
    offClick: (cb: () => void) => void;
  };
  HapticFeedback?: {
    impactOccurred: (style: "light" | "medium" | "heavy" | "rigid" | "soft") => void;
    notificationOccurred: (type: "error" | "success" | "warning") => void;
  };
  openLink: (url: string, options?: { try_instant_view?: boolean }) => void;
  openTelegramLink: (url: string) => void;
  requestContact?: (callback: (shared: boolean, response?: { responseUnsafe?: { contact?: TelegramContact } }) => void) => void;
  showPopup?: (
    params: { title?: string; message: string; buttons?: { id?: string; type?: "default" | "ok" | "close" | "cancel" | "destructive"; text?: string }[] },
    cb?: (id: string) => void,
  ) => void;
  CloudStorage?: {
    setItem: (key: string, value: string, cb?: (err: Error | null, ok: boolean) => void) => void;
    getItem: (key: string, cb: (err: Error | null, value: string | null) => void) => void;
    removeItem: (key: string, cb?: (err: Error | null, ok: boolean) => void) => void;
  };
  disableVerticalSwipes?: () => void;
  enableVerticalSwipes?: () => void;
};

declare global {
  interface Window {
    Telegram?: { WebApp?: TelegramWebApp };
  }
}

export function useTelegram(): { tg: TelegramWebApp | null; isInTelegram: boolean } {
  const tg = useMemo<TelegramWebApp | null>(() => {
    return typeof window !== "undefined" ? (window.Telegram?.WebApp ?? null) : null;
  }, []);
  const [isInTelegram, setIsInTelegram] = useState<boolean>(false);

  useEffect(() => {
    // A real Telegram client always populates initData; the dev-shim does not.
    setIsInTelegram(Boolean(tg && tg.initData && tg.initData.length > 0));
  }, [tg]);

  return { tg, isInTelegram };
}

export function cloudStorageGet(key: string): Promise<string | null> {
  return new Promise((resolve) => {
    const tg = window.Telegram?.WebApp;
    if (!tg?.CloudStorage) {
      resolve(localStorage.getItem(key));
      return;
    }
    tg.CloudStorage.getItem(key, (_err, value) => resolve(value ?? null));
  });
}

export function cloudStorageSet(key: string, value: string): Promise<void> {
  return new Promise((resolve) => {
    const tg = window.Telegram?.WebApp;
    if (!tg?.CloudStorage) {
      localStorage.setItem(key, value);
      resolve();
      return;
    }
    tg.CloudStorage.setItem(key, value, () => resolve());
  });
}

export function cloudStorageRemove(key: string): Promise<void> {
  return new Promise((resolve) => {
    const tg = window.Telegram?.WebApp;
    if (!tg?.CloudStorage) {
      localStorage.removeItem(key);
      resolve();
      return;
    }
    tg.CloudStorage.removeItem(key, () => resolve());
  });
}
