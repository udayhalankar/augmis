"use client";

import Link from "next/link";
import { useEffect, useMemo, useState,  type MouseEvent, } from "react";

import BadgeOutlinedIcon from "@mui/icons-material/BadgeOutlined";
import ChevronRightRoundedIcon from "@mui/icons-material/ChevronRightRounded";
import ChevronLeftRoundedIcon from "@mui/icons-material/ChevronLeftRounded";
import DescriptionOutlinedIcon from "@mui/icons-material/DescriptionOutlined";
import MoreVertIcon from "@mui/icons-material/MoreVert";
import SearchIcon from "@mui/icons-material/Search";
import {
  Box,
  Button,
  Card,
  //CardActionArea,
  CardContent,
  Chip,
  CircularProgress,
  IconButton,
  InputAdornment,
  Menu,
  MenuItem,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";

import { OutletPage } from "@/components/layout/OutletPage";
import { getSymployees } from "@/services/symployeeService";

const NAVY = "#0B1F33";
const BLUE = "#2563EB";
const BORDER = "#E4EAF1";
const MUTED = "#64748B";
const PAGE_SIZE = 9;

const placeholderCards = [
  { name: "Symployee PO", typeLabel: "Procurement Officer", status: "PLANNED" },
  { name: "Symployee FIN", typeLabel: "Finance Officer", status: "PLANNED" },
  { name: "Symployee Legal", typeLabel: "Legal Officer", status: "PLANNED" },
  { name: "Symployee Safety Officer", typeLabel: "Safety Officer", status: "PLANNED" },
  { name: "Symployee HR", typeLabel: "Human Resources Officer", status: "PLANNED" },
];

function formatTypeLabel(value?: string | null) {
  if (!value) return "Synthetic Employee";
  return value
    .split("_")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function normalizeStatus(value?: string | null) {
  return String(value || "PLANNED").toUpperCase();
}

function statusChipProps(status?: string | null) {
  const normalized = normalizeStatus(status);
  if (normalized === "ACTIVE") {
    return {
      label: "Active",
      color: "success" as const,
      sx: { bgcolor: "#ECFDF3", borderColor: "#ABEFC6", color: "#067647" },
    };
  }
  if (normalized === "INACTIVE" || normalized === "DISABLED") {
    return {
      label: "Inactive",
      color: "default" as const,
      sx: { bgcolor: "#F2F4F7", borderColor: "#D0D5DD", color: "#475467" },
    };
  }
  return {
    label: "Planned",
    color: "warning" as const,
    sx: { bgcolor: "#FFFAEB", borderColor: "#FEDF89", color: "#B54708" },
  };
}

export default function SyntheticEmployeesPage() {
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchText, setSearchText] = useState("");
  const [page, setPage] = useState(0);
  
  const [menuAnchor, setMenuAnchor] = useState<null | HTMLElement>(null);
  const [menuCard, setMenuCard] = useState<any | null>(null);

  useEffect(() => {
    let active = true;
    getSymployees()
      .then((result) => {
        if (!active) return;
        setItems(result?.data?.items || []);
      })
      .catch((error) => {
        console.error("Unable to load synthetic employees", error);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const realCards = useMemo(
    () =>
      items.map((item) => ({
        key: item.symployee_id,
        name: item.name,
        typeLabel: formatTypeLabel(item.employee_type),
        status: item.status,
        href:
          item.code === "document_controller"
            ? "/synthetic-employees/document-controller"
            : undefined,
      })),
    [items]
  );

  const cards = useMemo(() => {
    const liveNames = new Set(realCards.map((card) => card.name.trim().toLowerCase()));
    const derivedPlaceholders = placeholderCards
      .filter((card) => !liveNames.has(card.name.trim().toLowerCase()))
      .map((card) => ({
        key: `placeholder-${card.name}`,
        name: card.name,
        typeLabel: card.typeLabel,
        status: card.status,
        href: undefined,
      }));
    return [...realCards, ...derivedPlaceholders];
  }, [realCards]);

  const filteredCards = useMemo(() => {
    const query = searchText.trim().toLowerCase();
    if (!query) return cards;
    return cards.filter((card) =>
      [card.name, card.typeLabel, card.status]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(query))
    );
  }, [cards, searchText]);

  useEffect(() => {
    setPage(0);
  }, [searchText]);

  const pageCount = Math.max(1, Math.ceil(filteredCards.length / PAGE_SIZE));
  const safePage = Math.min(page, pageCount - 1);
  const startIndex = safePage * PAGE_SIZE;
  const pagedCards = filteredCards.slice(startIndex, startIndex + PAGE_SIZE);

  function openCardMenu(
  event: MouseEvent<HTMLElement>,
  card: any
  ) {
    event.preventDefault();
    event.stopPropagation();
    setMenuAnchor(event.currentTarget);
    setMenuCard(card);
  }

  function closeCardMenu() {
    setMenuAnchor(null);
    setMenuCard(null);
  }

  return (
    <OutletPage
      title="Synthetic Employees"
      description="Manage your digital workforce, monitor availability, and open active employee modules."
      actions={
        <TextField
          placeholder="Search synthetic employees"
          value={searchText}
          onChange={(event) => setSearchText(event.target.value)}
          size="small"
          sx={{
            width: {
              xs: "100%",
              md: 304,
            },
            "& .MuiOutlinedInput-root": {
              height: 35,
              borderRadius: 999,
              bgcolor: "#FFFFFF",
              boxShadow: "0 1px 2px rgba(16, 24, 40, 0.04)",
              "& fieldset": {
                borderColor: "#D0D5DD",
              },
            },
          }}
          slotProps={{
            input: {
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon fontSize="small" sx={{ color: MUTED }} />
                </InputAdornment>
              ),
            },
          }}
        />
      }
    >
            {loading ? (
              <Stack
                sx={{
                  minHeight: "50vh",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <CircularProgress />
              </Stack>
            ) : (
              <Stack spacing={3}>
                <Box
                  sx={{
                    display: "grid",
                    gridTemplateColumns: {
                      xs: "1fr",
                      md: "repeat(2, minmax(0, 1fr))",
                      xl: "repeat(3, minmax(0, 1fr))",
                    },
                    gap: 2.5,
                  }}
                >
                  {pagedCards.map((card) => {
                    const chip = statusChipProps(card.status);
                    const content = (
                      <CardContent
                          sx={{
                            p: 2,
                            height: "100%",
                            display: "grid",
                            gridTemplateRows: "34px minmax(0, 1fr) 28px",
                            rowGap: 1.5,

                            "&:last-child": {
                              pb: 2,
                            },
                          }}
                        >
                          {/* Icon and menu */}
                          <Box
                            sx={{
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "space-between",
                              minWidth: 0,
                            }}
                          >
                            <Box
                              sx={{
                                width: 32,
                                height: 32,
                                display: "grid",
                                placeItems: "center",
                                flexShrink: 0,
                                borderRadius: 2,
                                bgcolor: "#EFF6FF",
                                color: BLUE,
                                border: "1px solid #DBEAFE",
                              }}
                            >
                              <BadgeOutlinedIcon fontSize="small" />
                            </Box>

                            <IconButton
                              size="small"
                              onClick={(event) => openCardMenu(event, card)}
                              sx={{
                                width: 30,
                                height: 30,
                                flexShrink: 0,
                                color: MUTED,
                                border: "1px solid transparent",

                                "&:hover": {
                                  borderColor: BORDER,
                                  bgcolor: "#F8FAFC",
                                },
                              }}
                            >
                              <MoreVertIcon fontSize="small" />
                            </IconButton>
                          </Box>

                          {/* Title and type */}
                          <Box
                            sx={{
                              minWidth: 0,
                              display: "flex",
                              flexDirection: "column",
                              justifyContent: "center",
                            }}
                          >
                            <Typography
                              sx={{
                                color: NAVY,
                                fontWeight: 900,
                                lineHeight: 1.3,
                                fontSize: 14,
                                overflow: "hidden",
                                textOverflow: "ellipsis",
                                whiteSpace: "nowrap",
                              }}
                              title={card.name}
                            >
                              {card.name}
                            </Typography>

                            <Typography
                              sx={{
                                mt: 0.5,
                                color: MUTED,
                                fontSize: 10,
                                lineHeight: 1.4,
                                overflow: "hidden",
                                textOverflow: "ellipsis",
                                whiteSpace: "nowrap",
                              }}
                              title={card.typeLabel}
                            >
                              {card.typeLabel}
                            </Typography>
                          </Box>

                          {/* Footer */}
                          <Box
                            sx={{
                              display: "grid",
                              gridTemplateColumns: "auto minmax(0, 1fr)",
                              columnGap: 1.25,
                              alignItems: "center",
                              minWidth: 0,
                            }}
                          >
                            <Chip
                              size="small"
                              variant="outlined"
                              color={chip.color}
                              label={chip.label}
                              sx={{
                                height: 22,
                                minWidth: 66,
                                borderRadius: 999,
                                fontSize: 9,
                                fontWeight: 800,
                                justifySelf: "start",
                                ...chip.sx,
                              }}
                            />

                            {card.href ? (
                              <Button
                                component={Link}
                                href={card.href}
                                size="small"
                                endIcon={<ChevronRightRoundedIcon />}
                                sx={{
                                  minWidth: 0,
                                  height: 26,
                                  px: 0,
                                  justifySelf: "start",
                                  justifyContent: "flex-start",
                                  color: BLUE,
                                  textTransform: "none",
                                  fontWeight: 800,
                                  fontSize: 12,
                                  whiteSpace: "nowrap",

                                  "& .MuiButton-endIcon": {
                                    ml: 0.5,
                                  },
                                }}
                              >
                                Open module
                              </Button>
                            ) : (
                              <Typography
                                variant="caption"
                                sx={{
                                  justifySelf: "start",
                                  color: "#98A2B3",
                                  fontWeight: 700,
                                  fontSize: 10,
                                  lineHeight: 1,
                                  whiteSpace: "nowrap",
                                }}
                              >
                                Coming soon
                              </Typography>
                            )}
                          </Box>
                        </CardContent>
                    );

                    return (
                      <Card
                        key={card.key}
                        variant="outlined"
                        sx={{
                          height: 200,
                          borderRadius: 3,
                          borderColor: BORDER,
                          bgcolor: "#FFFFFF",
                          boxShadow: "0 1px 2px rgba(16, 24, 40, 0.03)",
                          overflow: "hidden",
                          transition: "transform 160ms ease, box-shadow 160ms ease, border-color 160ms ease",
                          "&:hover": {
                            transform: "translateY(-2px)",
                            borderColor: "#C7D7FE",
                            boxShadow: "0 10px 24px rgba(16, 24, 40, 0.08)",
                          },
                        }}
                      >
                        {content}
                      </Card>
                    );
                  })}
                </Box>

                {!pagedCards.length ? (
                  <Paper
                    variant="outlined"
                    sx={{
                      py: 8,
                      textAlign: "center",
                      borderRadius: 3,
                      borderColor: BORDER,
                      bgcolor: "#FFFFFF",
                    }}
                  >
                    <DescriptionOutlinedIcon sx={{ fontSize: 40, color: "#98A2B3" }} />
                    <Typography sx={{ mt: 1.5, color: NAVY, fontWeight: 800 }}>
                      No synthetic employees found
                    </Typography>
                    <Typography variant="body2" sx={{ mt: 0.5, color: MUTED }}>
                      Try a different search term.
                    </Typography>
                  </Paper>
                ) : null}

              
              

              <Box
  sx={{
    width: "100%",
    display: "flex",
    justifyContent: "flex-end",
    alignItems: "center",
    pt: 0.5,
  }}
>
  <Stack
    direction="row"
    spacing={1}
    sx={{
      alignItems: "center",
      justifyContent: "flex-end",
    }}
  >
    <Typography
      variant="body2"
      sx={{
        height: 32,
        display: "flex",
        alignItems: "center",
        color: MUTED,
        fontWeight: 600,
        fontSize: 12,
        lineHeight: 1,
        whiteSpace: "nowrap",
      }}
    >
      {filteredCards.length
        ? `${startIndex + 1}-${Math.min(
            startIndex + PAGE_SIZE,
            filteredCards.length
          )} of ${filteredCards.length}`
        : "0 of 0"}
    </Typography>

    <IconButton
      size="small"
      disabled={safePage === 0}
      onClick={() =>
        setPage((current) => Math.max(0, current - 1))
      }
      sx={{
        width: 36,
        height: 32,
        border: `1px solid ${BORDER}`,
        borderRadius: 1.5,
        bgcolor: "#FFFFFF",
      }}
    >
      <ChevronLeftRoundedIcon fontSize="small" />
    </IconButton>

    <IconButton
      size="small"
      disabled={safePage >= pageCount - 1}
      onClick={() =>
        setPage((current) =>
          Math.min(pageCount - 1, current + 1)
        )
      }
      sx={{
        width: 36,
        height: 32,
        border: `1px solid ${BORDER}`,
        borderRadius: 1.5,
        bgcolor: "#FFFFFF",
      }}
    >
      <ChevronRightRoundedIcon fontSize="small" />
    </IconButton>
  </Stack>
</Box>
              
              
              
              
                
              </Stack>
            )}
      <Menu
        anchorEl={menuAnchor}
        open={Boolean(menuAnchor)}
        onClose={closeCardMenu}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
        transformOrigin={{ vertical: "top", horizontal: "right" }}
        slotProps={{
          paper: {
            sx: {
              mt: 0.75,
              minWidth: 170,
              borderRadius: 2,
              border: `1px solid ${BORDER}`,
              boxShadow: "0 12px 28px rgba(16, 24, 40, 0.12)",
            },
          },
        }}
      >
        {menuCard?.href ? (
          <MenuItem component={Link} href={menuCard.href} onClick={closeCardMenu}>
            Open module
          </MenuItem>
        ) : (
          <MenuItem disabled>Module not available</MenuItem>
        )}
        <MenuItem onClick={closeCardMenu}>View details</MenuItem>
      </Menu>
    </OutletPage>
  );
}
