/**
 * US state abbreviation → full name mapping.
 * Used throughout the UI so non-US users can understand state labels.
 */

const STATE_NAMES: Record<string, string> = {
  AL: "Alabama",
  AK: "Alaska",
  AZ: "Arizona",
  AR: "Arkansas",
  CA: "California",
  CO: "Colorado",
  CT: "Connecticut",
  DE: "Delaware",
  FL: "Florida",
  GA: "Georgia",
  HI: "Hawaii",
  ID: "Idaho",
  IL: "Illinois",
  IN: "Indiana",
  IA: "Iowa",
  KS: "Kansas",
  KY: "Kentucky",
  LA: "Louisiana",
  ME: "Maine",
  MD: "Maryland",
  MA: "Massachusetts",
  MI: "Michigan",
  MN: "Minnesota",
  MS: "Mississippi",
  MO: "Missouri",
  MT: "Montana",
  NE: "Nebraska",
  NV: "Nevada",
  NH: "New Hampshire",
  NJ: "New Jersey",
  NM: "New Mexico",
  NY: "New York",
  NC: "North Carolina",
  ND: "North Dakota",
  OH: "Ohio",
  OK: "Oklahoma",
  OR: "Oregon",
  PA: "Pennsylvania",
  RI: "Rhode Island",
  SC: "South Carolina",
  SD: "South Dakota",
  TN: "Tennessee",
  TX: "Texas",
  UT: "Utah",
  VT: "Vermont",
  VA: "Virginia",
  WA: "Washington",
  WV: "West Virginia",
  WI: "Wisconsin",
  WY: "Wyoming",
  DC: "Washington D.C.",
  PR: "Puerto Rico",
  GU: "Guam",
  VI: "U.S. Virgin Islands",
  AS: "American Samoa",
  MP: "Northern Mariana Islands",
};

/**
 * Convert a US state abbreviation to its full name.
 * Returns the original value if no mapping is found (e.g. "Federal").
 */
export function fullStateName(code: string | null | undefined): string {
  if (!code) return "Not specified";
  const trimmed = code.trim().toUpperCase();
  return STATE_NAMES[trimmed] ?? code;
}

/**
 * Format as "Full Name (XX)" — e.g. "New York (NY)".
 * Use this for labels/charts where the abbreviation is also useful.
 */
export function stateLabel(code: string | null | undefined): string {
  if (!code) return "Not specified";
  const trimmed = code.trim().toUpperCase();
  const name = STATE_NAMES[trimmed];
  return name ? `${name} (${trimmed})` : code;
}

/**
 * Format for compact display — "New York" without the abbreviation.
 * Falls back to the code itself for unknown values.
 */
export function stateNameOnly(code: string | null | undefined): string {
  if (!code) return "Not specified";
  const trimmed = code.trim().toUpperCase();
  return STATE_NAMES[trimmed] ?? code;
}
