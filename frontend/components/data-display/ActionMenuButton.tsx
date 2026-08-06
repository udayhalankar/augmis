"use client";

import type { MouseEvent, ReactNode } from "react";
import { useState } from "react";

import ArrowDropDownIcon from "@mui/icons-material/ArrowDropDown";
import Link from "next/link";
import { Button, Menu, MenuItem } from "@mui/material";

type SimpleSx = Record<string, any>;

export type ActionMenuItemConfig<TContext> = {
  key: string;
  label: ReactNode;
  disabled?: boolean;
  href?: string;
  onSelect?: (context: TContext) => void;
};

type ActionMenuButtonProps<TContext> = {
  context: TContext;
  items: Array<ActionMenuItemConfig<TContext>>;
  label?: ReactNode;
  buttonSx?: SimpleSx;
  menuSx?: SimpleSx;
  menuItemSx?: SimpleSx;
};

const DEFAULT_BUTTON_SX = {
  minWidth: 96,
  height: 28,
  px: 1.35,
  borderRadius: "5px",
  fontSize: 12,
  fontWeight: 600,
  lineHeight: 1,
  textTransform: "none",
  whiteSpace: "nowrap",
  gap: 0.5,
  borderColor: "#A9BFDF",
  color: "#123D73",
  backgroundColor: "#FFFFFF",
  boxShadow: "none",
  "& .MuiButton-endIcon": {
    ml: 0,
  },
  "& .MuiSvgIcon-root": {
    fontSize: 18,
  },
  "&:hover": {
    borderColor: "#7F9EC8",
    backgroundColor: "#F7FAFC",
    boxShadow: "none",
  },
} as const;

const DEFAULT_MENU_SX = {
  "& .MuiPaper-root": {
    mt: 0.5,
    minWidth: 180,
    borderRadius: "5px",
    border: "1px solid #D7E2F0",
    boxShadow: "0 14px 32px rgba(15, 23, 42, 0.12)",
    overflow: "hidden",
  },
  "& .MuiMenu-list": {
    py: 0.5,
  },
} as const;

const DEFAULT_MENU_ITEM_SX = {
  minHeight: 34,
  px: 1.5,
  py: 0.875,
  borderRadius: 0,
  alignItems: "center",
  fontSize: 12.5,
  fontWeight: 500,
  color: "#102A43",
  "&.Mui-disabled": {
    opacity: 0.42,
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

export function ActionMenuButton<TContext>({
  context,
  items,
  label = "Actions",
  buttonSx,
  menuSx,
  menuItemSx,
}: ActionMenuButtonProps<TContext>) {
  const [anchorEl, setAnchorEl] = useState<HTMLElement | null>(null);
  const closeMenu = () => {
    setAnchorEl(null);
  };

  const openMenu = (event: MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  return (
    <>
      <Button
        size="small"
        variant="outlined"
        endIcon={<ArrowDropDownIcon />}
        sx={mergeSx(DEFAULT_BUTTON_SX, buttonSx)}
        onClick={openMenu}
      >
        {label}
      </Button>
      <Menu anchorEl={anchorEl} open={Boolean(anchorEl)} onClose={closeMenu} sx={mergeSx(DEFAULT_MENU_SX, menuSx)}>
        {items.map((item) => {
          const content = (
            <MenuItem
              key={item.key}
              disabled={item.disabled}
              sx={mergeSx(DEFAULT_MENU_ITEM_SX, menuItemSx)}
              onClick={() => {
                item.onSelect?.(context);
                closeMenu();
              }}
            >
              {item.label}
            </MenuItem>
          );

          if (item.href) {
            return (
              <MenuItem
                key={item.key}
                component={Link}
                href={item.href}
                disabled={item.disabled}
                sx={mergeSx(DEFAULT_MENU_ITEM_SX, menuItemSx)}
                onClick={closeMenu}
              >
                {item.label}
              </MenuItem>
            );
          }

          return content;
        })}
      </Menu>
    </>
  );
}
