import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (pathname === "/login" || pathname.startsWith("/api/auth")) {
    return NextResponse.next();
  }

  const auth = request.cookies.get("auth")?.value;
  if (auth && auth === process.env.DASHBOARD_PASSWORD) {
    return withSecurityHeaders(NextResponse.next());
  }

  return NextResponse.redirect(new URL("/login", request.url));
}

function withSecurityHeaders(res: ReturnType<typeof NextResponse.next>) {
  res.headers.set("X-Frame-Options", "DENY");
  res.headers.set("X-Content-Type-Options", "nosniff");
  res.headers.set("Referrer-Policy", "strict-origin-when-cross-origin");
  res.headers.set("Permissions-Policy", "camera=(), microphone=(), geolocation=()");
  return res;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon\\.ico).*)"],
};
