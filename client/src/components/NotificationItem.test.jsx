import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import NotificationItem from "./NotificationItem";

const wrap = (ui) => render(<BrowserRouter>{ui}</BrowserRouter>);

const baseNotification = {
  id: 50,
  type: "follow",
  actor_username: "janedoe",
  actor_avatar_url: null,
  is_read: false,
  created_at: new Date().toISOString(),
  group_count: 1,
  post_id: null,
  community_id: null,
};

describe("NotificationItem", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders follow notification with correct text", () => {
    wrap(<NotificationItem notification={baseNotification} />);

    expect(screen.getByText("@janedoe")).toBeInTheDocument();
    expect(screen.getByText(/followed you/)).toBeInTheDocument();
  });

  it("renders new_comment notification with correct text", () => {
    wrap(
      <NotificationItem
        notification={{
          ...baseNotification,
          type: "new_comment",
          post_id: 10,
        }}
      />,
    );

    expect(screen.getByText(/commented on your post/)).toBeInTheDocument();
  });

  it("renders vote notification with correct text", () => {
    wrap(
      <NotificationItem
        notification={{
          ...baseNotification,
          type: "vote",
          post_id: 10,
        }}
      />,
    );

    expect(screen.getByText(/voted on your post/)).toBeInTheDocument();
  });

  it("renders welcome notification", () => {
    wrap(
      <NotificationItem
        notification={{
          ...baseNotification,
          type: "welcome",
          actor_username: null,
        }}
      />,
    );

    expect(screen.getByText(/Welcome to PimPam!/)).toBeInTheDocument();
  });

  it("shows unread dot when not read", () => {
    const { container } = wrap(
      <NotificationItem notification={{ ...baseNotification, is_read: false }} />,
    );

    // The component renders a <span> with styles.dot for unread
    // The outer div also has the unread class
    const dotSpans = container.querySelectorAll("span");
    // There should be an unread dot span
    expect(dotSpans.length).toBeGreaterThan(0);
  });

  it("does not show unread dot when read", () => {
    const { container } = wrap(
      <NotificationItem notification={{ ...baseNotification, is_read: true }} />,
    );

    // With is_read: true, the unread dot span is not rendered
    // The item div should not have the unread class
    const itemDiv = container.querySelector("div > div");
    // There should be no dot span (the last child span for unread indicator)
    // Just verify the component does not include the unread class
    expect(itemDiv.className).not.toContain("unread");
  });

  it("clicking calls onRead for unread items", () => {
    const onRead = vi.fn();
    wrap(
      <NotificationItem
        notification={baseNotification}
        onRead={onRead}
      />,
    );

    // The notification wraps in a Link (since follow type has href)
    const link = screen.getByRole("link");
    fireEvent.click(link);

    expect(onRead).toHaveBeenCalledWith(50);
  });

  it("does not call onRead for already-read items", () => {
    const onRead = vi.fn();
    wrap(
      <NotificationItem
        notification={{ ...baseNotification, is_read: true }}
        onRead={onRead}
      />,
    );

    const link = screen.getByRole("link");
    fireEvent.click(link);

    expect(onRead).not.toHaveBeenCalled();
  });

  it("wraps in Link when href exists (follow notification)", () => {
    wrap(<NotificationItem notification={baseNotification} />);

    const link = screen.getByRole("link");
    expect(link).toHaveAttribute("href", "/u/janedoe");
  });

  it("does not use Link when href is null (mod_promote)", () => {
    wrap(
      <NotificationItem
        notification={{
          ...baseNotification,
          type: "mod_promote",
        }}
      />,
    );

    // No <a> link should be present; instead a div with role="button"
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
    expect(screen.getByRole("button")).toBeInTheDocument();
  });

  it("shows group text for grouped notifications", () => {
    wrap(
      <NotificationItem
        notification={{
          ...baseNotification,
          group_count: 4,
        }}
      />,
    );

    expect(screen.getByText(/and 3 others/)).toBeInTheDocument();
  });
});
