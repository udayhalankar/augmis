"use client";

import { useState, type MouseEvent, type ReactNode } from "react";

import MoreVertRoundedIcon from "@mui/icons-material/MoreVertRounded";
import VisibilityOutlinedIcon from "@mui/icons-material/VisibilityOutlined";
import { IconButton, Menu, MenuItem, Stack, Tooltip } from "@mui/material";

export type BusinessRowActionMenuItem = {
  key: string;
  label: ReactNode;
  icon?: ReactNode;
  onClick: () => void;
  disabled?: boolean;
};

export default function BusinessRowActionMenu({
  primaryAction,
  onView,
  viewLabel = "View",
  menuItems,
}: {
  primaryAction?: ReactNode;
  onView?: () => void;
  viewLabel?: string;
  menuItems: BusinessRowActionMenuItem[];
}) {
  const [anchorEl, setAnchorEl] = useState<HTMLElement | null>(null);

  return (
    <>
      <Stack direction="row" spacing={0.5} sx={{ justifyContent: "flex-end", alignItems: "center" }}>
        {primaryAction}
        {onView ? (
          <Tooltip title={viewLabel}>
            <span>
              <IconButton
                size="small"
                onClick={onView}
                sx={{
                  borderRadius: "8px",
                  border: "1px solid #DBEAFE",
                  bgcolor: "#F8FBFF",
                }}
              >
                <VisibilityOutlinedIcon fontSize="small" sx={{ color: "#2563EB" }} />
              </IconButton>
            </span>
          </Tooltip>
        ) : null}
        <Tooltip title="More actions">
          <span>
            <IconButton
              size="small"
              onClick={(event: MouseEvent<HTMLElement>) => setAnchorEl(event.currentTarget)}
              sx={{
                borderRadius: "8px",
                border: "1px solid #E2E8F0",
                bgcolor: "#FFFFFF",
              }}
            >
              <MoreVertRoundedIcon fontSize="small" sx={{ color: "#475569" }} />
            </IconButton>
          </span>
        </Tooltip>
      </Stack>
      <Menu anchorEl={anchorEl} open={Boolean(anchorEl)} onClose={() => setAnchorEl(null)}>
        {menuItems.map((item) => (
          <MenuItem
            key={item.key}
            disabled={item.disabled}
            onClick={() => {
              setAnchorEl(null);
              item.onClick();
            }}
          >
            {item.icon ? <span style={{ marginRight: 10, display: "inline-flex" }}>{item.icon}</span> : null}
            {item.label}
          </MenuItem>
        ))}
      </Menu>
    </>
  );
}
