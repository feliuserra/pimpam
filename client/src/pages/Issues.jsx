import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import Header from "../components/Header";
import ArrowUpIcon from "../components/ui/icons/ArrowUpIcon";
import CommentIcon from "../components/ui/icons/CommentIcon";
import SearchIcon from "../components/ui/icons/SearchIcon";
import { useAuth } from "../contexts/AuthContext";
import { useToast } from "../contexts/ToastContext";
import * as issuesApi from "../api/issues";
import styles from "./Issues.module.css";

const CATEGORIES = ["bug", "feature", "improvement", "suggestion", "complaint"];
const STATUSES = { open: "Open", in_progress: "In progress", completed: "Completed", rejected: "Rejected" };

const EXAMPLES = {
  bug: [
    { title: "Profile photo disappears after editing bio", description: "When I edit my bio and save, my profile photo resets to the default avatar. Refreshing the page brings it back, but it's confusing." },
    { title: "Push notifications arrive twice on iOS", description: "Every notification (likes, comments, follows) shows up as a duplicate on my iPhone 15. Started happening after the last update." },
    { title: "Feed doesn't load when switching from WiFi to mobile data", description: "If I lose WiFi and switch to cellular, the feed shows a blank screen. I have to force-close and reopen the app to fix it." },
    { title: "Cannot unfollow users from their profile page", description: "Tapping the 'Following' button on someone's profile does nothing. The button flashes but the follow state doesn't change. Unfollowing from my following list works fine." },
    { title: "Dark mode text is unreadable in community descriptions", description: "In dark mode, community description text appears as dark grey on a dark background. Nearly invisible. Happens on both mobile and desktop." },
  ],
  feature: [
    { title: "Add bookmarks to save posts for later", description: "I'd love a way to bookmark posts without voting on them. A simple save button that collects posts into a private 'Saved' tab on my profile." },
    { title: "Allow scheduling posts for a future time", description: "As a community moderator, I'd like to schedule announcements to go out at specific times. Even a simple date/time picker when composing would be enough." },
    { title: "Support markdown formatting in posts", description: "Being able to use bold, italic, headings, and code blocks would make longer posts much more readable. A simple toolbar or markdown syntax would both work." },
    { title: "Add a 'mute' option separate from blocking", description: "Sometimes I want to stop seeing someone's posts without fully blocking them. A mute feature that hides their content from my feed without notifying them." },
    { title: "Enable polls in posts", description: "Let users create simple polls (2-6 options) that others can vote on. Great for community decisions and engagement. Results visible after voting." },
  ],
  improvement: [
    { title: "Make the compose button easier to reach on tall phones", description: "The compose button is at the very top of the screen. On phones over 6 inches, it's a stretch. Moving it to a floating action button at the bottom would help." },
    { title: "Show a character count when writing posts", description: "There's a character limit but no visible counter while typing. A small counter near the submit button would prevent surprises when hitting the limit." },
    { title: "Faster image loading in the feed", description: "Images in the feed take 2-3 seconds to appear even on fast connections. Progressive loading or blur-up placeholders would make scrolling feel smoother." },
    { title: "Better empty states across the app", description: "When I first joined, most screens just said 'Nothing here.' Adding helpful prompts like 'Follow people to see posts' or 'Join communities to get started' would help new users." },
    { title: "Remember my last-used community when composing", description: "Every time I write a new post, the community selector defaults to none. It would save time if it remembered the last community I posted to." },
  ],
  suggestion: [
    { title: "Weekly digest email of top community posts", description: "An optional weekly email summarizing the most-voted posts from communities I've joined. Helps me stay in the loop without checking the app constantly." },
    { title: "Add a 'quiet hours' setting for notifications", description: "Let users set hours when push notifications are silenced (e.g., 10pm-7am). Notifications still arrive but don't buzz or light up the screen." },
    { title: "Community-created post templates", description: "Let community moderators define optional post templates (like 'Bug Report' or 'Introduction') that appear when composing in their community." },
    { title: "Show trending topics without algorithmic ranking", description: "A simple list of hashtags or topics that many people are posting about today. Just sorted by volume, no engagement tricks — pure signal." },
    { title: "Let users set a custom accent colour for their profile", description: "A small personalisation touch: let users pick an accent colour that tints their profile header. Nothing wild, just from a curated palette of 8-10 colours." },
  ],
  complaint: [
    { title: "The app logs me out too frequently", description: "I get logged out almost every day even though I never tap log out. It's frustrating to re-enter my password constantly. Session persistence needs fixing." },
    { title: "Notification settings reset after every update", description: "Every time the app updates, my notification preferences go back to defaults. I have to re-disable email notifications each time." },
    { title: "Community search results are irrelevant", description: "Searching for 'photography' returns communities about cooking and politics before any actual photography communities. The search ranking needs work." },
    { title: "Loading times have gotten noticeably worse", description: "Over the past few weeks, the app has become slower. Feed takes 3-4 seconds to load, profiles take even longer. It used to be snappy." },
    { title: "No way to recover accidentally deleted posts", description: "I accidentally deleted a long post I spent an hour writing. There's no undo, no trash, no confirmation that feels serious enough. This needs a safety net." },
  ],
};

function getRandomExample(cat) {
  const list = EXAMPLES[cat];
  return list[Math.floor(Math.random() * list.length)];
}

function collectDeviceInfo() {
  const ua = navigator.userAgent;
  const platform = navigator.platform || "unknown";
  const screen = `${window.screen.width}x${window.screen.height}`;
  const viewport = `${window.innerWidth}x${window.innerHeight}`;
  const lang = navigator.language || "unknown";
  const touch = "ontouchstart" in window ? "yes" : "no";
  return `Browser: ${ua} | Platform: ${platform} | Screen: ${screen} | Viewport: ${viewport} | Language: ${lang} | Touch: ${touch}`;
}

function CategoryBadge({ category }) {
  return <span className={`${styles.categoryBadge} ${styles[category]}`}>{category}</span>;
}

function StatusBadge({ status }) {
  const cls = {
    open: styles.statusOpen,
    in_progress: styles.statusInProgress,
    completed: styles.statusCompleted,
    rejected: styles.statusRejected,
  };
  return <span className={cls[status] || styles.statusOpen}>{STATUSES[status] || status}</span>;
}

function IssueItem({ issue, onVote, user, onClick }) {
  const voted = issue.has_voted;

  return (
    <div className={styles.issueItem} onClick={onClick} role="button" tabIndex={0} onKeyDown={(e) => { if (e.key === "Enter") onClick(); }}>
      <div className={styles.voteCol}>
        <button
          className={voted ? styles.voteBtnActive : styles.voteBtn}
          onClick={(e) => {
            e.stopPropagation();
            onVote(issue.id, voted);
          }}
          disabled={!user}
          aria-label={voted ? "Remove vote" : "Vote for this issue"}
        >
          <ArrowUpIcon size={16} />
        </button>
        <span className={styles.voteCount}>{issue.vote_count}</span>
      </div>
      <div className={styles.issueContent}>
        <p className={styles.issueTitle}>{issue.title}</p>
        <div className={styles.issueMeta}>
          <CategoryBadge category={issue.category} />
          <StatusBadge status={issue.status} />
          {issue.is_closed && (
            <span className={styles.closedBadge}>Closed</span>
          )}
          {issue.is_security && (
            <span className={styles.securityBadge}>
              <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
              </svg>
              Security
            </span>
          )}
          {issue.poll && (
            <span className={styles.pollBadge}>Poll</span>
          )}
          {issue.comment_count > 0 && (
            <span style={{ display: "inline-flex", alignItems: "center", gap: 2 }}>
              <CommentIcon size={12} /> {issue.comment_count}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

export default function Issues() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { addToast } = useToast();
  const [issues, setIssues] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState(null);
  const [closedFilter, setClosedFilter] = useState(false);
  const [search, setSearch] = useState("");
  const [composing, setComposing] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState("feature");
  const [includeDevice, setIncludeDevice] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [addPoll, setAddPoll] = useState(false);
  const [pollQuestion, setPollQuestion] = useState("");
  const [pollOptions, setPollOptions] = useState(["", ""]);
  const [pollMultiple, setPollMultiple] = useState(false);

  // Pick a random example whenever category changes
  const example = useMemo(() => getRandomExample(category), [category]);

  const fetchIssues = useCallback(async () => {
    setLoading(true);
    try {
      const params = { sort: "votes", closed: closedFilter };
      if (filter) params.category = filter;
      const { data } = await issuesApi.list(params);
      setIssues(data);
    } catch {
      addToast("Failed to load issues", "error");
    } finally {
      setLoading(false);
    }
  }, [filter, closedFilter, addToast]);

  useEffect(() => {
    fetchIssues();
  }, [fetchIssues]);

  const handleVote = useCallback(
    async (issueId, alreadyVoted) => {
      setIssues((prev) =>
        prev.map((i) =>
          i.id === issueId
            ? {
                ...i,
                vote_count: alreadyVoted ? i.vote_count - 1 : i.vote_count + 1,
                has_voted: !alreadyVoted,
              }
            : i,
        ),
      );
      try {
        if (alreadyVoted) {
          await issuesApi.unvote(issueId);
        } else {
          await issuesApi.vote(issueId);
        }
      } catch {
        setIssues((prev) =>
          prev.map((i) =>
            i.id === issueId
              ? {
                  ...i,
                  vote_count: alreadyVoted ? i.vote_count + 1 : i.vote_count - 1,
                  has_voted: alreadyVoted,
                }
              : i,
          ),
        );
        addToast("Vote failed", "error");
      }
    },
    [addToast],
  );

  const filtered = search
    ? issues.filter(
        (i) =>
          i.title.toLowerCase().includes(search.toLowerCase()) ||
          i.description.toLowerCase().includes(search.toLowerCase())
      )
    : issues;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!title.trim() || !description.trim()) return;
    setSubmitting(true);
    try {
      const payload = { title: title.trim(), description: description.trim(), category };
      if (category === "bug" && includeDevice) {
        payload.device_info = collectDeviceInfo();
      }
      if (addPoll && pollQuestion.trim()) {
        const validOptions = pollOptions.map((o) => o.trim()).filter(Boolean);
        if (validOptions.length >= 2) {
          payload.poll = {
            question: pollQuestion.trim(),
            options: validOptions.map((text) => ({ text })),
            allows_multiple: pollMultiple,
          };
        }
      }
      await issuesApi.create(payload);
      setTitle("");
      setDescription("");
      setCategory("feature");
      setAddPoll(false);
      setPollQuestion("");
      setPollOptions(["", ""]);
      setPollMultiple(false);
      setComposing(false);
      addToast("Issue submitted!", "success");
      fetchIssues();
    } catch (err) {
      const msg = err.response?.data?.detail || "Failed to submit issue";
      addToast(msg, "error");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <Header
        left={<span>Issues &amp; Requests</span>}
        right={
          <div className={styles.headerRight}>
            <div className={styles.searchPill}>
              <SearchIcon size={14} />
              <input
                className={styles.searchInput}
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search issues..."
              />
            </div>
            {user && !composing && (
              <button className={styles.createBtn} onClick={() => setComposing(true)}>
                + Create
              </button>
            )}
          </div>
        }
      />

      <div className={styles.container}>
        <div className={styles.filters}>
          <div className={styles.closedToggle}>
            <button
              className={!closedFilter ? styles.toggleBtnActive : styles.toggleBtn}
              onClick={() => setClosedFilter(false)}
            >
              Open
            </button>
            <button
              className={closedFilter ? styles.toggleBtnActive : styles.toggleBtn}
              onClick={() => setClosedFilter(true)}
            >
              Closed
            </button>
          </div>
          <span className={styles.filterSep} />
          <button
            className={filter === null ? styles.filterBtnActive : styles.filterBtn}
            onClick={() => setFilter(null)}
          >
            All
          </button>
          {CATEGORIES.map((cat) => (
            <button
              key={cat}
              className={filter === cat ? styles.filterBtnActive : styles.filterBtn}
              onClick={() => setFilter(cat)}
            >
              {cat.charAt(0).toUpperCase() + cat.slice(1)}
            </button>
          ))}
        </div>

        <div className={styles.list}>
          {loading && issues.length === 0 ? (
            <div className={styles.empty}>Loading...</div>
          ) : filtered.length === 0 ? (
            <div className={styles.empty}>
              {search ? "No issues match your search." : "No issues yet. Be the first to submit one!"}
            </div>
          ) : (
            filtered.map((issue) => (
              <IssueItem
                key={issue.id}
                issue={issue}
                onVote={handleVote}
                user={user}
                onClick={() => navigate(`/issues/${issue.id}`)}
              />
            ))
          )}
        </div>

        {user && composing && (
          <div className={styles.composeSection}>
            <form className={styles.composeForm} onSubmit={handleSubmit}>
              <select value={category} onChange={(e) => setCategory(e.target.value)}>
                <option value="bug">Bug</option>
                <option value="feature">Feature</option>
                <option value="improvement">Improvement</option>
                <option value="suggestion">Suggestion</option>
                <option value="complaint">Complaint</option>
              </select>
              {category === "bug" && (
                <label className={styles.deviceToggle}>
                  <input
                    type="checkbox"
                    checked={includeDevice}
                    onChange={(e) => setIncludeDevice(e.target.checked)}
                  />
                  <span>Include device info (browser, screen size, OS) to help us reproduce</span>
                </label>
              )}
              <input
                type="text"
                placeholder={`e.g. "${example.title}"`}
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                minLength={5}
                maxLength={200}
                required
              />
              <textarea
                placeholder={`e.g. "${example.description}"`}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                minLength={10}
                maxLength={5000}
                required
              />
              <div className={styles.pollToggle}>
                <label>
                  <input
                    type="checkbox"
                    checked={addPoll}
                    onChange={(e) => setAddPoll(e.target.checked)}
                  />
                  <span>Add a poll</span>
                </label>
              </div>

              {addPoll && (
                <div className={styles.pollCompose}>
                  <input
                    type="text"
                    className={styles.pollQuestionInput}
                    placeholder="Poll question"
                    value={pollQuestion}
                    onChange={(e) => setPollQuestion(e.target.value)}
                    maxLength={300}
                  />
                  {pollOptions.map((opt, i) => (
                    <div key={i} className={styles.pollOptionRow}>
                      <input
                        type="text"
                        className={styles.pollOptionInput}
                        placeholder={`Option ${i + 1}`}
                        value={opt}
                        onChange={(e) => {
                          const next = [...pollOptions];
                          next[i] = e.target.value;
                          setPollOptions(next);
                        }}
                        maxLength={200}
                      />
                      {pollOptions.length > 2 && (
                        <button
                          type="button"
                          className={styles.pollRemoveOption}
                          onClick={() => setPollOptions(pollOptions.filter((_, j) => j !== i))}
                          aria-label={`Remove option ${i + 1}`}
                        >
                          &times;
                        </button>
                      )}
                    </div>
                  ))}
                  {pollOptions.length < 10 && (
                    <button
                      type="button"
                      className={styles.pollAddOption}
                      onClick={() => setPollOptions([...pollOptions, ""])}
                    >
                      + Add option
                    </button>
                  )}
                  <label className={styles.pollMultipleLabel}>
                    <input
                      type="checkbox"
                      checked={pollMultiple}
                      onChange={(e) => setPollMultiple(e.target.checked)}
                    />
                    <span>Allow multiple selections</span>
                  </label>
                </div>
              )}

              <div className={styles.composeActions}>
                <button
                  type="button"
                  className={styles.cancelBtn}
                  onClick={() => {
                    setComposing(false);
                    setTitle("");
                    setDescription("");
                  }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className={styles.submitBtn}
                  disabled={submitting || title.trim().length < 5 || description.trim().length < 10}
                >
                  {submitting ? "Submitting..." : "Submit"}
                </button>
              </div>
            </form>
          </div>
        )}
      </div>
    </>
  );
}
