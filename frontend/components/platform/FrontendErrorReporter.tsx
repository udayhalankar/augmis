"use client";

import { useEffect } from "react";

import { getCurrentBrowserRoute, reportFrontendLog } from "@/services/clientLogService";

function toText(value: unknown): string {
  if (typeof value === "string") {
    return value;
  }

  if (value instanceof Error) {
    return value.message || value.name || "Error";
  }

  if (typeof value === "object" && value !== null) {
    try {
      return JSON.stringify(value);
    } catch {
      return String(value);
    }
  }

  return String(value);
}

export default function FrontendErrorReporter() {
  useEffect(() => {
    let reporterActive = true;
    const originalConsoleError = console.error;

    const safeReport = async (payload: {
      message: string;
      category: string;
      stack?: string | null;
      component?: string;
      is_critical?: boolean;
    }) => {
      if (!reporterActive) {
        return;
      }

      await reportFrontendLog({
        message: payload.message,
        category: payload.category,
        level: "ERROR",
        route: getCurrentBrowserRoute(),
        stack: payload.stack || null,
        component: payload.component || "global_reporter",
        is_critical: payload.is_critical,
      });
    };

    const onWindowError = (event: ErrorEvent) => {
      void safeReport({
        message: event.message || "Unhandled browser error",
        category: "window_error",
        stack: event.error?.stack || null,
        component: "window",
        is_critical: true,
      });
    };

    const onUnhandledRejection = (event: PromiseRejectionEvent) => {
      const reason = event.reason;
      void safeReport({
        message: toText(reason) || "Unhandled promise rejection",
        category: "unhandled_rejection",
        stack: reason instanceof Error ? reason.stack || null : null,
        component: "promise",
        is_critical: true,
      });
    };

    console.error = (...args: unknown[]) => {
      originalConsoleError(...args);
      const maybeError = args.find((arg) => arg instanceof Error);
      void safeReport({
        message: args.map(toText).join(" | ").slice(0, 4000),
        category: "console_error",
        stack: maybeError instanceof Error ? maybeError.stack || null : null,
        component: "console",
      });
    };

    window.addEventListener("error", onWindowError);
    window.addEventListener("unhandledrejection", onUnhandledRejection);

    return () => {
      reporterActive = false;
      console.error = originalConsoleError;
      window.removeEventListener("error", onWindowError);
      window.removeEventListener("unhandledrejection", onUnhandledRejection);
    };
  }, []);

  return null;
}
