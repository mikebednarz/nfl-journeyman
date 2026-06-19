export interface Franchise {
  abbr: string;
  display: string;
}

export interface Player {
  id: string;
  full_name: string;
  initials: string;
  position: string;
  college: string;
  franchises: Franchise[];
  first_season: number;
  last_season: number;
  franchise_count: number;
  difficulty?: string;
}

export interface AutocompleteEntry {
  id: string;
  name: string;
  position: string;
  team: string;
  alias?: string;
}

export type HintType = "position" | "years" | "college" | "initials";

export const HINT_ORDER: { type: HintType; label: string }[] = [
  { type: "position", label: "Position" },
  { type: "years", label: "Years Active" },
  { type: "college", label: "College" },
  { type: "initials", label: "Initials" },
];
