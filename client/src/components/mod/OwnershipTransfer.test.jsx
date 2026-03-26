import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

vi.mock("../../api/moderation", () => ({
  proposeTransfer: vi.fn(),
}));

vi.mock("./ModSection.module.css", () => ({
  default: {
    heading: "heading",
    hint: "hint",
    form: "form",
    input: "input",
    dangerBtn: "dangerBtn",
    error: "error",
    success: "success",
  },
}));

import OwnershipTransfer from "./OwnershipTransfer";
import * as modApi from "../../api/moderation";

describe("OwnershipTransfer", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.confirm = vi.fn(() => true);
  });

  it("renders heading and description", () => {
    render(<OwnershipTransfer communityName="tech" />);
    expect(screen.getByText("Ownership Transfer")).toBeInTheDocument();
    expect(
      screen.getByText(/Transfer community ownership to another senior moderator/),
    ).toBeInTheDocument();
  });

  it("renders form with username input", () => {
    render(<OwnershipTransfer communityName="tech" />);
    expect(screen.getByPlaceholderText("Recipient username")).toBeInTheDocument();
  });

  it("submit button is disabled when username is empty", () => {
    render(<OwnershipTransfer communityName="tech" />);
    const btn = screen.getByRole("button", { name: "Propose Transfer" });
    expect(btn).toBeDisabled();
  });

  it("submit button is enabled when username is filled", () => {
    render(<OwnershipTransfer communityName="tech" />);
    fireEvent.change(screen.getByPlaceholderText("Recipient username"), {
      target: { value: "alice" },
    });
    const btn = screen.getByRole("button", { name: "Propose Transfer" });
    expect(btn).not.toBeDisabled();
  });

  it("shows confirmation dialog before submitting", async () => {
    modApi.proposeTransfer.mockResolvedValue({});

    render(<OwnershipTransfer communityName="tech" />);

    fireEvent.change(screen.getByPlaceholderText("Recipient username"), {
      target: { value: "alice" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Propose Transfer" }));

    expect(window.confirm).toHaveBeenCalledWith(
      "Transfer ownership of c/tech to @alice?",
    );
  });

  it("does not submit if confirmation is cancelled", async () => {
    window.confirm = vi.fn(() => false);

    render(<OwnershipTransfer communityName="tech" />);

    fireEvent.change(screen.getByPlaceholderText("Recipient username"), {
      target: { value: "alice" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Propose Transfer" }));

    expect(modApi.proposeTransfer).not.toHaveBeenCalled();
  });

  it("submits transfer proposal on confirmation", async () => {
    modApi.proposeTransfer.mockResolvedValue({});

    render(<OwnershipTransfer communityName="tech" />);

    fireEvent.change(screen.getByPlaceholderText("Recipient username"), {
      target: { value: "alice" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Propose Transfer" }));

    await waitFor(() => {
      expect(modApi.proposeTransfer).toHaveBeenCalledWith("tech", {
        recipient_username: "alice",
      });
    });
  });

  it("shows success message after successful transfer", async () => {
    modApi.proposeTransfer.mockResolvedValue({});

    render(<OwnershipTransfer communityName="tech" />);

    fireEvent.change(screen.getByPlaceholderText("Recipient username"), {
      target: { value: "alice" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Propose Transfer" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        "Transfer proposed. Waiting for recipient to accept.",
      );
    });

    // Username should be cleared
    expect(screen.getByPlaceholderText("Recipient username")).toHaveValue("");
  });

  it("shows error message on failure", async () => {
    modApi.proposeTransfer.mockRejectedValue({
      response: { data: { detail: "Recipient is not a senior mod" } },
    });

    render(<OwnershipTransfer communityName="tech" />);

    fireEvent.change(screen.getByPlaceholderText("Recipient username"), {
      target: { value: "newbie" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Propose Transfer" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        "Recipient is not a senior mod",
      );
    });
  });

  it("shows fallback error when no detail in response", async () => {
    modApi.proposeTransfer.mockRejectedValue(new Error("Network error"));

    render(<OwnershipTransfer communityName="tech" />);

    fireEvent.change(screen.getByPlaceholderText("Recipient username"), {
      target: { value: "alice" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Propose Transfer" }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        "Failed to propose transfer",
      );
    });
  });

  it("shows Submitting... text while busy", async () => {
    modApi.proposeTransfer.mockReturnValue(new Promise(() => {}));

    render(<OwnershipTransfer communityName="tech" />);

    fireEvent.change(screen.getByPlaceholderText("Recipient username"), {
      target: { value: "alice" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Propose Transfer" }));

    await waitFor(() => {
      expect(screen.getByText("Submitting...")).toBeInTheDocument();
    });
  });
});
