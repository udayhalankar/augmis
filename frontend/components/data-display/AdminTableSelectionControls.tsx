"use client";

import { Box, Checkbox } from "@mui/material";

type SimpleSx = Record<string, any>;

type AdminTableSelectAllControlProps = {
  checked: boolean;
  indeterminate?: boolean;
  onChange: (checked: boolean) => void;
  sx?: SimpleSx;
};

type AdminTableRowSelectionControlProps = {
  checked: boolean;
  onChange: (checked: boolean) => void;
  endAdornment?: React.ReactNode;
  sx?: SimpleSx;
};

export const ADMIN_TABLE_SELECTION_CELL_SX = {
  width: 66,
  px: 1,
} as const;

export const ADMIN_TABLE_SELECTION_CONTROL_SX = {
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  width: "100%",
  minWidth: 0,
  gap: 0.25,
} as const;

export const ADMIN_TABLE_SELECTION_CHECKBOX_SX = {
  p: 0.35,
  color: "#7B8794",
  "&.Mui-checked, &.MuiCheckbox-indeterminate": {
    color: "#315FB5",
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

export function AdminTableSelectAllControl({
  checked,
  indeterminate = false,
  onChange,
  sx,
}: AdminTableSelectAllControlProps) {
  return (
    <Box sx={mergeSx(ADMIN_TABLE_SELECTION_CONTROL_SX, sx)}>
      <Checkbox
        checked={checked}
        indeterminate={indeterminate}
        onChange={(_, value) => onChange(value)}
        slotProps={{ input: { "aria-label": "Select all rows" } }}
        sx={ADMIN_TABLE_SELECTION_CHECKBOX_SX}
      />
      <Box sx={{ width: 22, height: 22, flex: "0 0 22px" }} />
    </Box>
  );
}

export function AdminTableRowSelectionControl({
  checked,
  onChange,
  endAdornment,
  sx,
}: AdminTableRowSelectionControlProps) {
  return (
    <Box sx={mergeSx(ADMIN_TABLE_SELECTION_CONTROL_SX, sx)}>
      <Checkbox
        checked={checked}
        onChange={(_, value) => onChange(value)}
        slotProps={{ input: { "aria-label": "Select row" } }}
        sx={ADMIN_TABLE_SELECTION_CHECKBOX_SX}
      />
      <Box sx={{ display: "inline-flex", alignItems: "center", justifyContent: "center" }}>
        {endAdornment}
      </Box>
    </Box>
  );
}
