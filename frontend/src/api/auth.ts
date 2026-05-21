import { api } from "@/api/client";
import type { AuthUser } from "@/store/authStore";

export type TokenResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
};

export type AuthStartResponse =
  | { status: "authenticated"; tokens: TokenResponse }
  | { status: "needs_contact"; telegram_user?: { id: number; first_name?: string } };

export function startAuth(initData: string) {
  return api<AuthStartResponse>("/auth/telegram", {
    method: "POST",
    body: { init_data: initData },
  });
}

export function linkContact(params: {
  initData: string;
  phoneNumber: string;
  contactUserId: number;
}) {
  return api<TokenResponse>("/auth/telegram/contact", {
    method: "POST",
    body: {
      init_data: params.initData,
      phone_number: params.phoneNumber,
      contact_user_id: params.contactUserId,
    },
  });
}

export function fetchMe() {
  return api<AuthUser>("/auth/me");
}

export function logout(refreshToken: string) {
  return api<{ message: string }>("/auth/logout", {
    method: "POST",
    body: { refresh_token: refreshToken },
  });
}
