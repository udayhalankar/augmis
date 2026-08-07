type ValidationDetailItem = {
  loc?: unknown;
  msg?: unknown;
  type?: unknown;
};

export type ParsedApiValidationError = {
  message: string;
  fieldErrors: Record<string, string>;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function sanitizeMessage(value: unknown): string | null {
  if (typeof value !== "string") {
    return null;
  }
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function mapFieldName(loc: unknown): string | null {
  if (!Array.isArray(loc) || loc.length === 0) {
    return null;
  }
  const last = loc[loc.length - 1];
  return typeof last === "string" ? last : null;
}

export function parseApiValidationError(
  error: unknown,
  fallback: string
): ParsedApiValidationError {
  const parsed: ParsedApiValidationError = {
    message: fallback,
    fieldErrors: {},
  };

  if (!isRecord(error)) {
    return parsed;
  }

  const response = isRecord(error.response) ? error.response : null;
  const data = response && isRecord(response.data) ? response.data : null;
  if (!data) {
    return parsed;
  }

  const detail = data.detail;
  if (typeof detail === "string") {
    parsed.message = sanitizeMessage(detail) || fallback;
    return parsed;
  }

  if (Array.isArray(detail)) {
    const fieldErrors: Record<string, string> = {};
    const nonFieldMessages: string[] = [];

    for (const item of detail as ValidationDetailItem[]) {
      const fieldName = mapFieldName(item.loc);
      const message = sanitizeMessage(item.msg);
      if (!message) {
        continue;
      }
      if (fieldName) {
        fieldErrors[fieldName] = fieldErrors[fieldName]
          ? `${fieldErrors[fieldName]} ${message}`
          : message;
      } else {
        nonFieldMessages.push(message);
      }
    }

    parsed.fieldErrors = fieldErrors;
    parsed.message =
      Object.keys(fieldErrors).length > 0
        ? "Please correct the highlighted fields."
        : nonFieldMessages[0] || fallback;
    return parsed;
  }

  const message = sanitizeMessage(data.message);
  if (message) {
    parsed.message = message;
  }

  return parsed;
}
