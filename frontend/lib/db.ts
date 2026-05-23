import { neon } from "@neondatabase/serverless";

if (!process.env.DATABASE_URL) {
  throw new Error("DATABASE_URL environment variable is required");
}

const _sql = neon(process.env.DATABASE_URL);

/**
 * Execute a parameterized SQL query.
 * Uses neon's .query() method which accepts a plain string + params array.
 */
export async function query<T = Record<string, unknown>>(
  sqlString: string,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  params: any[] = []
): Promise<T[]> {
  // _sql.query() returns rows directly (not a { rows } wrapper) in default mode
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const result = await (_sql.query(sqlString, params) as any);
  // Support both { rows: [...] } (pg-style) and direct array responses
  return (Array.isArray(result) ? result : result.rows) as T[];
}

/** Alias used by API routes */
export const sql = query;

/** Valid US state/territory codes — filters out junk international codes from SAM.gov */
export const VALID_US_STATES: string[] = [
  "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA",
  "HI","ID","IL","IN","IA","KS","KY","LA","ME","MD",
  "MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ",
  "NM","NY","NC","ND","OH","OK","OR","PA","RI","SC",
  "SD","TN","TX","UT","VT","VA","WA","WV","WI","WY",
  "DC","PR","GU","VI","AS","MP",
];
