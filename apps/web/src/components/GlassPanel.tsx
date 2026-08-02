import { Box, type BoxProps } from "@mui/material";

import { cx, glassInset } from "../theme/tokens";

type Props = BoxProps & {
  hero?: boolean;
};

export function GlassPanel({ hero, sx, children, ...rest }: Props) {
  return (
    <Box
      {...rest}
      sx={{
        p: hero ? 3.5 : 3,
        borderRadius: hero ? 3.5 : 2.5,
        border: "1px solid",
        borderColor: hero ? cx.borderStrong : cx.border,
        bgcolor: hero ? "rgba(21,26,36,0.55)" : "rgba(16,20,29,0.75)",
        backdropFilter: "blur(18px)",
        boxShadow: glassInset,
        backgroundImage:
          "linear-gradient(145deg, rgba(255,255,255,0.045) 0%, transparent 42%)",
        ...sx,
      }}
    >
      {children}
    </Box>
  );
}
