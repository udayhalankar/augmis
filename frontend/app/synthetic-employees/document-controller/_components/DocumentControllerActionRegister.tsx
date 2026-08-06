"use client";
import { Fragment, useMemo, useState, useTransition } from "react";

import ChevronRightRoundedIcon from "@mui/icons-material/ChevronRightRounded";
import KeyboardArrowDownRoundedIcon from "@mui/icons-material/KeyboardArrowDownRounded";
import { AdminTableCard } from "@/components/data-display/AdminTableCard";
import { AdminTableLoadingState } from "@/components/data-display/AdminTableLoadingState";
import { AdminTableRowToggleButton } from "@/components/data-display/AdminTableRowToggleButton";
import {
  ADMIN_TABLE_SELECTION_CELL_SX,
  AdminTableRowSelectionControl,
  AdminTableSelectAllControl,
} from "@/components/data-display/AdminTableSelectionControls";
import {
  ActionMenuButton,
  type ActionMenuItemConfig,
} from "@/components/data-display/ActionMenuButton";
import { ADMIN_TABLE_CARD_PAGINATION_SX } from "@/components/data-display/AdminTableCard";
import { DocumentControllerDocumentLink } from "@/app/synthetic-employees/document-controller/_components/DocumentControllerDocumentLink";
import type { DocumentControllerExceptionItem } from "@/app/synthetic-employees/document-controller/_components/documentControllerExceptions";
import {
  ADMIN_DATA_TABLE_CELL_CONTENT_SX,
  ADMIN_DATA_TABLE_SX,
  mergeAdminTableSx,
} from "@/components/data-display/adminTableStyles";
import {
  Box,
  Button,
  Chip,
  Collapse,
  Skeleton,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TablePagination,
  TableRow,
  TableSortLabel,
  TextField,
  Typography,
} from "@mui/material";

type ActionItem = {
  command_id?: string | null;
  document_title?: string | null;
  identity_id?: string | null;
  version_id?: string | null;
  document_type_code?: string | null;
  document_status?: string | null;
  overdue_task_count?: number | null;
  command_type?: string | null;
  source_recommendation_type?: string | null;
  source_recommendation_summary?: string | null;
  source_recommendation_id?: string | null;
  status?: string | null;
  approval_status?: string | null;
  repository_id?: string | null;
  latest_execution?: {
    status?: string | null;
    artifact_path?: string | null;
  } | null;
  failure_reason?: string | null;
  exceptions?: DocumentControllerExceptionItem[];
};

type SortField =
  | "document_title"
  | "document_type_code"
  | "document_status"
  | "overdue_task_count"
  | "command_type";

type ActionRegisterProps = {
  items: ActionItem[];
  enableRowSelection?: boolean;
  loading?: boolean;
  isPending?: boolean;
  onApprove: (commandId: string) => Promise<unknown>;
  onReject: (commandId: string) => Promise<unknown>;
  onDispatch: (commandId: string) => Promise<unknown>;
  onAcknowledge: (commandId: string) => Promise<unknown>;
  onFail: (commandId: string) => Promise<unknown>;
  onRollback: (commandId: string) => Promise<unknown>;
  onOpenFile: (identityId: string, versionId?: string | null) => void;
};

type ActionMenuDefinition = {
  key: string;
  label: string;
  resolveHref?: (item: ActionItem) => string | undefined;
  isDisabled?: (item: ActionItem) => boolean;
  onSelect?: (item: ActionItem) => void;
};

const ACTION_TRIGGER_SX = {
  minWidth: 80,
  height: 24,
  px: 1.15,
  fontSize: 10.25,
  "& .MuiSvgIcon-root": {
    fontSize: 16,
  },
} as const;

const ACTION_MENU_SX = {
  "& .MuiPaper-root": {
    minWidth: 188,
    borderRadius: "5px",
  },
} as const;

const TOGGLE_CELL_SX = {
  width: 38,
  px: 1,
} as const;

const EXPANDED_ROW_CELL_SX = {
  px: 0,
  py: 0,
  borderTop: "none",
  backgroundColor: "#FBFDFF",
} as const;

const EXPANDED_ROW_CONTENT_SX = {
  pl: 6.75,
  pr: 2.5,
  py: 1.4,
  backgroundColor: "#FBFDFF",
} as const;

const EXPANDED_DETAIL_STACK_SX = {
  width: "100%",
  maxWidth: 760,
} as const;

const EXCEPTION_TOGGLE_BUTTON_SX = {
  minWidth: 102,
  borderRadius: "999px",
  px: 1,
  py: 0.3,
  fontSize: 9.25,
  fontWeight: 700,
  textTransform: "none",
  lineHeight: 1.2,
  whiteSpace: "nowrap",
  "& .MuiSvgIcon-root": {
    fontSize: 15,
  },
} as const;

const INBOX_TABLE_SX = mergeAdminTableSx(ADMIN_DATA_TABLE_SX, {
  "& .MuiTableBody-root .MuiTableCell-root": {
    py: 0.55,
  },
});

const EXPANDED_DETAIL_LABEL_SX = {
  fontSize: 11,
  fontWeight: 700,
  letterSpacing: 0.4,
  textTransform: "uppercase",
  color: "#7B8794",
} as const;

const EXPANDED_DETAIL_VALUE_SX = {
  ...ADMIN_DATA_TABLE_CELL_CONTENT_SX,
  whiteSpace: "normal",
  overflow: "visible",
  textOverflow: "unset",
  fontWeight: 400,
  color: "#102A43",
  wordBreak: "break-word",
} as const;

function renderStatusChip(value?: string | null) {
  const normalized = String(value || "").toUpperCase();
  const color =
    normalized === "APPROVED" ||
    normalized === "ACKNOWLEDGED" ||
    normalized === "ROLLED_BACK"
      ? "success"
      : normalized === "REJECTED" || normalized === "FAILED"
        ? "error"
        : normalized === "PENDING_APPROVAL" || normalized === "ROLLBACK_PENDING"
          ? "warning"
          : normalized === "DISPATCHED"
            ? "info"
            : "default";

  return (
    <Chip
      size="small"
      label={(normalized || "-").replaceAll("_", " ")}
      color={color as any}
      variant="outlined"
      sx={{
        height: 24,
        borderRadius: 999,
        fontSize: 10.5,
        fontWeight: 600,
        letterSpacing: 0.1,
        backgroundColor: "#FFFFFF",
      }}
    />
  );
}

function formatActionType(value?: string | null) {
  return String(value || "-")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function renderExpandedDetailValue(value: string) {
  return <Typography sx={EXPANDED_DETAIL_VALUE_SX}>{value}</Typography>;
}

function resolveRowKey(item: ActionItem) {
  return item.identity_id || item.command_id || item.document_title || "row";
}

function resolveSearchText(item: ActionItem) {
  return [
    item.document_title,
    item.identity_id,
    item.command_type,
    item.source_recommendation_type,
    item.source_recommendation_summary,
    item.source_recommendation_id,
    item.status,
    item.approval_status,
    item.repository_id,
    item.latest_execution?.artifact_path,
    item.latest_execution?.status,
    item.failure_reason,
    ...(item.exceptions || []).map((exception) => exception.type),
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
}

export function DocumentControllerActionRegister({
  items,
  enableRowSelection = false,
  loading = false,
  isPending = false,
  onApprove,
  onReject,
  onDispatch,
  onAcknowledge,
  onFail,
  onRollback,
  onOpenFile,
}: ActionRegisterProps) {
  const [searchValue, setSearchValue] = useState("");
  const [page, setPage] = useState(0);
  const [sortField, setSortField] = useState<SortField>("document_title");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("asc");
  const [expandedCommandIds, setExpandedCommandIds] = useState<Set<string>>(() => new Set());
  const [selectedRowIds, setSelectedRowIds] = useState<Set<string>>(() => new Set());
  const [transitionPending, startTransition] = useTransition();
  const rowsPerPage = 10;
  const pending = isPending || transitionPending;

  const filteredItems = useMemo(() => {
    const query = searchValue.trim().toLowerCase();
    if (!query) {
      return items;
    }
    return items.filter((item) => resolveSearchText(item).includes(query));
  }, [items, searchValue]);

  const sortedItems = useMemo(() => {
    const resolveValue = (item: ActionItem) => {
      switch (sortField) {
        case "document_title":
          return String(item.document_title || item.identity_id || "").toLowerCase();
        case "document_type_code":
          return String(item.document_type_code || "").toLowerCase();
        case "document_status":
          return String(item.document_status || "").toLowerCase();
        case "overdue_task_count":
          return Number(item.overdue_task_count ?? 0);
        case "command_type":
          return String(item.command_type || "").toLowerCase();
        default:
          return "";
      }
    };

    return [...filteredItems].sort((left, right) => {
      const leftValue = resolveValue(left);
      const rightValue = resolveValue(right);
      if (leftValue < rightValue) {
        return sortDirection === "asc" ? -1 : 1;
      }
      if (leftValue > rightValue) {
        return sortDirection === "asc" ? 1 : -1;
      }
      return 0;
    });
  }, [filteredItems, sortDirection, sortField]);

  const pagedItems = useMemo(
    () => sortedItems.slice(page * rowsPerPage, (page + 1) * rowsPerPage),
    [page, sortedItems],
  );

  const runAction = (action: () => Promise<unknown>) => {
    startTransition(async () => {
      await action();
    });
  };

  const actionMenuDefinitions = useMemo<ActionMenuDefinition[]>(
    () => [
      {
        key: "view-document",
        label: "View document",
        resolveHref: (item) =>
          item.identity_id
            ? `/synthetic-employees/document-controller/documents/${encodeURIComponent(item.identity_id)}`
            : undefined,
        isDisabled: (item) => !item.identity_id,
      },
      {
        key: "open-file",
        label: "Open file",
        isDisabled: (item) => !item.identity_id,
        onSelect: (item) => {
          if (item.identity_id) {
            onOpenFile(item.identity_id, item.version_id);
          }
        },
      },
      {
        key: "approve",
        label: "Approve",
        isDisabled: (item) => pending || !item.command_id || item.status !== "PENDING_APPROVAL",
        onSelect: (item) => {
          if (item.command_id) {
            runAction(() => onApprove(item.command_id!));
          }
        },
      },
      {
        key: "reject",
        label: "Reject",
        isDisabled: (item) => pending || !item.command_id || item.status !== "PENDING_APPROVAL",
        onSelect: (item) => {
          if (item.command_id) {
            runAction(() => onReject(item.command_id!));
          }
        },
      },
      {
        key: "dispatch",
        label: "Dispatch",
        isDisabled: (item) => pending || !item.command_id || item.status !== "APPROVED",
        onSelect: (item) => {
          if (item.command_id) {
            runAction(() => onDispatch(item.command_id!));
          }
        },
      },
      {
        key: "acknowledge",
        label: "Acknowledge",
        isDisabled: (item) => pending || !item.command_id || item.status !== "DISPATCHED",
        onSelect: (item) => {
          if (item.command_id) {
            runAction(() => onAcknowledge(item.command_id!));
          }
        },
      },
      {
        key: "fail",
        label: "Fail",
        isDisabled: (item) =>
          pending ||
          !item.command_id ||
          !["APPROVED", "DISPATCHED"].includes(String(item.status || "").toUpperCase()),
        onSelect: (item) => {
          if (item.command_id) {
            runAction(() => onFail(item.command_id!));
          }
        },
      },
      {
        key: "rollback",
        label: "Rollback",
        isDisabled: (item) =>
          pending ||
          !item.command_id ||
          !["ACKNOWLEDGED", "FAILED"].includes(String(item.status || "").toUpperCase()),
        onSelect: (item) => {
          if (item.command_id) {
            runAction(() => onRollback(item.command_id!));
          }
        },
      },
    ],
    [onAcknowledge, onApprove, onDispatch, onFail, onOpenFile, onReject, onRollback, pending],
  );

  const resolveActionMenuItems = (item: ActionItem): Array<ActionMenuItemConfig<ActionItem>> =>
    actionMenuDefinitions.map((definition) => ({
      key: definition.key,
      label: definition.label,
      disabled: definition.isDisabled?.(item) ?? false,
      href: definition.resolveHref?.(item),
      onSelect: definition.onSelect,
    }));

  const toggleExpandedRow = (commandId: string) => {
    setExpandedCommandIds((current) => {
      const next = new Set(current);
      if (next.has(commandId)) {
        next.delete(commandId);
      } else {
        next.add(commandId);
      }
      return next;
    });
  };

  const handleSort = (field: SortField) => {
    setPage(0);
    if (sortField === field) {
      setSortDirection((current) => (current === "asc" ? "desc" : "asc"));
      return;
    }
    setSortField(field);
    setSortDirection("asc");
  };

  const pagedRowKeys = useMemo(() => pagedItems.map((item) => resolveRowKey(item)), [pagedItems]);
  const selectedPagedRowCount = useMemo(
    () => pagedRowKeys.filter((key) => selectedRowIds.has(key)).length,
    [pagedRowKeys, selectedRowIds],
  );
  const allPagedRowsSelected = pagedRowKeys.length > 0 && selectedPagedRowCount === pagedRowKeys.length;
  const somePagedRowsSelected =
    selectedPagedRowCount > 0 && selectedPagedRowCount < pagedRowKeys.length;

  const toggleRowSelection = (rowKey: string, checked: boolean) => {
    setSelectedRowIds((current) => {
      const next = new Set(current);
      if (checked) {
        next.add(rowKey);
      } else {
        next.delete(rowKey);
      }
      return next;
    });
  };

  const toggleSelectAllPagedRows = (checked: boolean) => {
    setSelectedRowIds((current) => {
      const next = new Set(current);
      pagedRowKeys.forEach((rowKey) => {
        if (checked) {
          next.add(rowKey);
        } else {
          next.delete(rowKey);
        }
      });
      return next;
    });
  };

  const firstColumnColSpan = enableRowSelection ? 8 : 7;

  return (
    <>
      <AdminTableCard
        title="Inbox"
        // description="Registered document identities with mapped action, exception, and workflow follow-up context."
        // accentLabel="Inbox"
        summary={
          loading ? (
            <Skeleton variant="text" width={168} height={22} />
          ) : (
            `${filteredItems.length} documents available`
          )
        }
        headerActions={
          <TextField
            size="small"
            placeholder="Search inbox"
            value={searchValue}
            onChange={(event) => {
              setSearchValue(event.target.value);
              setPage(0);
            }}
            sx={{ width: { xs: "100%", sm: 320 } }}
          />
        }
        bodySx={{ px: 0, pb: 0 }}
        footerEnd={
          !loading ? (
            <TablePagination
              component="div"
              count={sortedItems.length}
              page={page}
              onPageChange={(_, nextPage) => setPage(nextPage)}
              rowsPerPage={rowsPerPage}
              rowsPerPageOptions={[10]}
              sx={ADMIN_TABLE_CARD_PAGINATION_SX}
            />
          ) : null
        }
      >
        {loading ? (
          <Box sx={{ px: 0, pb: 0 }}>
            <AdminTableLoadingState
              columnCount={enableRowSelection ? 8 : 7}
              rowCount={8}
              showCountLabel={false}
            />
          </Box>
        ) : (
          <>
            <Table size="small" sx={INBOX_TABLE_SX}>
              <TableHead>
                <TableRow>
                  <TableCell sx={enableRowSelection ? ADMIN_TABLE_SELECTION_CELL_SX : TOGGLE_CELL_SX}>
                    {enableRowSelection ? (
                      <AdminTableSelectAllControl
                        checked={allPagedRowsSelected}
                        indeterminate={somePagedRowsSelected}
                        onChange={toggleSelectAllPagedRows}
                      />
                    ) : null}
                  </TableCell>
                  <TableCell sortDirection={sortField === "document_title" ? sortDirection : false}>
                    <TableSortLabel
                      active={sortField === "document_title"}
                      direction={sortField === "document_title" ? sortDirection : "asc"}
                      onClick={() => handleSort("document_title")}
                    >
                      Document
                    </TableSortLabel>
                  </TableCell>
                  <TableCell sortDirection={sortField === "document_type_code" ? sortDirection : false}>
                    <TableSortLabel
                      active={sortField === "document_type_code"}
                      direction={sortField === "document_type_code" ? sortDirection : "asc"}
                      onClick={() => handleSort("document_type_code")}
                    >
                      Type
                    </TableSortLabel>
                  </TableCell>
                  <TableCell sortDirection={sortField === "document_status" ? sortDirection : false}>
                    <TableSortLabel
                      active={sortField === "document_status"}
                      direction={sortField === "document_status" ? sortDirection : "asc"}
                      onClick={() => handleSort("document_status")}
                    >
                      Document Status
                    </TableSortLabel>
                  </TableCell>
                  <TableCell sortDirection={sortField === "overdue_task_count" ? sortDirection : false}>
                    <TableSortLabel
                      active={sortField === "overdue_task_count"}
                      direction={sortField === "overdue_task_count" ? sortDirection : "asc"}
                      onClick={() => handleSort("overdue_task_count")}
                    >
                      Overdue
                    </TableSortLabel>
                  </TableCell>
                  <TableCell>Exceptions</TableCell>
                  <TableCell align="center">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {pagedItems.length ? (
                  pagedItems.map((item) => {
                const rowKey = resolveRowKey(item);
                const sourceLabel = item.source_recommendation_type || "Manual";
                const sourceDetail =
                  item.source_recommendation_summary ||
                  item.source_recommendation_id ||
                  "No recommendation source";
                const exceptions = item.exceptions || [];
                const expanded = expandedCommandIds.has(rowKey);

                    return (
                      <Fragment key={rowKey}>
                        <TableRow hover>
                          <TableCell
                            align="center"
                            sx={enableRowSelection ? ADMIN_TABLE_SELECTION_CELL_SX : TOGGLE_CELL_SX}
                          >
                            {enableRowSelection ? (
                              <AdminTableRowSelectionControl
                                checked={selectedRowIds.has(rowKey)}
                                onChange={(checked) => toggleRowSelection(rowKey, checked)}
                                endAdornment={
                                  <AdminTableRowToggleButton
                                    expanded={expanded}
                                    onClick={() => toggleExpandedRow(rowKey)}
                                  />
                                }
                              />
                            ) : (
                              <AdminTableRowToggleButton
                                expanded={expanded}
                                onClick={() => toggleExpandedRow(rowKey)}
                              />
                            )}
                          </TableCell>
                          <TableCell>
                            <DocumentControllerDocumentLink
                              identityId={item.identity_id}
                              label={item.document_title || item.identity_id || item.command_id}
                              sx={ADMIN_DATA_TABLE_CELL_CONTENT_SX}
                            />
                          </TableCell>
                          <TableCell>
                            <Box
                              component="span"
                              sx={ADMIN_DATA_TABLE_CELL_CONTENT_SX}
                              title={item.document_type_code || "Pending"}
                            >
                              {item.document_type_code || "Pending"}
                            </Box>
                          </TableCell>
                          <TableCell>
                            <Box
                              component="span"
                              sx={ADMIN_DATA_TABLE_CELL_CONTENT_SX}
                              title={item.document_status || "-"}
                            >
                              {item.document_status || "-"}
                            </Box>
                          </TableCell>
                          <TableCell>
                            <Box
                              component="span"
                              sx={ADMIN_DATA_TABLE_CELL_CONTENT_SX}
                              title={String(item.overdue_task_count ?? 0)}
                            >
                              {item.overdue_task_count ?? 0}
                            </Box>
                          </TableCell>
                          <TableCell>
                            {exceptions.length ? (
                              <Button
                                size="small"
                                variant="outlined"
                                endIcon={
                                  expanded ? (
                                    <KeyboardArrowDownRoundedIcon fontSize="small" />
                                  ) : (
                                    <ChevronRightRoundedIcon fontSize="small" />
                                  )
                                }
                                onClick={() => toggleExpandedRow(rowKey)}
                                sx={EXCEPTION_TOGGLE_BUTTON_SX}
                              >
                                Show Exceptions
                              </Button>
                            ) : (
                              <Box
                                component="span"
                                sx={{ ...ADMIN_DATA_TABLE_CELL_CONTENT_SX, color: "#9AA5B1" }}
                              >
                                -
                              </Box>
                            )}
                          </TableCell>
                          <TableCell align="center">
                            <ActionMenuButton
                              context={item}
                              items={resolveActionMenuItems(item)}
                              label="Actions"
                              buttonSx={ACTION_TRIGGER_SX}
                              menuSx={ACTION_MENU_SX}
                            />
                          </TableCell>
                        </TableRow>
                        {expanded ? (
                          <TableRow>
                            <TableCell colSpan={firstColumnColSpan} sx={EXPANDED_ROW_CELL_SX}>
                              <Collapse in timeout="auto">
                                <Stack spacing={1.2} sx={EXPANDED_ROW_CONTENT_SX}>
                                  <Stack spacing={1.35} sx={EXPANDED_DETAIL_STACK_SX}>
                                    <Stack spacing={0.45}>
                                      <Typography sx={EXPANDED_DETAIL_LABEL_SX}>
                                        Document
                                      </Typography>
                                      {renderExpandedDetailValue(
                                        item.document_title || item.identity_id || item.command_id || "-"
                                      )}
                                    </Stack>
                                    <Stack spacing={0.45}>
                                      <Typography sx={EXPANDED_DETAIL_LABEL_SX}>
                                        Repository
                                      </Typography>
                                      {renderExpandedDetailValue(item.repository_id || "-")}
                                    </Stack>
                                    <Stack spacing={0.45}>
                                      <Typography sx={EXPANDED_DETAIL_LABEL_SX}>
                                        Action Type
                                      </Typography>
                                      {renderExpandedDetailValue(
                                        formatActionType(item.command_type)
                                      )}
                                    </Stack>
                                    <Stack spacing={0.45}>
                                      <Typography sx={EXPANDED_DETAIL_LABEL_SX}>
                                        Source
                                      </Typography>
                                      {renderExpandedDetailValue(
                                        formatActionType(sourceLabel)
                                      )}
                                    </Stack>
                                    <Stack spacing={0.45}>
                                      <Typography sx={EXPANDED_DETAIL_LABEL_SX}>
                                        Status
                                      </Typography>
                                      <Box component="span" sx={{ display: "inline-flex", alignSelf: "flex-start" }}>
                                        {renderStatusChip(item.status)}
                                      </Box>
                                    </Stack>
                                    <Stack spacing={0.45}>
                                      <Typography sx={EXPANDED_DETAIL_LABEL_SX}>
                                        Approval
                                      </Typography>
                                      <Box component="span" sx={{ display: "inline-flex", alignSelf: "flex-start" }}>
                                        {renderStatusChip(item.approval_status)}
                                      </Box>
                                    </Stack>
                                    <Stack spacing={0.45}>
                                      <Typography sx={EXPANDED_DETAIL_LABEL_SX}>
                                        Overdue
                                      </Typography>
                                      {renderExpandedDetailValue(String(item.overdue_task_count ?? 0))}
                                    </Stack>
                                    {exceptions.length ? (
                                      <Stack spacing={0.55}>
                                        <Typography sx={EXPANDED_DETAIL_LABEL_SX}>
                                          Exceptions
                                        </Typography>
                                        <Stack spacing={0.45}>
                                          {exceptions.map((exception) => (
                                            <Typography key={exception.id} sx={EXPANDED_DETAIL_VALUE_SX}>
                                              {exception.type}
                                            </Typography>
                                          ))}
                                        </Stack>
                                      </Stack>
                                    ) : null}
                                    <Stack spacing={0.45}>
                                      <Typography sx={EXPANDED_DETAIL_LABEL_SX}>
                                        {`${formatActionType(sourceLabel)} Detail`}
                                      </Typography>
                                      {renderExpandedDetailValue(sourceDetail)}
                                    </Stack>
                                  </Stack>
                                </Stack>
                              </Collapse>
                            </TableCell>
                          </TableRow>
                        ) : null}
                      </Fragment>
                    );
                  })
                ) : (
                  <TableRow>
                    <TableCell colSpan={firstColumnColSpan}>No actions match the current search.</TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </>
        )}
      </AdminTableCard>
    </>
  );
}
