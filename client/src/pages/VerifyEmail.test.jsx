import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";

let mockSearchParams = new URLSearchParams("token=valid-verify-token");

vi.mock("../api/auth", () => ({
  verifyEmail: vi.fn(),
}));

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useSearchParams: vi.fn(() => [mockSearchParams]),
  };
});

vi.mock("../components/ui/Spinner", () => ({
  default: () => <span role="status" aria-label="Loading">Loading...</span>,
}));

import { verifyEmail } from "../api/auth";
import VerifyEmail from "./VerifyEmail";
import { BrowserRouter } from "react-router-dom";

beforeEach(() => {
  vi.clearAllMocks();
  mockSearchParams = new URLSearchParams("token=valid-verify-token");
});

function renderVerifyEmail() {
  return render(
    <BrowserRouter>
      <VerifyEmail />
    </BrowserRouter>,
  );
}

describe("VerifyEmail", () => {
  it("shows spinner while verifying", () => {
    verifyEmail.mockReturnValue(new Promise(() => {}));
    renderVerifyEmail();

    expect(screen.getByRole("status", { name: "Loading" })).toBeInTheDocument();
  });

  it("shows success message after verification succeeds", async () => {
    verifyEmail.mockResolvedValue({});
    renderVerifyEmail();

    await waitFor(() => {
      expect(screen.getByText("Verified!")).toBeInTheDocument();
    });
    expect(screen.getByText("Email verified. You now have full access.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Sign in" })).toBeInTheDocument();
    expect(verifyEmail).toHaveBeenCalledWith("valid-verify-token");
  });

  it("shows error when verification fails", async () => {
    verifyEmail.mockRejectedValue({
      response: { data: { detail: "Token expired" } },
    });
    renderVerifyEmail();

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Token expired");
    });
    expect(screen.getByRole("link", { name: "Back to sign in" })).toBeInTheDocument();
  });

  it("shows error when no token is provided in URL", async () => {
    mockSearchParams = new URLSearchParams("");
    renderVerifyEmail();

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("No verification token provided.");
    });
    expect(verifyEmail).not.toHaveBeenCalled();
  });

  it("shows generic error when API fails without detail", async () => {
    verifyEmail.mockRejectedValue(new Error("Network Error"));
    renderVerifyEmail();

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Verification failed. The link may have expired.");
    });
  });
});
