// HMAC-SHA256 signed session tokens — works in both Edge and Node.js runtimes.
// Cookie stores a signed token, never the raw password.

function u8ToBase64url(u8: Uint8Array): string {
  let bin = "";
  for (let i = 0; i < u8.length; i++) bin += String.fromCharCode(u8[i]);
  return btoa(bin).replace(/\+/g, "-").replace(/\//g, "_").replace(/=/g, "");
}

function base64urlToU8(b64: string): Uint8Array {
  const b64std = b64.replace(/-/g, "+").replace(/_/g, "/");
  const bin = atob(b64std);
  const u8 = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
  return u8;
}

async function importKey(secret: string): Promise<CryptoKey> {
  return crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign", "verify"]
  );
}

const SESSION_TTL_MS = 30 * 24 * 60 * 60 * 1000;

export async function createSessionToken(secret: string): Promise<string> {
  const expiry = (Date.now() + SESSION_TTL_MS).toString();
  const key = await importKey(secret);
  const sig = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(expiry));
  return `${expiry}.${u8ToBase64url(new Uint8Array(sig))}`;
}

export async function verifySessionToken(token: string, secret: string): Promise<boolean> {
  try {
    const dot = token.lastIndexOf(".");
    if (dot === -1) return false;
    const expiry = token.slice(0, dot);
    const sig = token.slice(dot + 1);
    if (isNaN(Number(expiry)) || Date.now() > Number(expiry)) return false;
    const key = await importKey(secret);
    const sigBytes = base64urlToU8(sig);
    return crypto.subtle.verify(
      "HMAC",
      key,
      sigBytes.buffer as ArrayBuffer,
      new TextEncoder().encode(expiry)
    );
  } catch {
    return false;
  }
}
