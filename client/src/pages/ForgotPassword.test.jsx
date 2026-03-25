import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

vi.mock("../api/auth", () => ({
  requestPasswordReset: vi.fn(),
}));

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return { ...actual };
});

import { requestPasswordReset } from "../api/auth";
import ForgotPassword from "./ForgotPassword";
import { BrowserRouter } from "react-router-dom";

beforeEach(() => {
  vi.clearAllMocks();
});

function renderForgotPassword() {
  return render(
    <BrowserRouter>
      <ForgotPassword />
    </BrowserRouter>,
  );
}

describe("ForgotPassword", () => {
  it("renders the forgot password form", () => {
    renderForgotPassword();

    expect(screen.getByText("PimPam")).toBeInTheDocument();
    expect(screen.getByText("Enter your email and we'll send a reset link.")).toBeInTheDocument();
    expect(screen.getByLabelText("Email")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Send reset link" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Back to sign in" })).toBeInTheDocument();
  });

  it("shows confirmation message after successful submission", async () => {
    requestPasswordReset.mockResolvedValue({});
    renderForgotPassword();

    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "user@example.com" } });
    fireEvent.click(screen.getByRole("button", { name: "Send reset link" }));

    await waitFor(() => {
      expect(screen.getByText("Check your email")).toBeInTheDocument();
    });
    expect(screen.getByText(/If an account exists with that email/)).toBeInTheDocument();
    expect(screen.getByText(/It expires in 15 minutes/)).toBeInTheDocument();
    expect(requestPasswordReset).toHaveBeenCalledWith("user@example.com");
  });

  it("shows confirmation even when API fails (prevents email enumeration)", async () => {
    requestPasswordReset.mockRejectedValue(new Error("Not found"));
    renderForgotPassword();

    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "nonexistent@example.com" } });
    fireEvent.click(screen.getByRole("button", { name: "Send reset link" }));

    await waitFor(() => {
      expect(screen.getByText("Check your email")).toBeInTheDocument();
    });
  });

  it("shows loading state during submission", async () => {
    requestPasswordReset.mockReturnValue(new Promise(() => {}));
    renderForgotPassword();

    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "user@example.com" } });
    fireEvent.click(screen.getByRole("button", { name: "Send reset link" }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Sending\u2026" })).toBeDisabled();
    });
  });

  it("shows 'Back to sign in' link after submission", async () => {
    requestPasswordReset.mockResolvedValue({});
    renderForgotPassword();

    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "user@example.com" } });
    fireEvent.click(screen.getByRole("button", { name: "Send reset link" }));

    await waitFor(() => {
      expect(screen.getByText("Check your email")).toBeInTheDocument();
    });
    expect(screen.getByRole("link", { name: "Back to sign in" })).toBeInTheDocument();
  });
});
