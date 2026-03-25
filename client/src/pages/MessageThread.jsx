import { useState, useEffect, useCallback, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import Header from "../components/Header";
import MessageBubble from "../components/MessageBubble";
import Spinner from "../components/ui/Spinner";
import SendIcon from "../components/ui/icons/SendIcon";
import { useAuth } from "../contexts/AuthContext";
import { useWS } from "../contexts/WSContext";
import { useWSSend } from "../contexts/WSContext";
import * as messagesApi from "../api/messages";
import styles from "./MessageThread.module.css";

export default function MessageThread() {
  const { userId } = useParams();
  const navigate = useNavigate();
  const { user: me } = useAuth();
  const wsSend = useWSSend();
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [typing, setTyping] = useState(false);
  const bottomRef = useRef(null);
  const typingTimeout = useRef(null);

  const otherUserId = parseInt(userId, 10);

  // Load messages
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    messagesApi
      .getConversation(otherUserId)
      .then((res) => {
        if (cancelled) return;
        // API returns newest-first, reverse for display
        setMessages([...res.data].reverse());
      })
      .catch(() => {})
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [otherUserId]);

  // Mark as read on mount
  useEffect(() => {
    messagesApi.markRead(otherUserId).catch(() => {});
  }, [otherUserId]);

  // Scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Live new_message from WS
  useWS(
    "new_message",
    useCallback((data) => {
      if (data.sender_id === otherUserId) {
        // Reload to get the full message object
        messagesApi.getConversation(otherUserId).then((res) => {
          setMessages([...res.data].reverse());
        }).catch(() => {});
        messagesApi.markRead(otherUserId).catch(() => {});
      }
    }, [otherUserId]),
  );

  // Typing indicator from WS
  useWS(
    "typing",
    useCallback((data) => {
      if (data.user_id === otherUserId) {
        setTyping(true);
        clearTimeout(typingTimeout.current);
        typingTimeout.current = setTimeout(() => setTyping(false), 3000);
      }
    }, [otherUserId]),
  );

  const handleSend = async (e) => {
    e.preventDefault();
    const content = text.trim();
    if (!content || sending) return;
    setSending(true);
    try {
      // For now, send plaintext as ciphertext (E2EE comes in Phase 15)
      await messagesApi.send({
        recipient_id: otherUserId,
        ciphertext: content,
        encrypted_key: "",
      });
      setText("");
      // Reload to show sent message
      const res = await messagesApi.getConversation(otherUserId);
      setMessages([...res.data].reverse());
    } catch {
      // silent
    } finally {
      setSending(false);
    }
  };

  const handleInputChange = (e) => {
    setText(e.target.value);
    // Send typing indicator
    wsSend?.({ type: "typing", data: { recipient_id: otherUserId } });
  };

  // Find other username from messages
  const otherUsername = messages.find((m) => m.sender_id === otherUserId)
    ? messages.find((m) => m.sender_id === otherUserId).sender_username
    : null;

  return (
    <>
      <Header
        left={
          <div className={styles.headerLeft}>
            <button onClick={() => navigate("/messages")} className={styles.back}>
              ← Back
            </button>
            {otherUsername && <span className={styles.headerName}>@{otherUsername}</span>}
          </div>
        }
      />

      <div className={styles.container}>
        <div className={styles.messageList}>
          {loading ? (
            <div className={styles.loader}><Spinner size={24} /></div>
          ) : messages.length === 0 ? (
            <p className={styles.empty}>No messages yet. Say hi!</p>
          ) : (
            messages.map((msg) => (
              <MessageBubble
                key={msg.id}
                message={msg}
                isOwn={msg.sender_id === me?.id}
              />
            ))
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
            placeholder="Write a message..."
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
