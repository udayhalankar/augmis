"use client";

import {
  createContext,
  useContext,
  useEffect,
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
  refreshLogin,
  registerWorkspace,
} from "@/services/authService";

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

export function AuthContextProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  function establishSession(nextToken: string, nextUser: AuthUser, refreshToken?: string | null) {
    localStorage.setItem("infomentica_token", nextToken);
    localStorage.setItem("infomentica_user", JSON.stringify(nextUser));
    if (refreshToken) {
      localStorage.setItem("infomentica_refresh_token", refreshToken);
    }
    setToken(nextToken);
    setUser(nextUser);
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
          const refreshResult = await refreshLogin(storedRefreshToken);
          establishSession(refreshResult.access_token, refreshResult.user, refreshResult.refresh_token);
          activeToken = refreshResult.access_token;
        }

        const me = await getMe(activeToken as string);

        if (me.success) {
          setUser(me.data);
          localStorage.setItem("infomentica_user", JSON.stringify(me.data));
        }
      } catch {
        localStorage.removeItem("infomentica_token");
        localStorage.removeItem("infomentica_refresh_token");
        localStorage.removeItem("infomentica_user");
        setUser(null);
        setToken(null);
      } finally {
        setLoading(false);
      }
    }

    bootstrapAuth();
  }, []);

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
    localStorage.removeItem("infomentica_token");
    localStorage.removeItem("infomentica_refresh_token");
    localStorage.removeItem("infomentica_user");

    setUser(null);
    setToken(null);

    router.push("/login");
  }

  async function logoutAllSessions() {
    await logoutAllSessionsRequest();
    localStorage.removeItem("infomentica_token");
    localStorage.removeItem("infomentica_refresh_token");
    localStorage.removeItem("infomentica_user");
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
