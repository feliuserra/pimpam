import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return { ...actual };
});

import VerifyEmailSent from "./VerifyEmailSent";
import { BrowserRouter } from "react-router-dom";

function renderVerifyEmailSent() {
  return render(
    <BrowserRouter>
      <VerifyEmailSent />
    </BrowserRouter>,
  );
}

describe("VerifyEmailSent", () => {
  it("renders the confirmation page with all elements", () => {
    renderVerifyEmailSent();

    expect(screen.getByText("PimPam")).toBeInTheDocument();
    expect(screen.getByText("Check your email")).toBeInTheDocument();
    expect(
      screen.getByText("We sent a verification link to the email address you provided. Click the link to activate your account."),
    ).toBeInTheDocument();
  });

  it("provides a link to sign in for resending verification", () => {
    renderVerifyEmailSent();

    const link = screen.getByRole("link", { name: "sign in" });
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute("href", "/login");
  });

  it("mentions checking spam folder", () => {
    renderVerifyEmailSent();

    expect(screen.getByText(/Check your spam folder/)).toBeInTheDocument();
  });
});
