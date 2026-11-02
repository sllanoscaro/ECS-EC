/** Same-origin consumption client; wire types are generated from001 OpenAPI, values stay textual. */
import { apiRequest, sessionActivityHeaders } from "./session";
import type { Catalog, Configuration, ConfigurationInput, DetailResult, CategoryStatus, Period } from "./consumption-types";
export type * from "./consumption-types";
export type CategoryId = CategoryStatus["id"];

export const consumptionApi = {
  /** Read seven categories and global initial period; never derive either from visible rows. */
  catalog(signal?: AbortSignal): Promise<Catalog> {
    return apiRequest<Catalog>("/consumption/catalog", { signal });
  },
  /** Fetch one full immutable detail response for both representations; preserve offset/microsecond text. */
  detail(category: CategoryId, period: Period, signal?: AbortSignal): Promise<DetailResult> {
    const query = new URLSearchParams({ start: period.start, end: period.end, timezone: period.timezone });
    return apiRequest<DetailResult>(`/consumption/categories/${category}/detail?${query}`, { signal, headers: sessionActivityHeaders("interactive") });
  },
  /** Read administrative configuration; the shared session adapter handles401/403 and no-store. */
  configuration(signal?: AbortSignal): Promise<Configuration> {
    return apiRequest<Configuration>("/consumption/configuration", { signal });
  },
  /** Submit only writable fields with current CSRF; derived revisions cannot leak through object spreading. */
  configure(input: ConfigurationInput): Promise<Configuration> {
    const { expected_revision, effective_from, timezone } = input;
    const categories = input.categories.map(({ category_id, has_meter, source_id, source_label }) =>
      ({ category_id, has_meter, source_id, source_label }));
    return apiRequest<Configuration>("/consumption/configuration", { method: "PUT",
      headers: sessionActivityHeaders("interactive"), body: JSON.stringify({ expected_revision, effective_from, timezone, categories }) });
  },
};
