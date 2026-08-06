"use client";

import {
  createContext,
  type ReactNode,
  useContext,
  useEffect,
  useState,
} from "react";

import { useAuth } from "@/context/AuthContext";
import { getMySubscription } from "@/services/subscriptionService";

type SubscriptionContextType = {
  subscription: any | null;
  tenant: any | null;
  plan: any | null;
  usage: any | null;
  loading: boolean;
  refreshSubscription: () => Promise<void>;
  planHasModule: (moduleName: string) => boolean;
};

const SubscriptionContext = createContext<
  SubscriptionContextType | undefined
>(undefined);

export function SubscriptionContextProvider({
  children,
}: {
  children: ReactNode;
}) {
  const { user } = useAuth();

  const [subscription, setSubscription] = useState<any | null>(null);
  const [tenant, setTenant] = useState<any | null>(null);
  const [plan, setPlan] = useState<any | null>(null);
  const [usage, setUsage] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);

  async function refreshSubscription() {
    if (!user) {
      setSubscription(null);
      setTenant(null);
      setPlan(null);
      setUsage(null);
      return;
    }

    setLoading(true);

    try {
      const result = await getMySubscription();

      if (result.success) {
        setSubscription(result.data);
        setTenant(result.data.tenant);
        setPlan(result.data.plan);
        setUsage(result.data.usage);
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refreshSubscription();
  }, [user?.user_id]);

  function planHasModule(moduleName: string) {
    return Boolean(plan?.allowed_modules?.includes(moduleName));
  }

  return (
    <SubscriptionContext.Provider
      value={{
        subscription,
        tenant,
        plan,
        usage,
        loading,
        refreshSubscription,
        planHasModule,
      }}
    >
      {children}
    </SubscriptionContext.Provider>
  );
}

export function useSubscription() {
  const context = useContext(SubscriptionContext);

  if (!context) {
    throw new Error(
      "useSubscription must be used inside SubscriptionContextProvider"
    );
  }

  return context;
}
