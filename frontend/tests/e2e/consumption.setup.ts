/** Protected001 E2E fixture inputs; database provisioning uses scripts/seed_consumption_reference.py. */
import { readFileSync, statSync } from "node:fs";

/** Require an explicit synthetic mode and private password file, never default to real installation credentials. */
export function consumptionFixture() {
  const path = process.env.IDENTITY_E2E_PASSWORD_FILE;
  const mode = process.env.CONSUMPTION_E2E_MODE;
  if (!path || !["physical", "calculated"].includes(mode ?? "") || (statSync(path).mode & 0o077)) {
    throw new Error("Consumption E2E requires an explicit mode and a protected synthetic fixture file.");
  }
  return { password: readFileSync(path, "utf8").replace(/\n$/, ""), mode };
}
