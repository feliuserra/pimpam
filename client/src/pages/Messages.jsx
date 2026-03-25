import { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import Header from "../components/Header";
import Avatar from "../components/ui/Avatar";
import Spinner from "../components/ui/Spinner";
import RelativeTime from "../components/ui/RelativeTime";
import NewMessageModal from "../components/NewMessageModal";
import PlusIcon from "../components/ui/icons/PlusIcon";
import { useWS } from "../contexts/WSContext";
import * as messagesApi from "../api/messages";
import styles from "./Messages.module.css";

export default function Messages() {
  const [conversations, setConversations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [composeOpen, setComposeOpen] = useState(false);

  const loadInbox = useCallback(async () => {
    try {
      const res = await messagesApi.getInbox();
      setConversations(res.data);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadInbox(); }, [loadInbox]);

  // Bump conversation to top on new message
  useWS(
    "new_message",
    useCallback((data) => {
      setConversations((prev) => {
        const idx = prev.findIndex((c) => c.other_user_id === data.sender_id);
        if (idx >= 0) {
          const updated = { ...prev[idx], unread_count: prev[idx].unread_count + 1, last_message_at: new Date().toISOString() };
          return [updated, ...prev.filter((_, i) => i !== idx)];
        }
        // New conversation — reload
        loadInbox();
        return prev;
      });
    }, [loadInbox]),
  );

  return (
    <>
      <Header
        left={<span>Messages</span>}
        right={
          <button className={styles.composeBtn} onClick={() => setComposeOpen(true)} aria-label="New message">
            <PlusIcon size={20} />
          </button>
        }
      />

      <div className={styles.container}>
        {loading ? (
          <div className={styles.loader}><Spinner size={24} /></div>
        ) : conversations.length === 0 ? (
          <div className={styles.empty}>
            <p>No messages yet.</p>
            <button className={styles.startBtn} onClick={() => setComposeOpen(true)}>
              Start a conversation
            </button>
          </div>
        ) : (
          <div className={styles.list}>
            {conversations.map((c) => (
              <Link
                key={c.other_user_id}
                to={`/messages/${c.other_user_id}`}
                className={styles.conversation}
              >
                <Avatar src={c.other_avatar_url} alt={`@${c.other_username}`} size={44} />
                <div className={styles.convBody}>
                  <div className={styles.convHeader}>
                    <span className={styles.convName}>@{c.other_username}</span>
                    <RelativeTime date={c.last_message_at} />
                  </div>
                  {c.unread_count > 0 && (
                    <span className={styles.unread}>{c.unread_count} unread</span>
                  )}
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>

      <NewMessageModal
        open={composeOpen}
        onClose={() => { setComposeOpen(false); loadInbox(); }}
      />
    </>
  );
}
