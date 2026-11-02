// Null is a default selection, not a copied or uploaded product asset.
export function siteAssetUrl(site, role) {
  if (!["logo", "avatar"].includes(role)) throw new Error("Unknown site image role");
  const id = site[role];
  if (id == null) return "/assets/mark.svg";
  if (typeof id !== "string" || !/^[0-9a-f]{64}\.png$/.test(id)) throw new Error("Invalid site image reference");
  return `/site-assets/${encodeURIComponent(id)}`;
}
