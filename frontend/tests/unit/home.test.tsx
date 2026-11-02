/** Verify the scaffold states its purpose without inventing consumption data. */
import React from "react";
import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import Home from "../../src/app/page";

test("shows the public platform placeholder", () => {
  /** Render known static content and verify the accessible title and pending state. */
  render(<Home />);
  expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("ECS-EC");
  expect(screen.getByText("Las funcionalidades se incorporarán por módulo.")).toBeTruthy();
});
