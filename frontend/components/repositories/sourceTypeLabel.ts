export const sourceTypeLabel = (sourceType: string) => {
  const map: Record<string, string> = {
    sharedrive: "Shared Drive",
    sharepoint: "SharePoint",
    otcs: "OTCS",
  };

  return map[sourceType] || sourceType;
};
