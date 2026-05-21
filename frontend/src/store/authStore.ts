import { create } from "zustand";

import { cloudStorageGet, cloudStorageRemove, cloudStorageSet } from "@/hooks/useTelegram";

export type AuthUser = {
  id: string;
  telegram_user_id: number;
  phone_number: string;
  full_name: string;
  username: string | null;
  role: "student" | "admin";
  satzone_user_id: string | null;
};

type State = {
  accessToken: string | null;
  refreshToken: string | null;
  user: AuthUser | null;
  setTokens: (access: string, refresh: string) => Promise<void>;
  setUser: (user: AuthUser | null) => void;
  hydrate: () => Promise<void>;
  clear: () => Promise<void>;
};

const REFRESH_KEY = "miniapp.refresh";

export const useAuthStore = create<State>((set, get) => ({
  accessToken: null,
  refreshToken: null,
  user: null,
  setTokens: async (access, refresh) => {
    set({ accessToken: access, refreshToken: refresh });
    await cloudStorageSet(REFRESH_KEY, refresh);
  },
  setUser: (user) => set({ user }),
  hydrate: async () => {
    if (get().refreshToken) return;
    const stored = await cloudStorageGet(REFRESH_KEY);
    if (stored) set({ refreshToken: stored });
  },
  clear: async () => {
    set({ accessToken: null, refreshToken: null, user: null });
    await cloudStorageRemove(REFRESH_KEY);
  },
}));
