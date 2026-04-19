import { useState } from "react";
import { useNavigate } from "react-router-dom";
import Modal from "./ui/Modal";
import LockIcon from "./ui/icons/LockIcon";
import { useAuth } from "../contexts/AuthContext";
import * as usersApi from "../api/users";
import * as messagesApi from "../api/messages";
import * as devicesApi from "../api/devices";
import { encryptMessage } from "../crypto/encrypt";
import styles from "./NewMessageModal.module.css";

export default function NewMessageModal({ open, onClose }) {
  const navigate = useNavigate();
  const { user: me } = useAuth();
  const [username, setUsername] = useState("");
  const [message, setMessage] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (sending) return;
    setSending(true);
    setError("");
    try {
      // Look up the user to get their ID
      const cleanUsername = username.trim().replace(/^@/, "");
      const userRes = await usersApi.getUser(cleanUsername);
      const recipientId = userRes.data.id;

      // Fetch recipient and sender device keys for encryption
      const [recipientDkRes, senderDkRes] = await Promise.all([
        devicesApi.getUserDeviceKeys(cleanUsername),
        devicesApi.getMyDevices(),
      ]);
      const recipientDeviceKeys = recipientDkRes.data;
      const senderDeviceKeys = senderDkRes.data.map((d) => ({
        device_id: d.id,
        public_key: d.public_key,
      }));

      if (recipientDeviceKeys.length === 0) {
        setError("This user hasn't set up encryption yet. Messages cannot be sent.");
        setSending(false);
        return;
      }

      const { ciphertext, deviceKeys } =
        await encryptMessage(message.trim(), recipientDeviceKeys, senderDeviceKeys);
      const payload = {
        recipient_id: recipientId,
        ciphertext,
        device_keys: deviceKeys,
      };
      await messagesApi.send(payload);
      setUsername("");
      setMessage("");
      onClose();
      navigate(`/messages/${recipientId}`);
    } catch (err) {
      if (err.response?.status === 404) {
        setError("User not found");
      } else {
        setError(err.response?.data?.detail || "Failed to send message");
      }
    } finally {
      setSending(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose} title="New Message">
      <form className={styles.form} onSubmit={handleSubmit}>
        <label className={styles.label}>
          To
          <input
            className={styles.input}
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="@username"
            required
          />
        </label>

        <label className={styles.label}>
          Message
          <textarea
            className={styles.textarea}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Write your message..."
            rows={3}
            maxLength={5000}
            required
          />
        </label>

        {error && <p className={styles.error} role="alert">{error}</p>}

        <button
          type="submit"
          className={styles.sendBtn}
          disabled={sending || !username.trim() || !message.trim()}
        >
          {sending ? "Sending..." : "Send"}
        </button>

        <p className={styles.encryptionNote}>
          <LockIcon size={14} /> Messages are end-to-end encrypted
        </p>
      </form>
    </Modal>
  );
}
