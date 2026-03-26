import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

const mockAddToast = vi.fn();

vi.mock("../contexts/ToastContext", () => ({
  useToast: vi.fn(() => ({ addToast: mockAddToast })),
}));

vi.mock("../api/auth", () => ({
  resendVerification: vi.fn(),
}));

vi.mock("./VerificationBanner.module.css", () => ({ default: {} }));

import VerificationBanner from "./VerificationBanner";
import * as authApi from "../api/auth";

describe("VerificationBanner", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders with alert role and verification message", () => {
    render(<VerificationBanner />);

    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText("Please verify your email to get full access.")).toBeInTheDocument();
  });

  it("renders a resend button", () => {
    render(<VerificationBanner />);

    expect(screen.getByText("Resend email")).toBeInTheDocument();
  });

  it("calls resendVerification and shows success toast on click", async () => {
    authApi.resendVerification.mockResolvedValue({});

    render(<VerificationBanner />);

    fireEvent.click(screen.getByText("Resend email"));

    // Button shows sending state
    expect(screen.getByText("Sending\u2026")).toBeInTheDocument();

    await waitFor(() => {
      expect(authApi.resendVerification).toHaveBeenCalledTimes(1);
      expect(mockAddToast).toHaveBeenCalledWith("Verification email sent!", "success");
    });

    // Button returns to normal state
    expect(screen.getByText("Resend email")).toBeInTheDocument();
  });

  it("shows error toast when resend fails", async () => {
    authApi.resendVerification.mockRejectedValue(new Error("Network error"));

    render(<VerificationBanner />);

    fireEvent.click(screen.getByText("Resend email"));

    await waitFor(() => {
      expect(mockAddToast).toHaveBeenCalledWith(
        "Could not send email. Try again later.",
        "error",
      );
    });
  });

  it("disables button while sending", async () => {
    let resolveResend;
    authApi.resendVerification.mockReturnValue(
      new Promise((resolve) => { resolveResend = resolve; }),
    );

    render(<VerificationBanner />);

    fireEvent.click(screen.getByText("Resend email"));

    const button = screen.getByText("Sending\u2026");
    expect(button).toBeDisabled();

    resolveResend({});

    await waitFor(() => {
      expect(screen.getByText("Resend email")).not.toBeDisabled();
    });
  });
});
