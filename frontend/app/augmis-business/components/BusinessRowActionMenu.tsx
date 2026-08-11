"use client";

import { useState, type MouseEvent, type ReactNode } from "react";

import MoreVertRoundedIcon from "@mui/icons-material/MoreVertRounded";
import VisibilityOutlinedIcon from "@mui/icons-material/VisibilityOutlined";
import { Button, IconButton, Menu, MenuItem, Stack, Tooltip } from "@mui/material";

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
              <Button
                size="small"
                variant="outlined"
                startIcon={<VisibilityOutlinedIcon fontSize="small" />}
                onClick={onView}
                sx={{
                  minWidth: 0,
                  px: 1,
                  py: 0.45,
                  textTransform: "none",
                  borderRadius: "8px",
                  fontSize: 12,
                  fontWeight: 700,
                }}
              >
                View
              </Button>
            </span>
          </Tooltip>
        ) : null}
        <Tooltip title="More actions">
          <span>
            <IconButton size="small" onClick={(event: MouseEvent<HTMLElement>) => setAnchorEl(event.currentTarget)}>
              <MoreVertRoundedIcon fontSize="small" />
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
