"use client";

type SimpleSx = Record<string, any>;

export const ADMIN_DATA_TABLE_SX = {
  tableLayout: "fixed",
  "& .MuiTableCell-root": {
    px: 2,
    py: 0.9,
    borderColor: "#D8E1EE",
    verticalAlign: "middle",
    fontSize: 12.5,
    lineHeight: 1.35,
    color: "#102A43",
  },
  "& .MuiTableHead-root .MuiTableCell-root": {
    py: 0.8,
    fontSize: 12.5,
    fontWeight: 600,
    lineHeight: 1.2,
    color: "#243B53",
    whiteSpace: "nowrap",
    backgroundColor: "#F7FAFC",
  },
  "& .MuiTableBody-root .MuiTableRow-root:hover": {
    backgroundColor: "#F8FBFF",
  },
} as const;

export const ADMIN_DATA_TABLE_CELL_CONTENT_SX = {
  display: "block",
  width: "100%",
  overflow: "hidden",
  textOverflow: "ellipsis",
  whiteSpace: "nowrap",
  lineHeight: 1.35,
  fontSize: 12.5,
} as const;

export const ADMIN_DATA_TABLE_EMPHASIS_TEXT_SX = {
  ...ADMIN_DATA_TABLE_CELL_CONTENT_SX,
  fontWeight: 600,
  color: "#102A43",
} as const;

export function mergeAdminTableSx(...items: Array<SimpleSx | undefined>) {
  return items.reduce<SimpleSx>((acc, item) => {
    if (!item) {
      return acc;
    }
    return { ...acc, ...item };
  }, {});
}
