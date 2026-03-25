import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

let mockSearchParams = new URLSearchParams("token=valid-reset-token");

vi.mock("../api/auth", () => ({
  confirmPasswordReset: vi.fn(),
}));

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useSearchParams: vi.fn(() => [mockSearchParams]),
  };
});

import { confirmPasswordReset } from "../api/auth";
import ResetPassword from "./ResetPassword";
import { BrowserRouter } from "react-router-dom";

beforeEach(() => {
  vi.clearAllMocks();
  mockSearchParams = new URLSearchParams("token=valid-reset-token");
});

function renderResetPassword() {
  return render(
    <BrowserRouter>
      <ResetPassword />
    </BrowserRouter>,
  );
}

describe("ResetPassword", () => {
  it("renders the reset password form when token is present", () => {
    renderResetPassword();

    expect(screen.getByText("PimPam")).toBeInTheDocument();
    expect(screen.getByText("Choose a new password.")).toBeInTheDocument();
    expect(screen.getByLabelText("New password")).toBeInTheDocument();
    expect(screen.getByLabelText("Confirm password")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Set new password" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Back to sign in" })).toBeInTheDocument();
  });

  it("shows error when token is missing", () => {
    mockSearchParams = new URLSearchParams("");
    renderResetPassword();

    expect(screen.getByRole("alert")).toHaveTextContent("Missing reset token");
    expect(screen.getByRole("link", { name: "Request reset" })).toBeInTheDocument();
  });

  it("shows error when passwords do not match", async () => {
    renderResetPassword();

    fireEvent.change(screen.getByLabelText("New password"), { target: { value: "newpass123" } });
    fireEvent.change(screen.getByLabelText("Confirm password"), { target: { value: "different" } });
    fireEvent.click(screen.getByRole("button", { name: "Set new password" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Passwords do not match");
    });
    expect(confirmPasswordReset).not.toHaveBeenCalled();
  });

  it("shows success message after password is reset", async () => {
    confirmPasswordReset.mockResolvedValue({});
    renderResetPassword();

    fireEvent.change(screen.getByLabelText("New password"), { target: { value: "newpass123" } });
    fireEvent.change(screen.getByLabelText("Confirm password"), { target: { value: "newpass123" } });
    fireEvent.click(screen.getByRole("button", { name: "Set new password" }));

    await waitFor(() => {
      expect(screen.getByText("Password updated")).toBeInTheDocument();
    });
    expect(screen.getByText("You can now sign in with your new password.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Sign in" })).toBeInTheDocument();
    expect(confirmPasswordReset).toHaveBeenCalledWith("valid-reset-token", "newpass123");
  });

  it("shows error when reset API call fails", async () => {
    confirmPasswordReset.mockRejectedValue({
      response: { data: { detail: "Token expired" } },
    });
    renderResetPassword();

    fireEvent.change(screen.getByLabelText("New password"), { target: { value: "newpass123" } });
    fireEvent.change(screen.getByLabelText("Confirm password"), { target: { value: "newpass123" } });
    fireEvent.click(screen.getByRole("button", { name: "Set new password" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Token expired");
    });
  });

  it("shows generic error when API fails without detail", async () => {
    confirmPasswordReset.mockRejectedValue(new Error("Network Error"));
    renderResetPassword();

    fireEvent.change(screen.getByLabelText("New password"), { target: { value: "newpass123" } });
    fireEvent.change(screen.getByLabelText("Confirm password"), { target: { value: "newpass123" } });
    fireEvent.click(screen.getByRole("button", { name: "Set new password" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Reset failed. The link may have expired.");
    });
  });
});
