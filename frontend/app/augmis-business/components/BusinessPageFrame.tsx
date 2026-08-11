"use client";

import { Box, Stack } from "@mui/material";

import { ADMIN_TOP_MENU_POST_MENU_CONTENT_SX } from "@/components/data-display/AdminTopMenu";
import { OutletPage } from "@/components/layout/OutletPage";
import AugmisBusinessTopMenu from "./AugmisBusinessTopMenu";
import type { BusinessMetricItem } from "./BusinessMetricCarousel";
import BusinessMetricCarousel from "./BusinessMetricCarousel";

export default function BusinessPageFrame({
  title,
  description,
  metrics,
  toolbar,
  actions,
  children,
}: {
  title: string;
  description: string;
  metrics?: BusinessMetricItem[];
  toolbar?: React.ReactNode;
  actions?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <OutletPage title={title} description={description}>
      <Stack spacing={0}>
        <AugmisBusinessTopMenu />
        <Stack spacing={1.6} sx={ADMIN_TOP_MENU_POST_MENU_CONTENT_SX}>
          {actions ? <Box>{actions}</Box> : null}
          {metrics && metrics.length ? <BusinessMetricCarousel items={metrics} /> : null}
          {toolbar}
          <Stack spacing={1.6}>{children}</Stack>
        </Stack>
      </Stack>
    </OutletPage>
  );
}
