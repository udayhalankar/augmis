"use client";

import { type ReactNode } from "react";
import { usePathname } from "next/navigation";

import { isPublicRoute } from "@/components/auth/authRouteConfig";
import EnterpriseShell from "./EnterpriseShell";

export default function AppFrame({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  if (isPublicRoute(pathname)) {
    return <>{children}</>;
  }

  return <EnterpriseShell>{children}</EnterpriseShell>;
}
