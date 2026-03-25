import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

vi.mock("../../api/moderation", () => ({
  listBans: vi.fn(),
  listAppeals: vi.fn(),
  proposeBan: vi.fn(),
  voteAppeal: vi.fn(),
}));

vi.mock("../ui/Spinner", () => ({
  default: () => <span role="status">Loading</span>,
}));

vi.mock("../ui/RelativeTime", () => ({
  default: ({ date }) => <time>{date}</time>,
}));

vi.mock("./ModSection.module.css", () => ({
  default: {
    loader: "loader",
    sectionHeader: "sectionHeader",
    heading: "heading",
    subheading: "subheading",
    btn: "btn",
    smallBtn: "smallBtn",
    dangerBtn: "dangerBtn",
    list: "list",
    card: "card",
    cardRow: "cardRow",
    cardText: "cardText",
    cardMeta: "cardMeta",
    badge: "badge",
    empty: "empty",
    form: "form",
    input: "input",
    textarea: "textarea",
    checkLabel: "checkLabel",
    error: "error",
  },
}));

import BanSection from "./BanSection";
import * as modApi from "../../api/moderation";

describe("BanSection", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows spinner while loading", () => {
    modApi.listBans.mockReturnValue(new Promise(() => {}));
    modApi.listAppeals.mockReturnValue(new Promise(() => {}));

    render(<BanSection communityName="tech" />);
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("renders empty state when no bans or appeals", async () => {
    modApi.listBans.mockResolvedValue({ data: [] });
    modApi.listAppeals.mockResolvedValue({ data: [] });

    render(<BanSection communityName="tech" />);

    await waitFor(() => {
      expect(screen.getByText("No active bans.")).toBeInTheDocument();
    });
    expect(screen.getByText("No pending appeals.")).toBeInTheDocument();
  });

  it("renders bans list with details", async () => {
    modApi.listBans.mockResolvedValue({
      data: [
        {
          id: 1,
          user_id: 42,
          reason: "Spam posts",
          coc_violation: "spam",
          is_permanent: true,
          created_at: "2025-01-01T00:00:00Z",
        },
      ],
    });
    modApi.listAppeals.mockResolvedValue({ data: [] });

    render(<BanSection communityName="tech" />);

    await waitFor(() => {
      expect(screen.getByText("User #42")).toBeInTheDocument();
    });
    expect(screen.getByText("Permanent")).toBeInTheDocument();
    expect(screen.getByText("Spam posts")).toBeInTheDocument();
    expect(screen.getByText("Violation: spam")).toBeInTheDocument();
    expect(screen.getByText("Active Bans (1)")).toBeInTheDocument();
  });

  it("renders temporary ban badge", async () => {
    modApi.listBans.mockResolvedValue({
      data: [
        {
          id: 1,
          user_id: 5,
          reason: "Minor offense",
          coc_violation: "other",
          is_permanent: false,
          created_at: "2025-01-01T00:00:00Z",
        },
      ],
    });
    modApi.listAppeals.mockResolvedValue({ data: [] });

    render(<BanSection communityName="tech" />);

    await waitFor(() => {
      expect(screen.getByText("Temporary")).toBeInTheDocument();
    });
  });

  it("renders appeals with vote button", async () => {
    modApi.listBans.mockResolvedValue({ data: [] });
    modApi.listAppeals.mockResolvedValue({
      data: [
        {
          id: 10,
          reason: "I was wrongfully banned",
          vote_count: 3,
          required_votes: 5,
          created_at: "2025-06-01T00:00:00Z",
        },
      ],
    });

    render(<BanSection communityName="tech" />);

    await waitFor(() => {
      expect(screen.getByText("I was wrongfully banned")).toBeInTheDocument();
    });
    expect(screen.getByText("Votes: 3/5")).toBeInTheDocument();
    expect(screen.getByText("Vote to Accept")).toBeInTheDocument();
    expect(screen.getByText("Pending Appeals (1)")).toBeInTheDocument();
  });

  it("vote appeal button calls API and refreshes", async () => {
    modApi.listBans.mockResolvedValue({ data: [] });
    modApi.listAppeals.mockResolvedValue({
      data: [
        { id: 10, reason: "Appeal", vote_count: 1, required_votes: 5, created_at: "2025-01-01T00:00:00Z" },
      ],
    });
    modApi.voteAppeal.mockResolvedValue({});

    render(<BanSection communityName="tech" />);

    await waitFor(() => {
      expect(screen.getByText("Vote to Accept")).toBeInTheDocument();
    });

    // After clicking, voteAppeal is called then listAppeals again
    modApi.listAppeals.mockResolvedValue({ data: [] });

    fireEvent.click(screen.getByText("Vote to Accept"));

    await waitFor(() => {
      expect(modApi.voteAppeal).toHaveBeenCalledWith("tech", 10);
    });
  });

  it("toggles propose ban form on button click", async () => {
    modApi.listBans.mockResolvedValue({ data: [] });
    modApi.listAppeals.mockResolvedValue({ data: [] });

    render(<BanSection communityName="tech" />);

    await waitFor(() => {
      expect(screen.getByText("Propose Ban")).toBeInTheDocument();
    });

    // No form initially
    expect(screen.queryByPlaceholderText("Username to ban")).not.toBeInTheDocument();

    fireEvent.click(screen.getByText("Propose Ban"));

    // Form appears
    expect(screen.getByPlaceholderText("Username to ban")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Reason for ban")).toBeInTheDocument();

    // Button text changes
    expect(screen.getByText("Cancel")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Cancel"));
    expect(screen.queryByPlaceholderText("Username to ban")).not.toBeInTheDocument();
  });

  it("submits propose ban form successfully", async () => {
    modApi.listBans.mockResolvedValue({ data: [] });
    modApi.listAppeals.mockResolvedValue({ data: [] });
    modApi.proposeBan.mockResolvedValue({});

    render(<BanSection communityName="tech" />);

    await waitFor(() => {
      expect(screen.getByText("Propose Ban")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Propose Ban"));

    fireEvent.change(screen.getByPlaceholderText("Username to ban"), {
      target: { value: "spammer" },
    });
    fireEvent.change(screen.getByPlaceholderText("Reason for ban"), {
      target: { value: "Spamming community" },
    });

    // After form submit, listBans is re-fetched
    modApi.listBans.mockResolvedValue({ data: [] });

    // Submit the form - there's a "Propose Ban" submit button inside the form
    const submitButtons = screen.getAllByRole("button");
    const formSubmit = submitButtons.find(
      (btn) => btn.getAttribute("type") === "submit",
    );
    fireEvent.click(formSubmit);

    await waitFor(() => {
      expect(modApi.proposeBan).toHaveBeenCalledWith("tech", {
        target_username: "spammer",
        reason: "Spamming community",
        coc_violation: "other",
        is_permanent: true,
      });
    });
  });

  it("shows error when propose ban fails", async () => {
    modApi.listBans.mockResolvedValue({ data: [] });
    modApi.listAppeals.mockResolvedValue({ data: [] });
    modApi.proposeBan.mockRejectedValue({
      response: { data: { detail: "User not found" } },
    });

    render(<BanSection communityName="tech" />);

    await waitFor(() => {
      expect(screen.getByText("Propose Ban")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Propose Ban"));

    fireEvent.change(screen.getByPlaceholderText("Username to ban"), {
      target: { value: "nobody" },
    });
    fireEvent.change(screen.getByPlaceholderText("Reason for ban"), {
      target: { value: "Test" },
    });

    const submitButtons = screen.getAllByRole("button");
    const formSubmit = submitButtons.find(
      (btn) => btn.getAttribute("type") === "submit",
    );
    fireEvent.click(formSubmit);

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("User not found");
    });
  });
});
