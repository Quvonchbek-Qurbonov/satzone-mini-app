import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { fetchMe, linkContact } from "@/api/auth";
import { ApiError } from "@/api/client";
import { useTelegram } from "@/hooks/useTelegram";
import { useAuthStore } from "@/store/authStore";

export default function ShareContact() {
  const navigate = useNavigate();
  const { tg } = useTelegram();
  const setTokens = useAuthStore((s) => s.setTokens);
  const setUser = useAuthStore((s) => s.setUser);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const websiteUrl = import.meta.env.VITE_WEBSITE_URL as string | undefined;

  const requestPhone = () => {
    if (!tg || !tg.initData) {
      setError("Not running inside Telegram.");
      return;
    }
    if (!tg.requestContact) {
      setError("Telegram client too old — please update Telegram.");
      return;
    }
    setPending(true);
    setError(null);
    tg.requestContact(async (shared, response) => {
      if (!shared) {
        setPending(false);
        setError("Phone share was cancelled.");
        return;
      }
      const contact = response?.responseUnsafe?.contact;
      if (!contact) {
        setPending(false);
        setError("Telegram did not return contact details.");
        return;
      }
      try {
        const tokens = await linkContact({
          initData: tg.initData,
          phoneNumber: contact.phone_number,
          contactUserId: contact.user_id,
        });
        await setTokens(tokens.access_token, tokens.refresh_token);
        const me = await fetchMe();
        setUser(me);
        tg.HapticFeedback?.notificationOccurred("success");
        navigate(me.role === "admin" ? "/admin" : "/home", { replace: true });
      } catch (err) {
        tg.HapticFeedback?.notificationOccurred("error");
        if (err instanceof ApiError && err.code === "not_registered") {
          setError(
            "We don't see your phone on the main website. Please register there first.",
          );
        } else if (err instanceof ApiError) {
          setError(`${err.code}: ${err.message}`);
        } else {
          setError("Could not link your contact. Try again.");
        }
      } finally {
        setPending(false);
      }
    });
  };

  return (
    <div className="h-full flex flex-col p-6">
      <div className="flex-1 flex flex-col items-center justify-center max-w-md mx-auto text-center">
        <h1 className="text-2xl font-bold mb-3">Welcome</h1>
        <p className="text-hint mb-6">
          To take SAT mock tests, share your phone number so we can confirm your
          account on the main website.
        </p>
        <button
          className="btn btn-primary w-full"
          onClick={requestPhone}
          disabled={pending}
        >
          {pending ? "Linking…" : "Share my phone"}
        </button>
        {error && (
          <div className="mt-4 w-full rounded-lg border border-danger/30 bg-danger/10 p-3 text-sm">
            {error}
            {websiteUrl && (
              <div className="mt-2">
                <button
                  className="btn btn-secondary w-full"
                  onClick={() => tg?.openLink(websiteUrl)}
                >
                  Open website to register
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
