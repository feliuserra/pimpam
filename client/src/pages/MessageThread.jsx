import { useState, useEffect, useCallback, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import DateSeparator from "../components/DateSeparator";
import Header from "../components/Header";
import MessageBubble from "../components/MessageBubble";
import Avatar from "../components/ui/Avatar";
import Spinner from "../components/ui/Spinner";
import SendIcon from "../components/ui/icons/SendIcon";
import { useAuth } from "../contexts/AuthContext";
import { useToast } from "../contexts/ToastContext";
import { useWS } from "../contexts/WSContext";
import { useWSSend } from "../contexts/WSContext";
import * as messagesApi from "../api/messages";
import * as usersApi from "../api/users";
import { encryptMessage } from "../crypto/encrypt";
import { tryDecrypt } from "../crypto/tryDecrypt";
import styles from "./MessageThread.module.css";

export default function MessageThread() {
  const { userId } = useParams();
  const navigate = useNavigate();
  const { user: me, isNewDevice, dismissNewDevice } = useAuth();
  const toast = useToast();
  const wsSend = useWSSend();
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [typing, setTyping] = useState(false);
  const [recipientKey, setRecipientKey] = useState(null);
  const [otherUser, setOtherUser] = useState(null);
  const [hasMore, setHasMore] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const bottomRef = useRef(null);
  const topSentinelRef = useRef(null);
  const messageListRef = useRef(null);
  const typingTimeout = useRef(null);
  const lastTypingSent = useRef(0);
  const initialScrollDone = useRef(false);
  const hasMoreRef = useRef(true);
  const loadingMoreRef = useRef(false);
  const messagesRef = useRef([]);
  const newMessageIds = useRef(new Set());

  const otherUserId = parseInt(userId, 10);

  // Fetch other user info (username, avatar, E2EE key) via inbox
  useEffect(() => {
    messagesApi.getInbox().then((res) => {
      const conv = res.data.find((c) => c.other_user_id === otherUserId);
      if (conv) {
        setOtherUser({ username: conv.other_username, avatar_url: conv.other_avatar_url });
        usersApi.getUser(conv.other_username).then((r) => {
          if (r.data.e2ee_public_key) setRecipientKey(r.data.e2ee_public_key);
          setOtherUser({ username: r.data.username, avatar_url: r.data.avatar_url });
        }).catch(() => {});
      }
    }).catch(() => {});
  }, [otherUserId]);

  // Load messages and decrypt them
  const loadAndDecrypt = useCallback(async () => {
    try {
      const res = await messagesApi.getConversation(otherUserId);
      const reversed = [...res.data].reverse();
      const decrypted = await Promise.all(reversed.map((m) => tryDecrypt(m, me?.id)));
      setMessages(decrypted);
    } catch {
      // silent
    }
  }, [otherUserId, me?.id]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    loadAndDecrypt()
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [loadAndDecrypt]);

  // Mark as read on mount
  useEffect(() => {
    messagesApi.markRead(otherUserId).catch(() => {});
  }, [otherUserId]);

  // Scroll to bottom on initial load
  useEffect(() => {
    if (!loading && messages.length > 0 && !initialScrollDone.current) {
      bottomRef.current?.scrollIntoView();
      initialScrollDone.current = true;
    }
  }, [loading, messages]);

  // Live new_message from WS — append single message instead of full reload
  useWS(
    "new_message",
    useCallback(async (data) => {
      if (data.sender_id === otherUserId && data.message_id) {
        try {
          const res = await messagesApi.getSingleMessage(data.message_id);
          const decrypted = await tryDecrypt(res.data, me?.id);
          newMessageIds.current.add(decrypted.id);
          setMessages((prev) => [...prev, decrypted]);
          setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
        } catch {
          // Fallback: full reload if single fetch fails
          loadAndDecrypt();
        }
        messagesApi.markRead(otherUserId).catch(() => {});
      }
    }, [otherUserId, me?.id, loadAndDecrypt]),
  );

  // Live message_deleted from WS — update message to tombstone
  useWS(
    "message_deleted",
    useCallback((data) => {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === data.message_id
            ? { ...m, is_deleted: true, ciphertext: "", decryptedText: "" }
            : m,
        ),
      );
    }, []),
  );

  // Read receipt from WS — sender sees blue ✓✓
  useWS(
    "messages_read",
    useCallback((data) => {
      if (data.reader_id === otherUserId && data.message_ids) {
        const readSet = new Set(data.message_ids);
        setMessages((prev) =>
          prev.map((m) => (readSet.has(m.id) ? { ...m, is_read: true } : m)),
        );
      }
    }, [otherUserId]),
  );

  // Typing indicator from WS
  useWS(
    "typing",
    useCallback((data) => {
      if (data.sender_id === otherUserId) {
        setTyping(true);
        clearTimeout(typingTimeout.current);
        typingTimeout.current = setTimeout(() => setTyping(false), 5000);
      }
    }, [otherUserId]),
  );

  // Typing stop from WS
  useWS(
    "typing_stop",
    useCallback((data) => {
      if (data.sender_id === otherUserId) {
        setTyping(false);
        clearTimeout(typingTimeout.current);
      }
    }, [otherUserId]),
  );

  // Keep refs in sync with state for the observer callback
  useEffect(() => { messagesRef.current = messages; }, [messages]);
  useEffect(() => { hasMoreRef.current = hasMore; }, [hasMore]);
  useEffect(() => { loadingMoreRef.current = loadingMore; }, [loadingMore]);

  // Infinite scroll — load older messages when top sentinel is visible
  useEffect(() => {
    const sentinel = topSentinelRef.current;
    if (!sentinel) return;
    const observer = new IntersectionObserver(
      async ([entry]) => {
        if (!entry.isIntersecting || loadingMoreRef.current || !hasMoreRef.current || messagesRef.current.length === 0) return;
        setLoadingMore(true);
        loadingMoreRef.current = true;
        const oldestId = messagesRef.current[0]?.id;
        try {
          const res = await messagesApi.getConversation(otherUserId, oldestId);
          const older = [...res.data].reverse();
          if (older.length < 50) { setHasMore(false); hasMoreRef.current = false; }
          if (older.length > 0) {
            const decrypted = await Promise.all(older.map((m) => tryDecrypt(m, me?.id)));
            const listEl = messageListRef.current;
            const prevHeight = listEl?.scrollHeight || 0;
            setMessages((prev) => [...decrypted, ...prev]);
            // Preserve scroll position after prepend
            requestAnimationFrame(() => {
              if (listEl) listEl.scrollTop = listEl.scrollHeight - prevHeight;
            });
          }
        } catch {
          // silent
        } finally {
          setLoadingMore(false);
          loadingMoreRef.current = false;
        }
      },
      { threshold: 0.1 },
    );
    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [otherUserId, me?.id]);

  // Send typing_stop on unmount
  useEffect(() => {
    return () => {
      wsSend?.({ type: "typing_stop", recipient_id: otherUserId });
    };
  }, [wsSend, otherUserId]);

  const handleDelete = async (messageId) => {
    try {
      await messagesApi.deleteMessage(messageId);
      setMessages((prev) =>
        prev.map((m) =>
          m.id === messageId
            ? { ...m, is_deleted: true, ciphertext: "", decryptedText: "" }
            : m,
        ),
      );
    } catch (err) {
      const detail = err?.response?.data?.detail;
      toast(detail || "Could not delete message", "error");
    }
  };

  const handleSend = async (e) => {
    e.preventDefault();
    const content = text.trim();
    if (!content || sending) return;
    setSending(true);
    // Stop typing indicator on send
    wsSend?.({ type: "typing_stop", recipient_id: otherUserId });
    try {
      let payload;
      if (recipientKey) {
        const senderPubKey = me?.e2ee_public_key || null;
        const { ciphertext, encryptedKey, senderEncryptedKey } =
          await encryptMessage(content, recipientKey, senderPubKey);
        payload = {
          recipient_id: otherUserId,
          ciphertext,
          encrypted_key: encryptedKey,
          sender_encrypted_key: senderEncryptedKey,
        };
      } else {
        payload = {
          recipient_id: otherUserId,
          ciphertext: content,
          encrypted_key: "",
        };
      }
      const res = await messagesApi.send(payload);
      setText("");
      // Append own sent message locally instead of full reload
      const decrypted = await tryDecrypt(res.data, me?.id);
      newMessageIds.current.add(decrypted.id);
      setMessages((prev) => [...prev, decrypted]);
      setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
    } catch {
      // silent
    } finally {
      setSending(false);
    }
  };

  const handleInputChange = (e) => {
    const val = e.target.value;
    setText(val);
    const now = Date.now();
    if (val.trim()) {
      // Throttle: only send typing every 2 seconds
      if (now - lastTypingSent.current > 2000) {
        wsSend?.({ type: "typing", recipient_id: otherUserId });
        lastTypingSent.current = now;
      }
    } else {
      // Input cleared — stop typing
      wsSend?.({ type: "typing_stop", recipient_id: otherUserId });
      lastTypingSent.current = 0;
    }
  };

  return (
    <>
      <Header
        left={
          <div className={styles.headerLeft}>
            <button onClick={() => navigate("/messages")} className={styles.back}>
              &larr; Back
            </button>
            {otherUser && (
              <>
                <Avatar src={otherUser.avatar_url} alt={`@${otherUser.username}`} size={28} />
                <span className={styles.headerName}>@{otherUser.username}</span>
              </>
            )}
          </div>
        }
      />

      <div className={styles.container}>
        {isNewDevice && (
          <div className={styles.newDeviceBanner} role="alert">
            <span>New device detected. Messages from before this device cannot be decrypted.</span>
            <button onClick={dismissNewDevice} className={styles.dismissBanner} aria-label="Dismiss">
              &times;
            </button>
          </div>
        )}

        <div className={styles.messageList} ref={messageListRef}>
          {loading ? (
            <div className={styles.loader}><Spinner size={24} /></div>
          ) : messages.length === 0 ? (
            <p className={styles.empty}>No messages yet. Say hi!</p>
          ) : (
            <>
              <div ref={topSentinelRef} className={styles.topSentinel}>
                {loadingMore && <Spinner size={16} />}
              </div>
              {messages.map((msg, i) => {
                const prevDate = i > 0 ? new Date(messages[i - 1].created_at).toDateString() : null;
                const curDate = new Date(msg.created_at).toDateString();
                const showSeparator = curDate !== prevDate;
                const isOwn = msg.sender_id === me?.id;
                const prevSameSender = i > 0 && messages[i - 1].sender_id === msg.sender_id && !showSeparator;
                const nextSameSender = i < messages.length - 1 && messages[i + 1].sender_id === msg.sender_id
                  && new Date(messages[i + 1].created_at).toDateString() === curDate;
                const isNew = newMessageIds.current.has(msg.id);
                return (
                  <div key={msg.id} style={prevSameSender ? { marginTop: -4 } : undefined} className={isNew ? styles.slideIn : undefined}>
                    {showSeparator && <DateSeparator date={msg.created_at} />}
                    <MessageBubble
                      message={{ ...msg, ciphertext: msg.decryptedText ?? msg.ciphertext }}
                      isOwn={isOwn}
                      onDelete={isOwn && !msg.is_deleted ? () => handleDelete(msg.id) : undefined}
                      grouped={prevSameSender}
                      hasNext={nextSameSender}
                    />
                  </div>
                );
              })}
            </>
          )}
          {typing && <div className={styles.typing}>typing...</div>}
          <div ref={bottomRef} />
        </div>

        {/* Compose bar */}
        <form className={styles.compose} onSubmit={handleSend}>
          <input
            className={styles.input}
            value={text}
            onChange={handleInputChange}
            placeholder={recipientKey ? "Encrypted message..." : "Write a message..."}
            maxLength={5000}
            disabled={sending}
          />
          <button
            type="submit"
            className={styles.sendBtn}
            disabled={!text.trim() || sending}
            aria-label="Send"
          >
            <SendIcon size={20} />
          </button>
        </form>
      </div>
    </>
  );
}
