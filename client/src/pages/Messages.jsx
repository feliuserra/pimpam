import Header from "../components/Header";

export default function Messages() {
  return (
    <>
      <Header left={<span>Messages</span>} />
      <div style={{ padding: "3rem 1rem", textAlign: "center", color: "var(--text-secondary)" }}>
        Messages coming soon.
      </div>
    </>
  );
}
