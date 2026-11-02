/** Financial retries/conflicts preserve user choices and block even same-render duplicate submissions. */
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { useFinancialOperation } from "../../src/components/costs/useFinancialOperation";
import { Problem } from "../../src/lib/api/session";

afterEach(cleanup);

/** Present only the public operation hook contract, leaving its internal identity and concurrency state private. */
function Operation({ send }: { send: (key: string) => Promise<unknown> }) {
  const operation = useFinancialOperation();
  return <><button onClick={() => { void operation.run({ amount: "100" }, send, () => undefined); }}>Confirmar</button>
    {operation.error && <p role="alert">{operation.error}</p>}{operation.conflict && <p>Revisar estado actual</p>}</>;
}

it("retains the same explicit pair identity on validation error and retry", async () => {
  /** A failed confirmation never implicitly selects another pair or generates another idempotency key. */
  const send = vi.fn().mockRejectedValueOnce(new Problem(422, "invalid_input", "Revise los datos.")).mockResolvedValue({});
  render(<Operation send={send} />);
  fireEvent.click(screen.getByRole("button"));
  await screen.findByRole("alert");
  fireEvent.click(screen.getByRole("button"));
  await waitFor(() => { expect(send).toHaveBeenCalledTimes(2); });
  expect(send.mock.calls[0][0]).toBe(send.mock.calls[1][0]);
});

it("blocks immediate duplicate submissions and identifies a stale revision for explicit review", async () => {
  /** Two same-tick clicks share one operation; a conflict exposes review without silently replacing entered data. */
  const send = vi.fn().mockRejectedValue(new Problem(412, "revision_conflict", "synthetic"));
  render(<Operation send={send} />);
  fireEvent.click(screen.getByRole("button")); fireEvent.click(screen.getByRole("button"));
  await screen.findByText("Revisar estado actual");
  expect(send).toHaveBeenCalledTimes(1);
});
