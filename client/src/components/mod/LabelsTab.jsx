import { useState, useEffect } from "react";
import Spinner from "../ui/Spinner";
import * as labelsApi from "../../api/communityLabels";
import styles from "./ModSection.module.css";

export default function LabelsTab({ communityName }) {
  const [labels, setLabels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState(null);

  const fetchLabels = () => {
    labelsApi
      .list(communityName)
      .then((r) => setLabels(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchLabels();
  }, [communityName]);

  const handleDelete = async (labelId) => {
    if (!window.confirm("Delete this label? Posts with it will lose the label.")) return;
    try {
      await labelsApi.remove(communityName, labelId);
      fetchLabels();
    } catch {
      // silent
    }
  };

  const handleMoveUp = async (index) => {
    if (index === 0) return;
    const ids = labels.map((l) => l.id);
    [ids[index - 1], ids[index]] = [ids[index], ids[index - 1]];
    try {
      const { data } = await labelsApi.reorder(communityName, ids);
      setLabels(data);
    } catch {
      // silent
    }
  };

  const handleMoveDown = async (index) => {
    if (index >= labels.length - 1) return;
    const ids = labels.map((l) => l.id);
    [ids[index], ids[index + 1]] = [ids[index + 1], ids[index]];
    try {
      const { data } = await labelsApi.reorder(communityName, ids);
      setLabels(data);
    } catch {
      // silent
    }
  };

  if (loading) return <div className={styles.loader}><Spinner size={20} /></div>;

  return (
    <div>
      <div className={styles.sectionHeader}>
        <h3 className={styles.heading}>Labels ({labels.length})</h3>
        <button className={styles.btn} onClick={() => { setShowForm(!showForm); setEditingId(null); }}>
          {showForm ? "Cancel" : "Add Label"}
        </button>
      </div>

      {showForm && (
        <LabelForm
          communityName={communityName}
          onSaved={() => { setShowForm(false); fetchLabels(); }}
        />
      )}

      {labels.length === 0 ? (
        <p className={styles.empty}>No labels yet. Create one to organize posts.</p>
      ) : (
        <div className={styles.list}>
          {labels.map((label, index) => (
            <div key={label.id} className={styles.card}>
              {editingId === label.id ? (
                <LabelForm
                  communityName={communityName}
                  initial={label}
                  onSaved={() => { setEditingId(null); fetchLabels(); }}
                  onCancel={() => setEditingId(null)}
                />
              ) : (
                <>
                  <div className={styles.cardRow}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      {label.color && (
                        <span
                          style={{
                            display: "inline-block",
                            width: 12,
                            height: 12,
                            borderRadius: "50%",
                            background: label.color,
                          }}
                          aria-hidden="true"
                        />
                      )}
                      <strong>{label.name}</strong>
                    </div>
                    <div style={{ display: "flex", gap: 4 }}>
                      <button className={styles.smallBtn} onClick={() => handleMoveUp(index)} disabled={index === 0} aria-label="Move up">
                        &uarr;
                      </button>
                      <button className={styles.smallBtn} onClick={() => handleMoveDown(index)} disabled={index === labels.length - 1} aria-label="Move down">
                        &darr;
                      </button>
                    </div>
                  </div>
                  {label.description && (
                    <p className={styles.cardText}>{label.description}</p>
                  )}
                  <div style={{ display: "flex", gap: 8, marginTop: 6 }}>
                    <button className={styles.smallBtn} onClick={() => setEditingId(label.id)}>Edit</button>
                    <button className={styles.dangerBtn} style={{ fontSize: "0.78rem", padding: "4px 12px" }} onClick={() => handleDelete(label.id)}>
                      Delete
                    </button>
                  </div>
                </>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function LabelForm({ communityName, initial, onSaved, onCancel }) {
  const [name, setName] = useState(initial?.name || "");
  const [color, setColor] = useState(initial?.color || "#6366f1");
  const [description, setDescription] = useState(initial?.description || "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      if (initial) {
        await labelsApi.update(communityName, initial.id, {
          name: name.trim(),
          color: color || null,
          description: description.trim() || null,
        });
      } else {
        await labelsApi.create(communityName, {
          name: name.trim(),
          color: color || null,
          description: description.trim() || null,
        });
      }
      onSaved();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to save label");
    } finally {
      setBusy(false);
    }
  };

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      <input
        className={styles.input}
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="Label name"
        maxLength={50}
        required
      />
      <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
        <label style={{ fontSize: "0.85rem" }}>Color:</label>
        <input
          type="color"
          value={color}
          onChange={(e) => setColor(e.target.value)}
          style={{ width: 36, height: 28, border: "none", cursor: "pointer" }}
        />
      </div>
      <input
        className={styles.input}
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        placeholder="Description (optional)"
        maxLength={200}
      />
      {error && <p className={styles.error} role="alert">{error}</p>}
      <div style={{ display: "flex", gap: 8 }}>
        <button type="submit" className={styles.btn} disabled={busy || !name.trim()}>
          {busy ? "Saving..." : initial ? "Update" : "Create"}
        </button>
        {onCancel && (
          <button type="button" className={styles.smallBtn} onClick={onCancel}>
            Cancel
          </button>
        )}
      </div>
    </form>
  );
}
