export type WorldId = "overdrive" | "hybrid" | "foundry" | "atlas" | "cathedral";

export type WorldInfo = {
  id: WorldId;
  heading: string;
  tabLabel: string;
};

export const WORLDS: WorldInfo[] = [
  { id: "overdrive", heading: "Atlas Foundry Overdrive", tabLabel: "Overdrive" },
  { id: "hybrid", heading: "Atlas Foundry", tabLabel: "Atlas Foundry" },
  { id: "foundry", heading: "The Foundry", tabLabel: "Foundry" },
  { id: "atlas", heading: "Signal Atlas", tabLabel: "Signal Atlas" },
  { id: "cathedral", heading: "Cathedral Engine", tabLabel: "Cathedral" },
];

export const DEFAULT_HEADING = "Atlas Foundry Overdrive";

export const PHONE_VIEWPORT = { width: 375, height: 812 };
