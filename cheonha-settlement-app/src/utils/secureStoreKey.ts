export function normalizeSecureStoreKeyPart(value: string): string {
  const normalized = value.trim().toUpperCase().replace(/\s+/g, "_");
  if (!normalized) {
    return "EMPTY";
  }

  if (/^[A-Z0-9._-]+$/.test(normalized)) {
    return normalized;
  }

  return Array.from(normalized)
    .map((char) => char.codePointAt(0)?.toString(36) ?? "0")
    .join("_");
}
