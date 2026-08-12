"use client";

import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { useRouter } from "next/navigation";

import {
  changePassword as changePasswordRequest,
  getMe,
  loginUser,
  logoutAllSessions as logoutAllSessionsRequest,
  logoutSession,
  registerWorkspace,
} from "@/services/authService";
import {
  clearStoredSession,
  refreshSessionTokens,
  sessionRefreshEventName,
} from "@/services/sessionRefresh";

type AuthUser = {
  user_id: string;
  tenant_id: string;
  tenant_name: string;
  name: string;
  email: string;
  role: string;
  status: string;
  allowed_modules: string[];
  permissions: string[];
};

type AuthContextType = {
  user: AuthUser | null;
  token: string | null;
  loading: boolean;
  login: (
    email: string,
    password: string,
    rememberMe?: boolean,
    options?: {
      requiredRole?: string;
      redirectTo?: string;
    }
  ) => Promise<void>;
  register: (payload: {
    tenant_name: string;
    name: string;
    email: string;
    password: string;
    plan_id?: string;
  }) => Promise<void>;
  changePassword: (payload: {
    current_password: string;
    new_password: string;
    revoke_other_sessions: boolean;
  }) => Promise<void>;
  logout: () => void;
  logoutAllSessions: () => Promise<void>;
  hasModule: (moduleName: string) => boolean;
  hasPermission: (permission: string) => boolean;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);
const SESSION_KEEPALIVE_INTERVAL_MS = 60 * 1000;
const SESSION_REFRESH_MIN_INTERVAL_MS = 15 * 60 * 1000;
const SESSION_ACTIVITY_WINDOW_MS = 5 * 60 * 1000;

export function AuthContextProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const lastInteractionAtRef = useRef<number>(0);
  const lastRefreshAtRef = useRef<number>(0);

  function establishSession(nextToken: string, nextUser: AuthUser, refreshToken?: string | null) {
    localStorage.setItem("infomentica_token", nextToken);
    localStorage.setItem("infomentica_user", JSON.stringify(nextUser));
    if (refreshToken) {
      localStorage.setItem("infomentica_refresh_token", refreshToken);
    }
    setToken(nextToken);
    setUser(nextUser);
    lastRefreshAtRef.current = Date.now();
  }

  useEffect(() => {
    async function bootstrapAuth() {
      try {
        const storedToken = localStorage.getItem("infomentica_token");
        const storedRefreshToken = localStorage.getItem("infomentica_refresh_token");
        const storedUser = localStorage.getItem("infomentica_user");

        if (!storedToken && !storedRefreshToken) {
          setLoading(false);
          return;
        }

        if (storedToken) {
          setToken(storedToken);
        }

        if (storedUser) {
          setUser(JSON.parse(storedUser));
        }

        let activeToken = storedToken;
        if (!activeToken && storedRefreshToken) {
          const refreshResult = await refreshSessionTokens();
          establishSession(refreshResult.access_token, refreshResult.user as AuthUser, refreshResult.refresh_token);
          activeToken = refreshResult.access_token;
        }

        const me = await getMe(activeToken as string);

        if (me.success) {
          setUser(me.data);
          localStorage.setItem("infomentica_user", JSON.stringify(me.data));
        }
      } catch {
        clearStoredSession();
        setUser(null);
        setToken(null);
      } finally {
        setLoading(false);
      }
    }

    bootstrapAuth();
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    const recordActivity = () => {
      lastInteractionAtRef.current = Date.now();
    };

    const syncRefreshedSession = (event: Event) => {
      const detail = (event as CustomEvent).detail as
        | { access_token?: string; user?: AuthUser; refresh_token?: string }
        | undefined;
      if (!detail?.access_token || !detail.user) {
        return;
      }
      lastRefreshAtRef.current = Date.now();
      setToken(detail.access_token);
      setUser(detail.user);
    };

    const activityEvents: Array<keyof WindowEventMap> = ["pointerdown", "keydown", "mousemove", "scroll", "focus"];
    recordActivity();
    for (const eventName of activityEvents) {
      window.addEventListener(eventName, recordActivity, { passive: true });
    }
    window.addEventListener(sessionRefreshEventName(), syncRefreshedSession as EventListener);

    const interval = window.setInterval(async () => {
      if (!document.hasFocus() || document.visibilityState !== "visible") {
        return;
      }
      if (!localStorage.getItem("infomentica_token") || !localStorage.getItem("infomentica_refresh_token")) {
        return;
      }
      const now = Date.now();
      if (now - lastInteractionAtRef.current > SESSION_ACTIVITY_WINDOW_MS) {
        return;
      }
      if (now - lastRefreshAtRef.current < SESSION_REFRESH_MIN_INTERVAL_MS) {
        return;
      }
      try {
        await refreshSessionTokens();
      } catch {
        clearStoredSession();
        setUser(null);
        setToken(null);
        router.push("/login");
      }
    }, SESSION_KEEPALIVE_INTERVAL_MS);

    return () => {
      window.clearInterval(interval);
      for (const eventName of activityEvents) {
        window.removeEventListener(eventName, recordActivity);
      }
      window.removeEventListener(sessionRefreshEventName(), syncRefreshedSession as EventListener);
    };
  }, [router]);

  async function login(
    email: string,
    password: string,
    rememberMe = true,
    options?: {
      requiredRole?: string;
      redirectTo?: string;
    }
  ) {
    const result = await loginUser(email, password, rememberMe);

    if (!result.success) {
      throw new Error("Login failed");
    }

    if (options?.requiredRole && result.user?.role !== options.requiredRole) {
      const roleError = new Error(
        `This login page is only for ${options.requiredRole} users.`
      ) as Error & { response?: { data?: { detail?: string } } };
      roleError.response = {
        data: {
          detail:
            options.requiredRole === "SUPER_ADMIN"
              ? "Only AUGMIS Super Admin users can sign in from this page."
              : `Only ${options.requiredRole} users can sign in from this page.`,
        },
      };
      throw roleError;
    }

    establishSession(result.access_token, result.user, result.refresh_token);

    router.push(options?.redirectTo || "/home");
  }

  async function register(payload: {
    tenant_name: string;
    name: string;
    email: string;
    password: string;
    plan_id?: string;
  }) {
    const result = await registerWorkspace(payload);

    if (!result.success) {
      throw new Error("Registration failed");
    }

    establishSession(result.access_token, result.user, result.refresh_token);
    router.push("/home");
  }

  async function changePassword(payload: {
    current_password: string;
    new_password: string;
    revoke_other_sessions: boolean;
  }) {
    const result = await changePasswordRequest(payload);
    if (!result.success) {
      throw new Error("Password change failed");
    }
    establishSession(result.access_token, result.user, result.refresh_token);
  }

  function logout() {
    void logoutSession().catch(() => undefined);
    clearStoredSession();

    setUser(null);
    setToken(null);

    router.push("/login");
  }

  async function logoutAllSessions() {
    await logoutAllSessionsRequest();
    clearStoredSession();
    setUser(null);
    setToken(null);
    router.push("/login");
  }

  function hasModule(moduleName: string) {
    return Boolean(user?.allowed_modules?.includes(moduleName));
  }

  function hasPermission(permission: string) {
    return Boolean(user?.permissions?.includes(permission));
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        loading,
        login,
        register,
        changePassword,
        logout,
        logoutAllSessions,
        hasModule,
        hasPermission,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error("useAuth must be used inside AuthContextProvider");
  }

  return context;
}
