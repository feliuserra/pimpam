import { useState, useEffect } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import Header from "../components/Header";
import Spinner from "../components/ui/Spinner";
import RemovedContent from "../components/mod/RemovedContent";
import BanSection from "../components/mod/BanSection";
import ModPromotion from "../components/mod/ModPromotion";
import OwnershipTransfer from "../components/mod/OwnershipTransfer";
import * as communitiesApi from "../api/communities";
import styles from "./ModPanel.module.css";

const TABS = ["Removed", "Bans", "Moderators", "Transfer"];

export default function ModPanel() {
  const { name } = useParams();
  const navigate = useNavigate();
  const [community, setCommunity] = useState(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState("Removed");

  useEffect(() => {
    communitiesApi
      .get(name)
      .then((res) => setCommunity(res.data))
      .catch(() => navigate(`/c/${name}`, { replace: true }))
      .finally(() => setLoading(false));
  }, [name, navigate]);

  if (loading) {
    return (
      <>
        <Header left={<span>Mod: c/{name}</span>} />
        <div className={styles.loader}><Spinner size={28} /></div>
      </>
    );
  }

  if (!community) return null;

  return (
    <>
      <Header
        left={
          <div className={styles.headerLeft}>
            <Link to={`/c/${name}`} className={styles.back}>← c/{name}</Link>
            <span className={styles.headerTitle}>Mod Panel</span>
          </div>
        }
      />

      <div className={styles.container}>
        <nav className={styles.tabs} aria-label="Moderation tabs">
          {TABS.map((t) => (
            <button
              key={t}
              className={`${styles.tab} ${tab === t ? styles.activeTab : ""}`}
              onClick={() => setTab(t)}
              aria-selected={tab === t}
              role="tab"
            >
              {t}
            </button>
          ))}
        </nav>

        {tab === "Removed" && <RemovedContent communityName={name} />}
        {tab === "Bans" && <BanSection communityName={name} />}
        {tab === "Moderators" && <ModPromotion communityName={name} />}
        {tab === "Transfer" && <OwnershipTransfer communityName={name} />}
      </div>
    </>
  );
}
