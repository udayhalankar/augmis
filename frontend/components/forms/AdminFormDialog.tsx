"use client";

import type { ReactNode } from "react";

import CloseIcon from "@mui/icons-material/Close";
import {
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import type { TextFieldProps } from "@mui/material";

export const ADMIN_FORM_LABEL_SX = {
  display: "block",
  mb: 0.45,
  fontSize: "10px",
  fontWeight: 700,
  color: "#64748B",
  textTransform: "uppercase",
  letterSpacing: ".05em",
} as const;

export const ADMIN_FORM_HELPER_SX = {
  display: "block",
  mt: 0.45,
  fontSize: "12px",
  color: "#64748B",
  lineHeight: 1.35,
} as const;

export const ADMIN_FORM_TEXTFIELD_SX = {
  "& .MuiOutlinedInput-root": {
    borderRadius: "6px",
    minHeight: 36,
    fontSize: "12px",
    color: "#1E293B",
    backgroundColor: "#FFFFFF",
    "& fieldset": {
      borderColor: "#D1D5DB",
    },
    "&:hover fieldset": {
      borderColor: "#CBD5E1",
    },
    "&.Mui-focused fieldset": {
      borderColor: "#3B82F6",
      boxShadow: "0 0 0 2px rgba(59,130,246,.12)",
    },
  },
  "& .MuiInputBase-input": {
    px: 1.25,
    py: 0.85,
    "&::placeholder": {
      color: "#94A3B8",
      opacity: 1,
    },
  },
  "& .MuiInputBase-inputMultiline": {
    px: 0,
    py: 0,
    "&::placeholder": {
      color: "#94A3B8",
      opacity: 1,
    },
  },
  "& .MuiSelect-select": {
    px: 1.25,
    py: 0.85,
  },
  "& .MuiOutlinedInput-input.Mui-disabled": {
    WebkitTextFillColor: "#64748B",
  },
} as const;

export const ADMIN_FORM_MULTILINE_TEXTFIELD_SX = {
  "& .MuiOutlinedInput-root": {
    alignItems: "flex-start",
    pt: 0,
  },
  "& .MuiInputBase-inputMultiline": {
    padding: "2px 2px !important",
  },
  "& textarea": {
    padding: "0 !important",
    margin: 0,
  },
} as const;

type SimpleSx = Record<string, any>;

function mergeSx(...items: Array<SimpleSx | undefined>) {
  return items.reduce<SimpleSx>((acc, item) => {
    if (!item) {
      return acc;
    }
    return { ...acc, ...item };
  }, {});
}

type AdminFormDialogProps = {
  actions?: ReactNode;
  children: ReactNode;
  contentSx?: SimpleSx;
  maxWidth?: number;
  onClose: () => void;
  open: boolean;
  paperSx?: SimpleSx;
  stackSx?: SimpleSx;
  stackSpacing?: number;
  title: ReactNode;
  titleSx?: SimpleSx;
};

type AdminFormFieldProps = {
  children: ReactNode;
  helperText?: ReactNode;
  helperTextSx?: SimpleSx;
  label: ReactNode;
  labelSx?: SimpleSx;
};

type AdminFormTextFieldProps = Omit<TextFieldProps, "label" | "helperText"> & {
  fieldSx?: SimpleSx;
  helperText?: ReactNode;
  helperTextSx?: SimpleSx;
  label: ReactNode;
  labelSx?: SimpleSx;
};

export function AdminFormField({
  children,
  helperText,
  helperTextSx,
  label,
  labelSx,
}: AdminFormFieldProps) {
  return (
    <div>
      <Typography variant="caption" sx={mergeSx(ADMIN_FORM_LABEL_SX, labelSx)}>
        {label}
      </Typography>
      {children}
      {helperText ? (
        <Typography variant="caption" sx={mergeSx(ADMIN_FORM_HELPER_SX, helperTextSx)}>
          {helperText}
        </Typography>
      ) : null}
    </div>
  );
}

export function AdminFormTextField({
  fieldSx,
  fullWidth = true,
  helperText,
  helperTextSx,
  label,
  labelSx,
  multiline,
  ...props
}: AdminFormTextFieldProps) {
  return (
    <AdminFormField label={label} helperText={helperText} labelSx={labelSx} helperTextSx={helperTextSx}>
      <TextField
        {...props}
        multiline={multiline}
        fullWidth={fullWidth}
        sx={mergeSx(
          ADMIN_FORM_TEXTFIELD_SX,
          multiline ? ADMIN_FORM_MULTILINE_TEXTFIELD_SX : undefined,
          fieldSx
        )}
      />
    </AdminFormField>
  );
}

export function AdminFormDialog({
  actions,
  children,
  contentSx,
  maxWidth = 570,
  onClose,
  open,
  paperSx,
  stackSx,
  stackSpacing = 1.05,
  title,
  titleSx,
}: AdminFormDialogProps) {
  return (
    <Dialog
      open={open}
      onClose={onClose}
      fullWidth
      maxWidth="md"
      scroll="paper"
      slotProps={{
        paper: {
          sx: mergeSx(
            {
              borderRadius: 1.5,
              overflow: "hidden",
              maxWidth,
            },
            paperSx
          ),
        },
      }}
    >
      <DialogTitle sx={{ px: 2.5, py: 1.6, borderBottom: "1px solid", borderColor: "divider" }}>
        <Stack direction="row" sx={{ justifyContent: "space-between", alignItems: "center" }}>
          <Typography sx={mergeSx({ fontSize: "1.1rem", fontWeight: 700 }, titleSx)}>{title}</Typography>
          <IconButton onClick={onClose} edge="end" aria-label="Close">
            <CloseIcon />
          </IconButton>
        </Stack>
      </DialogTitle>
      <DialogContent
        sx={mergeSx(
          {
            px: 1.8,
            pt: 6.75,
            pb: 2.5,
            "&.MuiDialogContent-root": {
              paddingTop: "54px !important",
            },
          },
          contentSx
        )}
      >
        <Stack spacing={stackSpacing} sx={mergeSx({ maxWidth: 430, mx: "auto" }, stackSx)}>
          {children}
        </Stack>
      </DialogContent>
      {actions ? (
        <DialogActions sx={{ px: 2.5, py: 2, borderTop: "1px solid", borderColor: "divider" }}>
          {actions}
        </DialogActions>
      ) : null}
    </Dialog>
  );
}
