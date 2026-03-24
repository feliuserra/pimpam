import Header from "../components/Header";

export default function Notifications() {
  return (
    <>
      <Header left={<span>Notifications</span>} />
      <div style={{ padding: "3rem 1rem", textAlign: "center", color: "var(--text-secondary)" }}>
        Notifications coming soon.
      </div>
    </>
  );
}
