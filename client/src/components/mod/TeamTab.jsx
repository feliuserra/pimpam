import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import Avatar from "../ui/Avatar";
import Spinner from "../ui/Spinner";
import ModPromotion from "./ModPromotion";
import OwnershipTransfer from "./OwnershipTransfer";
import * as modApi from "../../api/moderation";
import styles from "./ModSection.module.css";

const ROLE_ORDER = { owner: 0, senior_mod: 1, moderator: 2 };
const ROLE_LABELS = { owner: "Owner", senior_mod: "Senior Mod", moderator: "Moderator" };

export default function TeamTab({ communityName }) {
  const [team, setTeam] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    modApi
      .listTeam(communityName)
      .then((r) => {
        const sorted = [...r.data].sort(
          (a, b) => (ROLE_ORDER[a.role] ?? 9) - (ROLE_ORDER[b.role] ?? 9)
        );
        setTeam(sorted);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [communityName]);

  if (loading) return <div className={styles.loader}><Spinner size={20} /></div>;

  return (
    <div>
      <h3 className={styles.heading}>Team ({team.length})</h3>
      {team.length === 0 ? (
        <p className={styles.empty}>No team members found.</p>
      ) : (
        <div className={styles.list}>
          {team.map((member) => (
            <div key={member.user_id} className={styles.card}>
              <div className={styles.cardRow}>
                <Link
                  to={`/u/${member.username}`}
                  style={{ display: "flex", alignItems: "center", gap: 8, textDecoration: "none", color: "inherit" }}
                >
                  <Avatar src={member.avatar_url} alt={`@${member.username}`} size={28} />
                  <strong>@{member.username}</strong>
                </Link>
                <span className={styles.badge} style={{
                  background: member.role === "owner"
                    ? "var(--color-accent, #6366f1)"
                    : member.role === "senior_mod"
                    ? "var(--color-warning, #d69e2e)"
                    : "var(--color-text-muted, #888)",
                }}>
                  {ROLE_LABELS[member.role] || member.role}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      <div style={{ marginTop: 24 }}>
        <h3 className={styles.heading}>Promote Member</h3>
        <ModPromotion communityName={communityName} />
      </div>

      <div style={{ marginTop: 24 }}>
        <h3 className={styles.heading}>Transfer Ownership</h3>
        <OwnershipTransfer communityName={communityName} />
      </div>
    </div>
  );
}
