"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { authApi, clearToken, getToken } from "@/services/api";
import type { CurrentUser } from "@/types/api";

export function useRequireAuth() {
  const router = useRouter();
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = getToken();
    if (!token) {
      router.replace("/login");
      return;
    }
    authApi
      .me()
      .then(setUser)
      .catch(() => {
        clearToken();
        router.replace("/login");
      })
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function logout() {
    clearToken();
    router.replace("/login");
  }

  return { user, loading, logout };
}
