// Minimal jsdom stubs for Telegram WebApp APIs that tests touch.
(globalThis as unknown as { window?: Window }).window ??=
  {} as unknown as Window;
