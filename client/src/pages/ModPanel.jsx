import { useState, useEffect } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import Header from "../components/Header";
import Spinner from "../components/ui/Spinner";
import QueueTab from "../components/mod/QueueTab";
import BanSection from "../components/mod/BanSection";
import LabelsTab from "../components/mod/LabelsTab";
import TeamTab from "../components/mod/TeamTab";
import * as communitiesApi from "../api/communities";
import styles from "./ModPanel.module.css";

const TABS = ["Queue", "Bans", "Labels", "Team"];

export default function ModPanel() {
  const { name } = useParams();
  const navigate = useNavigate();
  const [community, setCommunity] = useState(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState("Queue");

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

        {tab === "Queue" && <QueueTab communityName={name} />}
        {tab === "Bans" && <BanSection communityName={name} />}
        {tab === "Labels" && <LabelsTab communityName={name} />}
        {tab === "Team" && <TeamTab communityName={name} />}
      </div>
    </>
  );
}
