import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

const mockNavigate = vi.fn();
const mockCreate = vi.fn();

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return { ...actual, useNavigate: vi.fn(() => mockNavigate) };
});

vi.mock("../api/communities", () => ({
  create: (...args) => mockCreate(...args),
}));

vi.mock("./ui/Modal", () => ({
  default: ({ open, onClose, title, children }) =>
    open ? (
      <div role="dialog" aria-label={title}>
        <button onClick={onClose} aria-label="Close">X</button>
        {children}
      </div>
    ) : null,
}));

import CreateCommunityModal from "./CreateCommunityModal";

describe("CreateCommunityModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("does not render when open is false", () => {
    render(<CreateCommunityModal open={false} onClose={vi.fn()} />);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("renders form with name input, description textarea, and submit button", () => {
    render(<CreateCommunityModal open={true} onClose={vi.fn()} />);

    expect(screen.getByRole("dialog")).toHaveAttribute("aria-label", "Create Community");
    expect(screen.getByPlaceholderText("e.g. photography")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("What is this community about?")).toBeInTheDocument();
    expect(screen.getByText("Create")).toBeInTheDocument();
    expect(screen.getByText("Letters, numbers, hyphens, underscores. 3-100 chars.")).toBeInTheDocument();
  });

  it("disables submit button when name is too short", () => {
    render(<CreateCommunityModal open={true} onClose={vi.fn()} />);

    const submitBtn = screen.getByText("Create");
    expect(submitBtn).toBeDisabled();

    // Type 2 characters — still too short
    fireEvent.change(screen.getByPlaceholderText("e.g. photography"), {
      target: { value: "ab" },
    });
    expect(submitBtn).toBeDisabled();
  });

  it("enables submit button when name has 3+ characters", () => {
    render(<CreateCommunityModal open={true} onClose={vi.fn()} />);

    fireEvent.change(screen.getByPlaceholderText("e.g. photography"), {
      target: { value: "art" },
    });

    expect(screen.getByText("Create")).not.toBeDisabled();
  });

  it("submits community and navigates on success", async () => {
    const onClose = vi.fn();
    mockCreate.mockResolvedValue({
      data: { id: 10, name: "photography" },
    });

    render(<CreateCommunityModal open={true} onClose={onClose} />);

    fireEvent.change(screen.getByPlaceholderText("e.g. photography"), {
      target: { value: "photography" },
    });
    fireEvent.change(screen.getByPlaceholderText("What is this community about?"), {
      target: { value: "Share your photos" },
    });

    fireEvent.submit(screen.getByPlaceholderText("e.g. photography").closest("form"));

    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledWith({
        name: "photography",
        description: "Share your photos",
      });
      expect(onClose).toHaveBeenCalled();
      expect(mockNavigate).toHaveBeenCalledWith("/c/photography");
    });
  });

  it("shows error message on API failure", async () => {
    mockCreate.mockRejectedValue({
      response: { data: { detail: "Name already taken" } },
    });

    render(<CreateCommunityModal open={true} onClose={vi.fn()} />);

    fireEvent.change(screen.getByPlaceholderText("e.g. photography"), {
      target: { value: "photography" },
    });

    fireEvent.submit(screen.getByPlaceholderText("e.g. photography").closest("form"));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Name already taken");
    });
  });

  it("shows generic error when no detail in response", async () => {
    mockCreate.mockRejectedValue(new Error("network error"));

    render(<CreateCommunityModal open={true} onClose={vi.fn()} />);

    fireEvent.change(screen.getByPlaceholderText("e.g. photography"), {
      target: { value: "newcommunity" },
    });

    fireEvent.submit(screen.getByPlaceholderText("e.g. photography").closest("form"));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Failed to create community");
    });
  });
});
