import type { CSSProperties } from "react";

declare module "@mui/material/Stack" {
  interface StackOwnProps {
    gap?: number | string;
    alignItems?: CSSProperties["alignItems"];
    justifyContent?: CSSProperties["justifyContent"];
    flexWrap?: CSSProperties["flexWrap"];
    useFlexGap?: boolean;
  }
}

declare module "@mui/material/Typography" {
  interface TypographyOwnProps {
    fontWeight?: CSSProperties["fontWeight"];
  }
}

declare module "@mui/material/TextField" {
  interface BaseTextFieldProps {
    InputLabelProps?: {
      shrink?: boolean;
    };
  }
}
