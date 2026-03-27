import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import Settings from "./Settings";

vi.mock("../contexts/AuthContext", () => ({
  useAuth: vi.fn(() => ({ user: { id: 1, username: "testuser" }, updateUser: vi.fn() })),
}));

vi.mock("../contexts/WSContext", () => ({
  useWS: vi.fn(),
  useWSSend: vi.fn(() => vi.fn()),
}));

vi.mock("../contexts/NotificationContext", () => ({
  useNotifications: vi.fn(() => ({
    unreadNotifications: 0,
    unreadMessages: 0,
    clearNotifications: vi.fn(),
    decrementNotifications: vi.fn(),
  })),
}));

function renderSettings() {
  return render(
    <BrowserRouter>
      <Settings />
    </BrowserRouter>,
  );
}

describe("Settings", () => {
  it("renders navigation links for all 6 sections", () => {
    renderSettings();

    expect(screen.getByRole("link", { name: "Account" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Profile" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Notifications" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Friend Groups" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Privacy" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Data" })).toBeInTheDocument();
  });

  it("renders Outlet for nested content", () => {
    renderSettings();
    // The nav is rendered and there is a content area for the Outlet
    const nav = screen.getByRole("navigation", { name: /settings navigation/i });
    expect(nav).toBeInTheDocument();
    // 6 links inside the nav
    const links = nav.querySelectorAll("a");
    expect(links).toHaveLength(6);
  });
});
