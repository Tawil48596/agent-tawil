export interface ToolDetail {
  name: string; description: string; toolset: string; version: string;
  author: string; tags: string[]; is_dangerous: boolean;
  requires_env: string[]; requires_packages: string[]; installed: boolean;
  genui_component?: string;
}

export interface MarketplaceEntry {
  name: string; description: string; version: string; author: string;
  tags: string[]; downloads: number; rating: number; is_dangerous: boolean;
}
