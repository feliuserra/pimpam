import { useState, useEffect, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import Header from "../components/Header";
import Avatar from "../components/ui/Avatar";
import Spinner from "../components/ui/Spinner";
import RelativeTime from "../components/ui/RelativeTime";
import ArrowUpIcon from "../components/ui/icons/ArrowUpIcon";
import { useAuth } from "../contexts/AuthContext";
import { useToast } from "../contexts/ToastContext";
import errorMessage from "../api/errorMessage";
import * as issuesApi from "../api/issues";
import styles from "./IssueDetail.module.css";

const STATUSES = {
  open: "Open",
  in_progress: "In progress",
  completed: "Completed",
  rejected: "Rejected",
};

function CategoryBadge({ category }) {
  return <span className={`${styles.badge} ${styles[category]}`}>{category}</span>;
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

function PollSection({ poll, issueId, user, onUpdate }) {
  const { addToast } = useToast();
  const [voting, setVoting] = useState(false);
  const userVoted = poll.user_voted_option_ids.length > 0;

  const handleVote = async (optionId) => {
    if (!user || voting) return;
    const alreadyVoted = poll.user_voted_option_ids.includes(optionId);
    setVoting(true);
    try {
      if (alreadyVoted) {
        await issuesApi.unvotePoll(issueId, optionId);
      } else {
        await issuesApi.votePoll(issueId, optionId);
      }
      // Reload issue to get updated poll data
      const res = await issuesApi.get(issueId);
      onUpdate(res.data.poll);
    } catch (err) {
      addToast(errorMessage(err, "Couldn't register your vote. Try again."), "error");
    } finally {
      setVoting(false);
    }
  };

  return (
    <div className={styles.pollSection}>
      <p className={styles.pollQuestion}>{poll.question}</p>
      {poll.allows_multiple && (
        <span className={styles.pollMultipleHint}>Select all that apply</span>
      )}
      <div className={styles.pollOptions}>
        {poll.options.map((opt) => {
          const isSelected = poll.user_voted_option_ids.includes(opt.id);
          const pct = poll.total_votes > 0 ? Math.round((opt.vote_count / poll.total_votes) * 100) : 0;
          return (
            <button
              key={opt.id}
              className={isSelected ? styles.pollOptionSelected : styles.pollOption}
              onClick={() => handleVote(opt.id)}
              disabled={!user || voting}
            >
              <div className={styles.pollBar} style={{ width: `${pct}%` }} />
              <span className={styles.pollOptionText}>{opt.text}</span>
              {userVoted && (
                <span className={styles.pollOptionPct}>{pct}%</span>
              )}
            </button>
          );
        })}
      </div>
      <span className={styles.pollTotalVotes}>
        {poll.total_votes} {poll.total_votes === 1 ? "vote" : "votes"}
      </span>
    </div>
  );
}

export default function IssueDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const { addToast } = useToast();
  const [issue, setIssue] = useState(null);
  const [loading, setLoading] = useState(true);
  const [comments, setComments] = useState([]);
  const [commentsLoading, setCommentsLoading] = useState(true);
  const [content, setContent] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [closing, setClosing] = useState(false);

  useEffect(() => {
    setLoading(true);
    issuesApi
      .get(id)
      .then((res) => setIssue(res.data))
      .catch(() => setIssue(null))
      .finally(() => setLoading(false));
  }, [id]);

  const loadComments = useCallback(() => {
    setCommentsLoading(true);
    issuesApi
      .listComments(id, { limit: 200 })
      .then((res) => setComments(res.data))
      .catch(() => {})
      .finally(() => setCommentsLoading(false));
  }, [id]);

  useEffect(() => { loadComments(); }, [loadComments]);

  const handleVote = async () => {
    if (!user || !issue) return;
    const voted = issue.has_voted;
    setIssue((i) => ({
      ...i,
      vote_count: voted ? i.vote_count - 1 : i.vote_count + 1,
      has_voted: !voted,
    }));
    try {
      if (voted) {
        await issuesApi.unvote(id);
      } else {
        await issuesApi.vote(id);
      }
    } catch (err) {
      setIssue((i) => ({
        ...i,
        vote_count: voted ? i.vote_count + 1 : i.vote_count - 1,
        has_voted: voted,
      }));
      addToast(errorMessage(err, "Couldn't register your vote. Try again."), "error");
    }
  };

  const handleSubmitComment = async (e) => {
    e.preventDefault();
    if (!content.trim() || submitting) return;
    setSubmitting(true);
    try {
      const res = await issuesApi.addComment(id, { content: content.trim() });
      setComments((prev) => [...prev, res.data]);
      setContent("");
      setIssue((i) => i && { ...i, comment_count: i.comment_count + 1 });
    } catch (err) {
      addToast(errorMessage(err, "Couldn't post your comment. Try again."), "error");
    } finally {
      setSubmitting(false);
    }
  };

  const canClose = user && issue && (issue.author_id === user.id || user.is_admin);

  const handleToggleClose = async () => {
    if (!issue || closing) return;
    setClosing(true);
    try {
      const res = issue.is_closed
        ? await issuesApi.reopen(id)
        : await issuesApi.close(id);
      setIssue(res.data);
      addToast(issue.is_closed ? "Issue reopened" : "Issue closed", "success");
    } catch (err) {
      addToast(errorMessage(err, issue.is_closed ? "Couldn't reopen this issue." : "Couldn't close this issue."), "error");
    } finally {
      setClosing(false);
    }
  };

  if (loading) {
    return (
      <>
        <Header left={<Link to="/issues" className={styles.backLink}>&larr; Issues</Link>} />
        <div className={styles.loader}><Spinner size={28} /></div>
      </>
    );
  }

  if (!issue) {
    return (
      <>
        <Header left={<Link to="/issues" className={styles.backLink}>&larr; Issues</Link>} />
        <div className={styles.emptyState}>Issue not found.</div>
      </>
    );
  }

  return (
    <>
      <Header left={<Link to="/issues" className={styles.backLink}>&larr; Issues</Link>} />

      <div className={styles.container}>
        {/* Issue header */}
        <article className={styles.issueHeader}>
          <div className={styles.voteCol}>
            <button
              className={issue.has_voted ? styles.voteBtnActive : styles.voteBtn}
              onClick={handleVote}
              disabled={!user}
              aria-label={issue.has_voted ? "Remove vote" : "Vote"}
            >
              <ArrowUpIcon size={20} />
            </button>
            <span className={styles.voteCount}>{issue.vote_count}</span>
          </div>

          <div className={styles.issueBody}>
            <h1 className={styles.issueTitle}>{issue.title}</h1>
            <div className={styles.meta}>
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
              <span className={styles.metaSep}>&middot;</span>
              <span className={styles.metaText}>
                by @{issue.author_username}
              </span>
              <span className={styles.metaSep}>&middot;</span>
              <RelativeTime date={issue.created_at} className={styles.metaText} />
            </div>
            <p className={styles.description}>{issue.description}</p>
            {issue.poll && (
              <PollSection
                poll={issue.poll}
                issueId={issue.id}
                user={user}
                onUpdate={(updatedPoll) => setIssue((i) => ({ ...i, poll: updatedPoll }))}
              />
            )}
            {issue.device_info && (
              <details className={styles.deviceInfo}>
                <summary>Device info</summary>
                <p>{issue.device_info}</p>
              </details>
            )}
            {canClose && (
              <button
                className={issue.is_closed ? styles.reopenBtn : styles.closeBtn}
                onClick={handleToggleClose}
                disabled={closing}
              >
                {closing ? "..." : issue.is_closed ? "Reopen issue" : "Close issue"}
              </button>
            )}
          </div>
        </article>

        {/* Comments */}
        <section className={styles.commentsSection}>
          <h2 className={styles.commentsTitle}>
            {issue.comment_count} {issue.comment_count === 1 ? "comment" : "comments"}
          </h2>

          {commentsLoading && comments.length === 0 ? (
            <div className={styles.loader}><Spinner size={20} /></div>
          ) : comments.length === 0 ? (
            <p className={styles.noComments}>No comments yet. Be the first to respond.</p>
          ) : (
            <div className={styles.commentList}>
              {comments.map((c) => (
                <div key={c.id} className={styles.comment}>
                  <div className={styles.commentHeader}>
                    <span className={styles.commentAuthor}>
                      @{c.author_username}
                    </span>
                    {c.is_admin && (
                      <span className={styles.adminBadge}>Admin</span>
                    )}
                    <RelativeTime date={c.created_at} className={styles.commentTime} />
                  </div>
                  <p className={styles.commentContent}>{c.content}</p>
                </div>
              ))}
            </div>
          )}

          {/* Comment compose */}
          {user ? (
            <form className={styles.commentForm} onSubmit={handleSubmitComment}>
              <textarea
                className={styles.commentInput}
                value={content}
                onChange={(e) => setContent(e.target.value)}
                placeholder="Write a comment..."
                rows={2}
                maxLength={2000}
              />
              <button
                type="submit"
                className={styles.submitBtn}
                disabled={submitting || !content.trim()}
              >
                {submitting ? "Posting..." : "Post comment"}
              </button>
            </form>
          ) : (
            <p className={styles.loginPrompt}>
              <Link to="/login">Sign in</Link> to comment.
            </p>
          )}
        </section>
      </div>
    </>
  );
}
