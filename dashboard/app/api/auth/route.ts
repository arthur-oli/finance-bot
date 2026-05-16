import { NextRequest, NextResponse } from "next/server";
import { createSessionToken } from "@/lib/session";

// Best-effort in-memory rate limiter (5 failures / 5 min per IP).
// Sufficient for a personal project; not shared across serverless instances.
const _attempts = new Map<string, { count: number; resetAt: number }>();
const MAX_ATTEMPTS = 5;
const WINDOW_MS = 5 * 60 * 1000;

function getIp(req: NextRequest): string {
  return req.headers.get("x-forwarded-for")?.split(",")[0].trim() ?? "unknown";
}

function isRateLimited(ip: string): boolean {
  const now = Date.now();
  const entry = _attempts.get(ip);
  if (!entry || now > entry.resetAt) {
    _attempts.set(ip, { count: 1, resetAt: now + WINDOW_MS });
    return false;
  }
  if (entry.count >= MAX_ATTEMPTS) return true;
  entry.count++;
  return false;
}

function clearAttempts(ip: string) {
  _attempts.delete(ip);
}

export async function POST(request: NextRequest) {
  const ip = getIp(request);

  if (isRateLimited(ip)) {
    return NextResponse.json(
      { error: "Muitas tentativas. Aguarde 5 minutos." },
      { status: 429 }
    );
  }

  const { password } = await request.json();
  const secret = process.env.SESSION_SECRET;

  if (!secret) {
    return NextResponse.json({ error: "Configuração inválida" }, { status: 500 });
  }

  if (!process.env.DASHBOARD_PASSWORD || password !== process.env.DASHBOARD_PASSWORD) {
    return NextResponse.json({ error: "Senha incorreta" }, { status: 401 });
  }

  clearAttempts(ip);

  const token = await createSessionToken(secret);
  const res = NextResponse.json({ ok: true });
  res.cookies.set("session", token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    maxAge: 60 * 60 * 24 * 30,
    path: "/",
  });
  return res;
}

export async function DELETE() {
  const res = NextResponse.json({ ok: true });
  res.cookies.delete("session");
  return res;
}
