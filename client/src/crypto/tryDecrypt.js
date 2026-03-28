import { decryptMessage } from "./decrypt";

/**
 * Try to decrypt a message. For own sent messages, use sender_encrypted_key.
 * For received messages, use encrypted_key. Falls back to plaintext or placeholder.
 */
export async function tryDecrypt(msg, myUserId) {
  // If encrypted_key is empty, the message was sent as plaintext (pre-E2EE)
  if (!msg.encrypted_key) {
    return { ...msg, decryptedText: msg.ciphertext };
  }

  // Pick the right wrapped key: sender's copy for own messages, recipient's for theirs
  const isMine = msg.sender_id === myUserId;
  const keyToUse = isMine ? msg.sender_encrypted_key : msg.encrypted_key;

  if (!keyToUse) {
    // Own message sent before sender-copy existed
    return {
      ...msg,
      decryptedText: isMine ? "[Sent from another device]" : "[Cannot decrypt]",
    };
  }

  try {
    const text = await decryptMessage(msg.ciphertext, keyToUse);
    return { ...msg, decryptedText: text };
  } catch {
    return {
      ...msg,
      decryptedText: isMine
        ? "[Sent from another device]"
        : "[Cannot decrypt — sent from another device]",
    };
  }
}
