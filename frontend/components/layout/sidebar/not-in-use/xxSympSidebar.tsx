"use client";

import UnifiedSidebar from "./Unifiedsidebar";

export function SympSidebar({
  open = true,
  onToggle,
}: {
  open?: boolean;
  onToggle?: () => void;
}) {
  return (
    <UnifiedSidebar
      collapsed={!open}
      onToggleCollapse={onToggle}
    />
  );
}

export default SympSidebar;
