"use client";

import ChevronRightRoundedIcon from "@mui/icons-material/ChevronRightRounded";
import ExpandMoreRoundedIcon from "@mui/icons-material/ExpandMoreRounded";
import { IconButton } from "@mui/material";

type SimpleSx = Record<string, any>;

type AdminTableRowToggleButtonProps = {
  expanded: boolean;
  onClick: () => void;
  sx?: SimpleSx;
};

export const ADMIN_TABLE_ROW_TOGGLE_BUTTON_SX = {
  width: 22,
  height: 22,
  borderRadius: "5px",
  color: "#6B7C93",
  "&:hover": {
    backgroundColor: "rgba(49, 95, 181, 0.08)",
    color: "#315FB5",
  },
  "& .MuiSvgIcon-root": {
    fontSize: 18,
  },
} as const;

function mergeSx(...items: Array<SimpleSx | undefined>) {
  return items.reduce<SimpleSx>((acc, item) => {
    if (!item) {
      return acc;
    }
    return { ...acc, ...item };
  }, {});
}

export function AdminTableRowToggleButton({
  expanded,
  onClick,
  sx,
}: AdminTableRowToggleButtonProps) {
  return (
    <IconButton
      size="small"
      aria-label={expanded ? "Collapse row" : "Expand row"}
      onClick={onClick}
      sx={mergeSx(ADMIN_TABLE_ROW_TOGGLE_BUTTON_SX, sx)}
    >
      {expanded ? <ExpandMoreRoundedIcon /> : <ChevronRightRoundedIcon />}
    </IconButton>
  );
}
