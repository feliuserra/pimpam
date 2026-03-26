import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

const mockLogin = vi.fn();
const mockNavigate = vi.fn();
let mockLocationState = { username: "alice", password: "pass123" };

vi.mock("../contexts/AuthContext", () => ({
  useAuth: vi.fn(() => ({ login: mockLogin })),
}));

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: vi.fn(() => mockNavigate),
    useLocation: vi.fn(() => ({ state: mockLocationState })),
    Navigate: ({ to }) => <div data-testid="navigate-redirect">Redirecting to {to}</div>,
  };
});

import LoginTotp from "./LoginTotp";

beforeEach(() => {
  vi.clearAllMocks();
  mockLocationState = { username: "alice", password: "pass123" };
});

describe("LoginTotp", () => {
  it("renders the TOTP form with all elements", () => {
    render(<LoginTotp />);

    expect(screen.getByText("PimPam")).toBeInTheDocument();
    expect(screen.getByText("Two-factor authentication")).toBeInTheDocument();
    expect(screen.getByText("Enter the 6-digit code from your authenticator app.")).toBeInTheDocument();
    expect(screen.getByLabelText("Verification code")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Verify" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Back to sign in" })).toBeInTheDocument();
  });

  it("redirects to login when location state is missing", () => {
    mockLocationState = {};
    render(<LoginTotp />);

    expect(screen.getByTestId("navigate-redirect")).toHaveTextContent("Redirecting to /login");
  });

  it("enables submit button only when 6 digits are entered", () => {
    render(<LoginTotp />);

    const input = screen.getByLabelText("Verification code");
    const button = screen.getByRole("button", { name: "Verify" });

    expect(button).toBeDisabled();

    fireEvent.change(input, { target: { value: "12345" } });
    expect(button).toBeDisabled();

    fireEvent.change(input, { target: { value: "123456" } });
    expect(button).not.toBeDisabled();
  });

  it("strips non-digit characters from input", () => {
    render(<LoginTotp />);

    const input = screen.getByLabelText("Verification code");
    fireEvent.change(input, { target: { value: "12ab34" } });

    expect(input.value).toBe("1234");
  });

  it("calls login with TOTP code and navigates home on success", async () => {
    mockLogin.mockResolvedValue({});
    render(<LoginTotp />);

    fireEvent.change(screen.getByLabelText("Verification code"), { target: { value: "654321" } });
    fireEvent.click(screen.getByRole("button", { name: "Verify" }));

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith("alice", "pass123", "654321");
    });
    expect(mockNavigate).toHaveBeenCalledWith("/");
  });

  it("displays error on invalid TOTP code", async () => {
    mockLogin.mockRejectedValue({
      response: { data: { detail: "Invalid TOTP code" } },
    });
    render(<LoginTotp />);

    fireEvent.change(screen.getByLabelText("Verification code"), { target: { value: "000000" } });
    fireEvent.click(screen.getByRole("button", { name: "Verify" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Invalid TOTP code");
    });
  });
});
