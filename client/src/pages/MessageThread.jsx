import { useState, useEffect, useCallback, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import Header from "../components/Header";
import MessageBubble from "../components/MessageBubble";
import Modal from "../components/ui/Modal";
import Avatar from "../components/ui/Avatar";
import Spinner from "../components/ui/Spinner";
import LockIcon from "../components/ui/icons/LockIcon";
import SendIcon from "../components/ui/icons/SendIcon";
import { useAuth } from "../contexts/AuthContext";
import { useWS } from "../contexts/WSContext";
import { useWSSend } from "../contexts/WSContext";
import * as messagesApi from "../api/messages";
import * as usersApi from "../api/users";
import { encryptMessage } from "../crypto/encrypt";
import { decryptMessage } from "../crypto/decrypt";
import styles from "./MessageThread.module.css";

/**
 * Format a 64-char hex fingerprint as groups of 4 for readability.
 * e.g. "abcd 1234 ef56 ..."
 */
function formatFingerprint(hex) {
  if (!hex) return "—";
  return hex.match(/.{1,4}/g).join(" ");
}

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
  const { user: me, isNewDevice, dismissNewDevice, e2eeError, retryE2eeSetup } = useAuth();
  const wsSend = useWSSend();
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [typing, setTyping] = useState(false);
  const [recipientKey, setRecipientKey] = useState(null);
  const [otherUser, setOtherUser] = useState(null);
  const [showEncryptionInfo, setShowEncryptionInfo] = useState(false);
  const bottomRef = useRef(null);
  const typingTimeout = useRef(null);

  const otherUserId = parseInt(userId, 10);

  // Whether sending is blocked (no recipient key or E2EE setup failed)
  const sendBlocked = e2eeError || !recipientKey;

  // Fetch other user info (username, avatar, E2EE key + metadata)
  useEffect(() => {
    messagesApi.getInbox().then((res) => {
      const conv = res.data.find((c) => c.other_user_id === otherUserId);
      if (conv) {
        setOtherUser({ username: conv.other_username, avatar_url: conv.other_avatar_url });
        // Fetch their profile for E2EE public key and metadata
        usersApi.getUser(conv.other_username).then((r) => {
          if (r.data.e2ee_public_key) setRecipientKey(r.data.e2ee_public_key);
          setOtherUser({
            username: r.data.username,
            avatar_url: r.data.avatar_url,
            e2ee_key_fingerprint: r.data.e2ee_key_fingerprint,
            e2ee_key_set_at: r.data.e2ee_key_set_at,
          });
        }).catch(() => {});
      } else {
        // New conversation — fetch user directly by ID
        // Try fetching by navigating to the messages endpoint
        // The user info will be available after first message
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

  // Detect if recipient's key changed after the oldest loaded message
  const keyChangedAfterMessages = (() => {
    if (!otherUser?.e2ee_key_set_at || messages.length === 0) return false;
    const oldestMsg = messages[0];
    if (!oldestMsg?.created_at) return false;
    return new Date(otherUser.e2ee_key_set_at) > new Date(oldestMsg.created_at);
  })();

  const handleSend = async (e) => {
    e.preventDefault();
    const content = text.trim();
    if (!content || sending || sendBlocked) return;
    setSending(true);
    try {
      const senderPubKey = me?.e2ee_public_key || null;
      const { ciphertext, encryptedKey, senderEncryptedKey } =
        await encryptMessage(content, recipientKey, senderPubKey);
      const payload = {
        recipient_id: otherUserId,
        ciphertext,
        encrypted_key: encryptedKey,
        sender_encrypted_key: senderEncryptedKey,
      };
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
            {recipientKey && (
              <button
                className={styles.lockIcon}
                onClick={() => setShowEncryptionInfo(true)}
                aria-label="Encryption info"
                type="button"
              >
                <LockIcon size={16} />
              </button>
            )}
          </div>
        }
      />

      <div className={styles.container}>
        {/* E2EE setup error banner */}
        {e2eeError && (
          <div className={styles.e2eeErrorBanner} role="alert">
            <span>Encryption setup failed. You cannot send messages.</span>
            <button onClick={retryE2eeSetup} className={styles.retryBtn}>
              Retry
            </button>
          </div>
        )}

        {/* New device banner */}
        {isNewDevice && !e2eeError && (
          <div className={styles.newDeviceBanner} role="alert">
            <span>New device detected. Messages from before this device cannot be decrypted.</span>
            <button onClick={dismissNewDevice} className={styles.dismissBanner} aria-label="Dismiss">
              &times;
            </button>
          </div>
        )}

        {/* Key changed warning */}
        {keyChangedAfterMessages && !e2eeError && (
          <div className={styles.keyChangedBanner} role="alert">
            <span>
              This user&apos;s encryption key changed on{" "}
              {new Date(otherUser.e2ee_key_set_at).toLocaleDateString()}.
              Some earlier messages may not be readable.
            </span>
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
        {!e2eeError && !recipientKey && !loading ? (
          <div className={styles.waitingKeys}>
            <LockIcon size={16} />
            <span>Waiting for recipient&apos;s encryption keys...</span>
          </div>
        ) : (
          <form className={styles.compose} onSubmit={handleSend}>
            <input
              className={styles.input}
              value={text}
              onChange={handleInputChange}
              placeholder="Encrypted message..."
              maxLength={5000}
              disabled={sending || sendBlocked}
            />
            <button
              type="submit"
              className={styles.sendBtn}
              disabled={!text.trim() || sending || sendBlocked}
              aria-label="Send"
            >
              <SendIcon size={20} />
            </button>
          </form>
        )}
      </div>

      {/* Encryption info modal */}
      <Modal
        open={showEncryptionInfo}
        onClose={() => setShowEncryptionInfo(false)}
        title="Encryption Info"
      >
        <div className={styles.encryptionInfo}>
          <p className={styles.encryptionStatus}>
            <LockIcon size={16} />
            End-to-end encrypted
          </p>
          <div className={styles.fingerprintSection}>
            <h4>Your fingerprint</h4>
            <code className={styles.fingerprint}>
              {formatFingerprint(me?.e2ee_key_fingerprint)}
            </code>
          </div>
          <div className={styles.fingerprintSection}>
            <h4>{otherUser?.username ? `@${otherUser.username}'s fingerprint` : "Their fingerprint"}</h4>
            <code className={styles.fingerprint}>
              {formatFingerprint(otherUser?.e2ee_key_fingerprint)}
            </code>
          </div>
          <p className={styles.encryptionHint}>
            To verify encryption, compare these fingerprints with your contact through another channel.
          </p>
        </div>
      </Modal>
    </>
  );
}
