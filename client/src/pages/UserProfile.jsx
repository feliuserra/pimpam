import { useParams } from "react-router-dom";
import Header from "../components/Header";

export default function UserProfile() {
  const { username } = useParams();
  return (
    <>
      <Header left={<span>@{username}</span>} />
      <div style={{ padding: "3rem 1rem", textAlign: "center", color: "var(--text-secondary)" }}>
        Profile coming soon.
      </div>
    </>
  );
}
