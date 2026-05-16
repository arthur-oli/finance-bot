import { NextRequest, NextResponse } from "next/server";

const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8000";
const API_KEY = process.env.API_SECRET_KEY ?? "";

export async function GET(req: NextRequest) {
  return proxy(req, "GET");
}

export async function POST(req: NextRequest) {
  return proxy(req, "POST");
}

export async function PATCH(req: NextRequest) {
  return proxy(req, "PATCH");
}

export async function DELETE(req: NextRequest) {
  return proxy(req, "DELETE");
}

async function proxy(req: NextRequest, method: string) {
  const path = req.nextUrl.searchParams.get("path") ?? "";
  if (!path.startsWith("/api/")) {
    return NextResponse.json({ error: "Invalid path" }, { status: 400 });
  }
  const url = `${BACKEND}${path}`;

  const headers: Record<string, string> = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json",
  };

  let body: string | undefined;
  if (method !== "GET" && method !== "DELETE") {
    body = await req.text();
  }

  const res = await fetch(url, { method, headers, body });

  if (res.status === 204) {
    return new NextResponse(null, { status: 204 });
  }

  const text = await res.text();
  try {
    const data = JSON.parse(text);
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ error: text }, { status: res.status });
  }
}
