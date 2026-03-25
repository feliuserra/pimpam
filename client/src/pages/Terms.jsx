import { Link } from "react-router-dom";
import styles from "./Legal.module.css";

export default function Terms() {
  return (
    <div className={styles.page}>
      <Link to="/" className={styles.backLink}>&larr; Back to PimPam</Link>
      <h1 className={styles.title}>Terms of Service</h1>
      <p className={styles.updated}>Last updated: March 2026</p>

      <section className={styles.section}>
        <h2>1. What PimPam is</h2>
        <p>
          PimPam is an open-source, community-owned social platform. We don't run ads,
          sell data, or use algorithms to rank your feed. Your timeline is chronological,
          your data is yours, and our code is public under the AGPL-3.0 licence.
        </p>
      </section>

      <section className={styles.section}>
        <h2>2. Who can use PimPam</h2>
        <p>You must be at least 13 years old to create an account. By registering, you confirm that you meet this requirement.</p>
        <p>You are responsible for keeping your login credentials secure. Please don't share your password or let others access your account.</p>
      </section>

      <section className={styles.section}>
        <h2>3. Your content</h2>
        <p>
          You own everything you post. By sharing content on PimPam, you grant us
          a licence to display, distribute, and store it as part of the service. You
          can delete your content at any time — when you do, we remove it from our servers.
        </p>
        <p>You agree not to post content that:</p>
        <ul>
          <li>Is illegal, threatening, or promotes violence</li>
          <li>Harasses, bullies, or targets individuals or groups</li>
          <li>Contains child sexual abuse material (CSAM)</li>
          <li>Infringes on intellectual property rights</li>
          <li>Is spam, misleading, or fraudulent</li>
          <li>Contains malware or attempts to compromise security</li>
        </ul>
      </section>

      <section className={styles.section}>
        <h2>4. Community moderation</h2>
        <p>
          Communities are moderated by their members through a transparent process.
          Moderation actions (content removal, bans) are visible and appealable.
          We don't use shadow banning or opaque moderation.
        </p>
        <p>
          Ban proposals require community consensus. If you believe a moderation
          action was unjust, you have the right to appeal.
        </p>
      </section>

      <section className={styles.section}>
        <h2>5. Privacy and data</h2>
        <p>
          We collect only the minimum data necessary to run the service. We never
          sell, share, or repurpose your data for advertising. Direct messages are
          end-to-end encrypted — we cannot read them.
        </p>
        <p>
          For full details, see our <Link to="/privacy">Privacy Policy</Link>.
        </p>
      </section>

      <section className={styles.section}>
        <h2>6. Account termination</h2>
        <p>
          You can delete your account at any time from Settings. Account deletion
          has a 7-day grace period during which you can cancel. After that, your
          personal data is permanently removed.
        </p>
        <p>
          We may suspend or terminate accounts that repeatedly violate these terms
          or pose a safety risk to the community.
        </p>
      </section>

      <section className={styles.section}>
        <h2>7. Open source</h2>
        <p>
          PimPam's source code is available under the AGPL-3.0 licence. Anyone
          can inspect, modify, and self-host the platform. This transparency is
          fundamental to our commitment to user trust.
        </p>
      </section>

      <section className={styles.section}>
        <h2>8. Disclaimer</h2>
        <p>
          PimPam is provided "as is." We do our best to keep the platform running
          smoothly, but we can't guarantee uninterrupted service. We are not liable
          for content posted by users.
        </p>
      </section>

      <section className={styles.section}>
        <h2>9. Changes to these terms</h2>
        <p>
          We may update these terms from time to time. When we make significant
          changes, we'll notify users through the platform. Continued use after
          changes constitutes acceptance.
        </p>
      </section>

      <p className={styles.contact}>
        Questions? Reach us at <a href="mailto:legal@pimpam.org">legal@pimpam.org</a>
      </p>
    </div>
  );
}
