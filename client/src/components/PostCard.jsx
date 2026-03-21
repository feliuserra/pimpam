import styles from "./PostCard.module.css";

export default function PostCard({ post }) {
  const date = new Date(post.created_at).toLocaleString();

  return (
    <article className={styles.card}>
      <h2 className={styles.title}>
        {post.url ? (
          <a href={post.url} target="_blank" rel="noopener noreferrer">
            {post.title}
          </a>
        ) : (
          post.title
        )}
      </h2>

      {post.content && <p className={styles.content}>{post.content}</p>}

      <footer className={styles.meta}>
        <span>{date}</span>
        <span>{post.karma} karma</span>
      </footer>
    </article>
  );
}
