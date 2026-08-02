import { create } from "zustand";

import type { TokenUser } from "../types";

type AuthState = {
  user: TokenUser | null;
  setUser: (user: TokenUser | null) => void;
  hasPermission: (code: string) => boolean;
};

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  setUser: (user) => set({ user }),
  hasPermission: (code) => {
    const user = get().user;
    if (!user) return false;
    if (user.is_super_admin) return true;
    return user.permissions.includes(code);
  },
}));
