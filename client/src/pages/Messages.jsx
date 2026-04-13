import { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import Header from "../components/Header";
import Avatar from "../components/ui/Avatar";
import Spinner from "../components/ui/Spinner";
import RelativeTime from "../components/ui/RelativeTime";
import NewMessageModal from "../components/NewMessageModal";
import PlusIcon from "../components/ui/icons/PlusIcon";
import { useAuth } from "../contexts/AuthContext";
import { useWS } from "../contexts/WSContext";
import { useNotifications } from "../contexts/NotificationContext";
import * as messagesApi from "../api/messages";
import * as usersApi from "../api/users";
import { tryDecrypt } from "../crypto/tryDecrypt";
import styles from "./Messages.module.css";

export default function Messages() {
  const { user: me, deviceId } = useAuth();
  const { refetch } = useNotifications();
  const [conversations, setConversations] = useState([]);
  const [suggestions, setSuggestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [composeOpen, setComposeOpen] = useState(false);

  const loadInbox = useCallback(async () => {
    try {
      const res = await messagesApi.getInbox(deviceId);
      // Decrypt last message preview for each conversation
      const withPreviews = await Promise.all(
        res.data.map(async (c) => {
          if (c.last_message_is_deleted) {
            return { ...c, preview: "This message was deleted" };
          }
          if (!c.last_message_ciphertext) return c;
          try {
            // Build a fake message with device_keys for tryDecrypt
            const deviceKeys = c.last_message_device_key
              ? [{ device_id: deviceId, encrypted_key: c.last_message_device_key }]
              : [];
            const fakeMsg = {
              ciphertext: c.last_message_ciphertext,
              device_keys: deviceKeys,
            };
            const decrypted = await tryDecrypt(fakeMsg);
            const text = decrypted.decryptedText || "";
            return { ...c, preview: text.length > 50 ? text.slice(0, 50) + "..." : text };
          } catch {
            return c;
          }
        }),
      );
      setConversations(withPreviews);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, [deviceId]);

  useEffect(() => { loadInbox(); refetch(); }, [loadInbox, refetch]);

  // Load following list for suggestions (exclude users with existing conversations)
  useEffect(() => {
    if (!me?.username) return;
    usersApi.getFollowing(me.username, { limit: 50 })
      .then((res) => setSuggestions(res.data))
      .catch(() => {});
  }, [me?.username]);

  // Reload inbox on new message — bumps conversation to top with fresh preview
  useWS(
    "new_message",
    useCallback(() => {
      loadInbox();
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
        ) : (
          <>
            {/* Friends to message suggestions */}
            {(() => {
              const convIds = new Set(conversations.map((c) => c.other_user_id));
              const friendSuggestions = suggestions.filter((u) => !convIds.has(u.id));
              if (friendSuggestions.length === 0) return null;
              return (
                <div className={styles.suggestionsSection}>
                  <span className={styles.suggestionsLabel}>Friends to message</span>
                  <div className={styles.suggestionsRow}>
                    {friendSuggestions.slice(0, 10).map((u) => (
                      <Link
                        key={u.id}
                        to={`/messages/${u.id}`}
                        className={styles.suggestionItem}
                      >
                        <Avatar src={u.avatar_url} alt={`@${u.username}`} size={44} />
                        <span className={styles.suggestionName}>
                          {u.display_name || u.username}
                        </span>
                      </Link>
                    ))}
                  </div>
                </div>
              );
            })()}

            {conversations.length === 0 ? (
              <div className={styles.empty}>
                <p>No messages yet.</p>
                <button className={styles.startBtn} onClick={() => setComposeOpen(true)}>
                  Start a conversation
                </button>
              </div>
            ) : (
              <div className={styles.list}>
                <span className={styles.sectionLabel}>Conversations</span>
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
                        <span className={styles.convTime}>
                          <RelativeTime date={c.last_message_at} />
                        </span>
                      </div>
                      {c.preview && (
                        <span className={`${styles.convPreview} ${c.last_message_is_deleted ? styles.convPreviewDeleted : ""}`}>
                          {c.preview}
                        </span>
                      )}
                    </div>
                    {c.unread_count > 0 && (
                      <span className={styles.unreadBadge}>{c.unread_count}</span>
                    )}
                  </Link>
                ))}
              </div>
            )}
          </>
        )}
      </div>

      <NewMessageModal
        open={composeOpen}
        onClose={() => { setComposeOpen(false); loadInbox(); }}
      />
    </>
  );
}
