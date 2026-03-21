# Contributing to PimPam

First off: thank you. PimPam exists because people like you believe social media can be better. Every contribution — whether it's code, documentation, design, translation, bug reports, or just good ideas — makes this project stronger.

This guide will help you get started.

---

## Our philosophy on contributions

PimPam is built by the people, for the people. That means we actively welcome contributors of all skill levels, backgrounds, and experiences. You don't need to be a senior developer to help. If you care about building an ethical, open, human-first social platform, you belong here.

We value clear communication over clever code. We value accessibility over performance tricks. We value thoughtful discussion over rapid shipping. There's no rush. We're building something meant to last.

## How to contribute

### Reporting bugs

Found something broken? Open an issue and include:

- A clear, descriptive title.
- Steps to reproduce the problem.
- What you expected to happen vs. what actually happened.
- Your environment (browser, OS, Node.js version if relevant).
- Screenshots or logs if they help explain the issue.

Don't worry about formatting it perfectly. A messy bug report is infinitely better than an unreported bug.

### Suggesting features

Have an idea? We want to hear it. Open an issue with the "feature request" label and tell us:

- What problem does this solve?
- Who benefits from this feature?
- Does this align with PimPam's principles (no algorithms, no ads, privacy-first)?
- How might this work from a user's perspective?

Feature discussions are open to everyone. We make decisions as a community.

### Contributing code

1. **Fork the repository** and create a branch from `main`. Use a descriptive branch name like `feature/community-moderation-tools` or `fix/message-encryption-bug`.

2. **Follow the code style.** We use ESLint and Prettier with the project's configuration. Run `npm run lint` before submitting.

3. **Write tests.** If you're adding a feature, add tests for it. If you're fixing a bug, add a test that would have caught it. We aim for meaningful test coverage, not 100% line coverage.

4. **Keep pull requests focused.** One PR should do one thing. If you find yourself writing "and also..." in your PR description, consider splitting it into multiple PRs.

5. **Write a clear PR description.** Explain what your change does, why it's needed, and how you tested it. Link to any related issues.

6. **Be patient with reviews.** Maintainers are volunteers. We'll review your PR as soon as we can, and we'll do our best to provide constructive, respectful feedback.

### Contributing documentation

Good documentation is just as important as good code. If you notice something unclear, missing, or wrong in the docs, please fix it or open an issue. Documentation PRs are always welcome and deeply appreciated.

### Contributing translations

PimPam aims to be accessible to people everywhere, in their own language. If you'd like to help translate the platform, open an issue and we'll coordinate. Translation infrastructure is being designed with community contribution in mind from day one.

### Contributing design

We need designers. If you have ideas for UI/UX, accessibility improvements, or visual design, share mockups, sketches, or even rough ideas. Open an issue with the "design" label.

## Development setup

```bash
# Clone your fork
git clone https://github.com/YOUR-USERNAME/pimpam.git
cd pimpam

# Install dependencies
npm install

# Set up environment variables
cp .env.example .env

# Start the development server
npm run dev

# Run tests
npm test

# Run linting
npm run lint
```

Detailed setup instructions, including database configuration, will be added as the technical architecture takes shape.

## Code review process

Every contribution goes through code review. This isn't gatekeeping — it's how we maintain quality and share knowledge. Here's what we look for:

- **Does it work?** Does the code do what the PR description says?
- **Is it secure?** Does it handle user data responsibly? Could it introduce vulnerabilities?
- **Is it accessible?** Can people with different abilities use this feature?
- **Is it maintainable?** Will someone else be able to understand this code six months from now?
- **Does it respect privacy?** Does it collect only the minimum data necessary?
- **Is it consistent?** Does it follow the project's patterns and conventions?

## Decision-making

PimPam is governed by its community. For day-to-day technical decisions, maintainers use their best judgment. For larger decisions that affect the project's direction, we discuss openly in issues and seek consensus.

Any decision that touches PimPam's core principles — no algorithms, no ads, no data exploitation, open source forever — requires broad community discussion and cannot be made unilaterally.

## Communication

- **Issues:** For bugs, feature requests, and technical discussions.
- **Pull Requests:** For code and documentation contributions.
- **Discussions:** For broader conversations about PimPam's direction, philosophy, and community.

Be kind. Be constructive. Assume good faith. See our [Code of Conduct](CODE_OF_CONDUCT.md).

## Recognition

Every contributor matters. We maintain a CONTRIBUTORS file recognizing everyone who has helped build PimPam. Your first merged PR gets you added — and it stays there forever.

## Legal

By contributing to PimPam, you agree that your contributions will be licensed under the AGPL-3.0 license. You also certify that you have the right to submit the contribution and that it doesn't violate anyone else's intellectual property.

We may adopt a Contributor License Agreement (CLA) or Developer Certificate of Origin (DCO) in the future to formalize this, with community input on the specifics.

---

**Not sure where to start?** Look for issues labeled "good first issue" or "help wanted." Or just say hi in the discussions — we'll help you find something that matches your interests and skills.

Welcome to PimPam. Let's build something good together.
