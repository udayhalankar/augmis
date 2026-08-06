import { NextRequest, NextResponse } from "next/server";

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (pathname === "/Infomentica" || pathname === "/Infomentica/") {
    const url = request.nextUrl.clone();
    url.pathname = "/infomentica";
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/Infomentica/:path*"],
};
