"use client";

import Link from "next/link";
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Grid,
  Stack,
  Typography,
} from "@mui/material";

import DashboardCustomizeOutlinedIcon from "@mui/icons-material/DashboardCustomizeOutlined";
import Groups2OutlinedIcon from "@mui/icons-material/Groups2Outlined";
import TimerOutlinedIcon from "@mui/icons-material/TimerOutlined";
import ArrowForwardOutlinedIcon from "@mui/icons-material/ArrowForwardOutlined";
const headlineFontFamily = '"Segoe UI", Roboto, sans-serif';

const solutions = [
  {
    title: "Infomentica DSS",
    description:
      "Open the executive decision-support workspace with dashboards, repository intelligence, enterprise search, and governed AI copilots.",
    href: "/infomentica",
    icon: <DashboardCustomizeOutlinedIcon fontSize="large" />,
    badge: "Secure Workspace",
  },
  {
    title: "AI Synthetic Employees",
    description:
      "Review the AUGMIS solution page for Syncora and Cyncora digital workers built for repetitive enterprise knowledge tasks.",
    href: "/synthetic-employees",
    icon: <Groups2OutlinedIcon fontSize="large" />,
    badge: "Solution Brief",
  },
  {
    title: "TICOSA",
    description:
      "Explore the Time Compression Systems offering for compressing long business workflows into structured AI-assisted cycles.",
    href: "/ticosa",
    icon: <TimerOutlinedIcon fontSize="large" />,
    badge: "Solution Brief",
  },
];

export default function HomeLauncherPage() {
  return (
    <Stack spacing={8.8541666667} sx={{ py: { xs: 3, md: 4 }, alignItems: "center" }}>
      <Box
        sx={{
          width: "100%",
          maxWidth: 1080,
          mx: "auto",
          pt: "25px",
          textAlign: "center",
        }}
      >
        <Typography
          variant="h2"
          sx={{
            fontWeight: 800,
            color: "#0b0b0d",
            fontFamily: headlineFontFamily,
            letterSpacing: "-0.03em",
            lineHeight: 1.1,
            fontSize: { xs: "1.4rem", md: "2.4rem" },
            maxWidth: 980,
            mx: "auto",
          }}
        >
          Open the right AUGMIS experience from one secure home page.
        </Typography>
        <Typography
          sx={{
            mt: 1.5,
            maxWidth: 980,
            mx: "auto",
            color: "#111827",
            fontWeight: 700,
            lineHeight: 1.45,
            fontSize: { xs: "0.92rem", md: "1rem" },
          }}
        >
          Infomentica DSS opens the working application. The other cards take users to the
          product solution pages so they can review the offering before deciding what they want to use next.
        </Typography>
      </Box>

      <Box sx={{ width: "100%", maxWidth: 1560, mx: "auto", px: { xs: 2, md: 14 } }}>
        <Grid container spacing={2.25} sx={{ justifyContent: "center" }}>
          {solutions.map((solution) => (
            <Grid key={solution.title} size={{ xs: 12, md: 4 }}>
              <Card
                sx={{
                  height: "100%",
                  width: "100%",
                  display: "flex",
                  flexDirection: "column",
                  borderRadius: "18px",
                  background: "linear-gradient(180deg, #072b76 0%, #0b5fb0 100%)",
                  color: "#fff",
                  boxShadow: "0 10px 28px rgba(5, 25, 80, 0.14)",
                  border: "none",
                }}
              >
                <CardContent
                  sx={{
                    p: { xs: 2.25, md: 3 },
                    flex: 1,
                    display: "flex",
                    flexDirection: "column",
                    textAlign: "left",
                  }}
                >
                  <Stack spacing={1.65} sx={{ flex: 1, width: "100%", alignItems: "stretch" }}>
                    <Box
                      sx={{
                        width: 44,
                        height: 44,
                        borderRadius: "8px",
                        display: "grid",
                        placeItems: "center",
                        bgcolor: "#fff",
                        color: "#0b5fb0",
                        alignSelf: "flex-start",
                      }}
                    >
                      {solution.icon}
                    </Box>

                    <Box sx={{ width: "100%" }}>
                      <Chip
                        label={solution.badge}
                        size="small"
                        sx={{
                          mb: 1.2,
                          bgcolor: "rgba(255,255,255,0.12)",
                          color: "#fff",
                          fontWeight: 500,
                        }}
                      />
                      <Typography
                        variant="h4"
                        sx={{
                          fontWeight: 800,
                          color: "#fff",
                          fontSize: { xs: "1.55rem", md: "1.8rem" },
                          lineHeight: 1.08,
                        }}
                      >
                        {solution.title}
                      </Typography>
                      <Typography
                        sx={{
                          mt: 1.2,
                          lineHeight: 1.3,
                          color: "rgba(255,255,255,0.96)",
                          fontSize: { xs: "0.84rem", md: "0.86rem" },
                        }}
                      >
                        {solution.description}
                      </Typography>
                    </Box>

                    <Box sx={{ flexGrow: 1 }} />

                    <Box sx={{ display: "flex", justifyContent: "flex-start" }}>
                      <Button
                        component={Link}
                        href={solution.href}
                        variant="contained"
                        endIcon={<ArrowForwardOutlinedIcon />}
                        sx={{
                          borderRadius: "7px",
                          bgcolor: "#93d86b",
                          color: "#fff",
                          boxShadow: "none",
                          px: 2,
                          py: 0.7,
                          minHeight: 0,
                          fontSize: "0.8rem",
                          "&:hover": {
                            bgcolor: "#82c85b",
                            boxShadow: "none",
                          },
                          "& .MuiButton-endIcon": {
                            ml: 1,
                          },
                        }}
                      >
                        Open
                      </Button>
                    </Box>
                  </Stack>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      </Box>
    </Stack>
  );
}
