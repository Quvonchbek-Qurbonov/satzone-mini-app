import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import Spinner from "@/components/ui/Spinner";
import ErrorBanner from "@/components/ui/ErrorBanner";
import { fetchMe, startAuth } from "@/api/auth";
import { ApiError } from "@/api/client";
import { useTelegram } from "@/hooks/useTelegram";
import { useAuthStore } from "@/store/authStore";

export default function Splash() {
  const navigate = useNavigate();
  const { tg } = useTelegram();
  const setTokens = useAuthStore((s) => s.setTokens);
  const setUser = useAuthStore((s) => s.setUser);
  const hydrate = useAuthStore((s) => s.hydrate);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function bootstrap() {
      try {
        await hydrate();
        if (!tg || !tg.initData) {
          setError("Open this app from the Telegram bot menu.");
          return;
        }
        const result = await startAuth(tg.initData);
        if (cancelled) return;
        if (result.status === "authenticated") {
          await setTokens(result.tokens.access_token, result.tokens.refresh_token);
          const me = await fetchMe();
          setUser(me);
          navigate(me.role === "admin" ? "/admin" : "/home", { replace: true });
        } else {
          navigate("/share-contact", { replace: true });
        }
      } catch (err) {
        const msg =
          err instanceof ApiError
            ? `${err.code}: ${err.message}`
            : err instanceof Error
              ? err.message
              : "Unknown error";
        setError(msg);
      }
    }
    bootstrap();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (error) {
    return (
      <div className="h-full flex flex-col">
        <ErrorBanner
          title="Cannot start"
          message={error}
          action={{ label: "Retry", onClick: () => window.location.reload() }}
        />
      </div>
    );
  }

  return (
    <div className="h-full flex items-center justify-center">
      <Spinner label="Signing you in…" />
    </div>
  );
}
