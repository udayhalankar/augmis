export const AUTH_ROUTES = [
  "/login",
  "/super-admin/login",
  "/register",
  "/forgot-password",
  "/reset-password",
  "/accept-invite",
];

export const PUBLIC_ROUTE_PREFIXES = [
  "/landing-page",
];

export const PUBLIC_ROUTES = [
  "/",
];

export function isAuthRoute(pathname: string) {
  return AUTH_ROUTES.includes(pathname);
}

export function isPublicRoute(pathname: string) {
  if (isAuthRoute(pathname)) {
    return true;
  }

  if (PUBLIC_ROUTES.includes(pathname)) {
    return true;
  }

  return PUBLIC_ROUTE_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`)
  );
}
