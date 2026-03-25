import { useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import styles from "./Legal.module.css";

export default function Privacy() {
  const { hash } = useLocation();

  useEffect(() => {
    if (hash) {
      const el = document.getElementById(hash.slice(1));
      if (el) el.scrollIntoView({ behavior: "smooth" });
    }
  }, [hash]);

  return (
    <div className={styles.page}>
      <Link to="/" className={styles.backLink}>&larr; Back to PimPam</Link>
      <h1 className={styles.title}>Privacy Policy</h1>
      <p className={styles.updated}>Last updated: March 2026</p>

      <div className={styles.highlight}>
        <p>
          <strong>The short version:</strong> We collect only what we need to run the platform.
          We never sell your data. We never profile you for ads. Direct messages are
          end-to-end encrypted. You can export or delete your data at any time.
        </p>
      </div>

      <section className={styles.section}>
        <h2>1. Data we collect</h2>
        <h3>Information you provide</h3>
        <ul>
          <li><strong>Account data:</strong> username, email address, hashed password</li>
          <li><strong>Profile data:</strong> display name, bio, avatar (all optional)</li>
          <li><strong>Content:</strong> posts, comments, votes, community memberships</li>
          <li><strong>Messages:</strong> stored as encrypted ciphertext only — we cannot read them</li>
        </ul>

        <h3>Information we do NOT collect</h3>
        <ul>
          <li>Location data</li>
          <li>Device fingerprints</li>
          <li>Browsing history outside PimPam</li>
          <li>Contact lists</li>
          <li>Biometric data</li>
          <li>Behavioural analytics or tracking data</li>
        </ul>

        <h3>Technical logs</h3>
        <p>
          Server logs (IP addresses, request timestamps) are retained for a maximum
          of 30 days for security and debugging purposes, then permanently deleted.
        </p>
      </section>

      <section className={styles.section}>
        <h2>2. How we use your data</h2>
        <ul>
          <li>To provide and maintain the service</li>
          <li>To authenticate you and secure your account</li>
          <li>To deliver notifications you've opted into</li>
          <li>To moderate content that violates our Terms</li>
        </ul>
        <p>
          We <strong>never</strong> use your data for advertising, profiling,
          behavioural analysis, or sale to third parties.
        </p>
      </section>

      <section className={styles.section}>
        <h2>3. Data sharing</h2>
        <p>
          We do not sell, rent, or share your personal data with third parties,
          with the following exceptions:
        </p>
        <ul>
          <li><strong>Federation:</strong> If you interact with users on other ActivityPub-compatible instances, your public profile and public posts are shared with those instances as part of the protocol.</li>
          <li><strong>Legal requirements:</strong> We may disclose data if required by law, such as a valid court order.</li>
        </ul>
      </section>

      <section className={styles.section}>
        <h2>4. Data security</h2>
        <ul>
          <li>Passwords are hashed with bcrypt (cost factor 12)</li>
          <li>All traffic uses TLS 1.3 encryption in transit</li>
          <li>Sensitive data at rest is encrypted with AES-256</li>
          <li>Direct messages use end-to-end encryption — the server stores only ciphertext</li>
          <li>Two-factor authentication (TOTP) available for all accounts</li>
        </ul>
      </section>

      <section className={styles.section}>
        <h2>5. Data retention</h2>
        <ul>
          <li><strong>Account data:</strong> retained while your account is active</li>
          <li><strong>Deleted content:</strong> removed from servers upon deletion</li>
          <li><strong>Deleted accounts:</strong> personal data permanently removed after a 7-day grace period</li>
          <li><strong>Unverified accounts:</strong> automatically deleted after 30 days</li>
          <li><strong>Technical logs:</strong> retained for a maximum of 30 days</li>
          <li><strong>Consent records:</strong> purged after 30 days</li>
        </ul>
      </section>

      <section className={styles.section} id="gdpr">
        <h2>6. Your rights (GDPR)</h2>
        <p>
          If you are in the European Economic Area (EEA), the UK, or any
          jurisdiction with equivalent data protection laws, you have the
          following rights:
        </p>
        <ul>
          <li><strong>Right to access:</strong> Request a copy of all personal data we hold about you</li>
          <li><strong>Right to rectification:</strong> Correct inaccurate personal data via your profile settings</li>
          <li><strong>Right to erasure:</strong> Delete your account and all associated data</li>
          <li><strong>Right to data portability:</strong> Export your data in a machine-readable format</li>
          <li><strong>Right to restriction:</strong> Request that we limit processing of your data</li>
          <li><strong>Right to object:</strong> Object to processing of your data</li>
          <li><strong>Right to withdraw consent:</strong> Withdraw consent at any time without affecting prior processing</li>
        </ul>

        <div className={styles.highlight}>
          <p>
            <strong>How to exercise these rights:</strong> Go to <Link to="/settings/data">Settings &rarr; Data &amp; Privacy</Link> to
            export your data or delete your account. For other requests,
            email <a href="mailto:privacy@pimpam.org">privacy@pimpam.org</a>.
          </p>
        </div>

        <h3>Legal basis for processing</h3>
        <ul>
          <li><strong>Consent:</strong> You consent to data processing when you register and accept our terms</li>
          <li><strong>Contract:</strong> Processing necessary to provide the service you signed up for</li>
          <li><strong>Legitimate interest:</strong> Security monitoring and abuse prevention</li>
        </ul>

        <h3>Data Protection Officer</h3>
        <p>
          For GDPR-related inquiries, contact our data protection
          team at <a href="mailto:privacy@pimpam.org">privacy@pimpam.org</a>.
        </p>
      </section>

      <section className={styles.section}>
        <h2>7. Children's privacy</h2>
        <p>
          PimPam is not intended for children under 13. We do not knowingly
          collect data from children under 13. If you believe a child has
          created an account, please contact us so we can remove it.
        </p>
      </section>

      <section className={styles.section}>
        <h2>8. Changes to this policy</h2>
        <p>
          We will notify users of significant changes through the platform.
          The "last updated" date at the top reflects the most recent revision.
        </p>
      </section>

      <p className={styles.contact}>
        Questions? Reach us at <a href="mailto:privacy@pimpam.org">privacy@pimpam.org</a>
      </p>
    </div>
  );
}
