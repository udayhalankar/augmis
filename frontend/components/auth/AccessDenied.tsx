"use client";

import { Box, Button, Paper, Typography } from "@mui/material";
import LockOutlinedIcon from "@mui/icons-material/LockOutlined";
import { useRouter } from "next/navigation";

export default function AccessDenied() {
  const router = useRouter();

  return (
    <Box sx={{ p: 4 }}>
      <Paper
        elevation={0}
        sx={{
          p: 5,
          borderRadius: 4,
          border: "1px solid",
          borderColor: "divider",
          textAlign: "center",
          maxWidth: 560,
          mx: "auto",
          mt: 8,
        }}
      >
        <LockOutlinedIcon
          sx={{ fontSize: 56, mb: 2, color: "text.secondary" }}
        />

        <Typography variant="h5" sx={{ fontWeight: 800, mb: 1 }}>
          Access Denied
        </Typography>

        <Typography color="text.secondary" sx={{ mb: 3 }}>
          You do not have permission to access this module.
        </Typography>

        <Button variant="contained" onClick={() => router.push("/")}>
          Go to Dashboard
        </Button>
      </Paper>
    </Box>
  );
}
