import "@testing-library/jest-dom";
import { vi } from "vitest";
import messages from "../../messages/en.json";

// Global mock for next-intl so all components can call useTranslations
// without needing NextIntlClientProvider in tests
vi.mock("next-intl", () => {
  function getNestedValue(obj: Record<string, unknown>, path: string): unknown {
    return path.split(".").reduce<unknown>((acc, key) => {
      if (acc && typeof acc === "object" && key in (acc as Record<string, unknown>)) {
        return (acc as Record<string, unknown>)[key];
      }
      return undefined;
    }, obj);
  }

  return {
    useTranslations: (namespace: string) => {
      const ns = getNestedValue(messages, namespace) as Record<string, string> | undefined;
      return (key: string, params?: Record<string, string | number>) => {
        const template = ns?.[key] ?? `${namespace}.${key}`;
        if (!params) return template;
        return Object.entries(params).reduce<string>(
          (str, [k, v]) => str.replace(`{${k}}`, String(v)),
          template
        );
      };
    },
    useLocale: () => "en",
    NextIntlClientProvider: ({ children }: { children: React.ReactNode }) => children,
  };
});
