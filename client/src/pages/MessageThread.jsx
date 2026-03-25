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
import * as usersApi from "../api/users";
import { encryptMessage } from "../crypto/encrypt";
import { decryptMessage } from "../crypto/decrypt";
import { exportPublicKey } from "../crypto/keys";
import styles from "./MessageThread.module.css";

/**
 * Try to decrypt a message. For own sent messages, use sender_encrypted_key.
 * For received messages, use encrypted_key. Falls back to plaintext or placeholder.
 */
async function tryDecrypt(msg, myUserId) {
  // If encrypted_key is empty, the message was sent as plaintext (pre-E2EE)
  if (!msg.encrypted_key) {
    return { ...msg, decryptedText: msg.ciphertext };
  }

  // Pick the right wrapped key: sender's copy for own messages, recipient's for theirs
  const isMine = msg.sender_id === myUserId;
  const keyToUse = isMine ? msg.sender_encrypted_key : msg.encrypted_key;

  if (!keyToUse) {
    // Own message sent before sender-copy existed
    return { ...msg, decryptedText: isMine ? "[Sent from another device]" : "[Cannot decrypt]" };
  }

  try {
    const text = await decryptMessage(msg.ciphertext, keyToUse);
    return { ...msg, decryptedText: text };
  } catch {
    return { ...msg, decryptedText: isMine ? "[Sent from another device]" : "[Cannot decrypt — sent from another device]" };
  }
}

export default function MessageThread() {
  const { userId } = useParams();
  const navigate = useNavigate();
  const { user: me, isNewDevice, dismissNewDevice } = useAuth();
  const wsSend = useWSSend();
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [typing, setTyping] = useState(false);
  const [recipientKey, setRecipientKey] = useState(null);
  const bottomRef = useRef(null);
  const typingTimeout = useRef(null);

  const otherUserId = parseInt(userId, 10);

  // Fetch recipient's public key
  useEffect(() => {
    // We need the username to fetch the user profile; try from URL or messages
    // For now, fetch conversation first to get username, then fetch profile
    // This is handled below after messages load
  }, []);

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

  // Fetch recipient's E2EE public key from their profile
  useEffect(() => {
    // We need the username; derive it from messages once loaded
    const otherMsg = messages.find((m) => m.sender_id === otherUserId);
    const username = otherMsg?.sender_username;
    if (!username) return;

    usersApi.getUser(username).then((res) => {
      if (res.data.e2ee_public_key) {
        setRecipientKey(res.data.e2ee_public_key);
      }
    }).catch(() => {});
  }, [messages, otherUserId]);

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
        loadAndDecrypt();
        messagesApi.markRead(otherUserId).catch(() => {});
      }
    }, [otherUserId, loadAndDecrypt]),
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
      let payload;
      if (recipientKey) {
        // Encrypt with recipient's public key + sender's own for re-reading
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
        // No public key available — send plaintext (pre-E2EE fallback)
        payload = {
          recipient_id: otherUserId,
          ciphertext: content,
          encrypted_key: "",
        };
      }
      await messagesApi.send(payload);
      setText("");
      await loadAndDecrypt();
    } catch {
      // silent
    } finally {
      setSending(false);
    }
  };

  const handleInputChange = (e) => {
    setText(e.target.value);
    wsSend?.({ type: "typing", data: { recipient_id: otherUserId } });
  };

  // Find other username from messages
  const otherUsername = messages.find((m) => m.sender_id === otherUserId)?.sender_username || null;

  return (
    <>
      <Header
        left={
          <div className={styles.headerLeft}>
            <button onClick={() => navigate("/messages")} className={styles.back}>
              &larr; Back
            </button>
            {otherUsername && <span className={styles.headerName}>@{otherUsername}</span>}
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

        <div className={styles.messageList}>
          {loading ? (
            <div className={styles.loader}><Spinner size={24} /></div>
          ) : messages.length === 0 ? (
            <p className={styles.empty}>No messages yet. Say hi!</p>
          ) : (
            messages.map((msg) => (
              <MessageBubble
                key={msg.id}
                message={{ ...msg, ciphertext: msg.decryptedText ?? msg.ciphertext }}
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
