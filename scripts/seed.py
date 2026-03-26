"""
Seed script — populates the database with test users, communities, follows, memberships, and posts.

Usage:
    cd /path/to/pimpam
    source .venv/bin/activate
    python scripts/seed.py
"""

import asyncio
import random
from datetime import datetime, timedelta, timezone

from app.core.security import hash_password
from app.db.base import *  # noqa: F401,F403 — register all models with SQLAlchemy
from app.db.session import AsyncSessionLocal
from app.models.community import Community, CommunityMember
from app.models.follow import Follow
from app.models.post import Post
from app.models.story import Story  # noqa: F811 — explicit import over star
from app.models.user import User

# ---------------------------------------------------------------------------
# Test data
# ---------------------------------------------------------------------------

USERS = [
    (
        "elena_rights",
        "Elena Vásquez",
        "Human rights lawyer. Justice is not negotiable.",
    ),
    (
        "marco_astro",
        "Marco Chen",
        "Astrophysics PhD student. Staring at stars for a living.",
    ),
    (
        "priya_learns",
        "Priya Sharma",
        "Lifelong learner. Currently obsessed with cognitive science.",
    ),
    (
        "tomás_guitar",
        "Tomás Rivera",
        "Guitarist, songwriter. Music is the universal language.",
    ),
    ("aisha_code", "Aisha Okafor", "Backend engineer. Open source enthusiast."),
    (
        "lucas_photo",
        "Lucas Bergström",
        "Street photographer. Finding beauty in the ordinary.",
    ),
    ("mei_climate", "Mei Tanaka", "Climate scientist. The data doesn't lie."),
    (
        "omar_history",
        "Omar Al-Rashid",
        "History teacher. The past explains the present.",
    ),
    (
        "sofia_art",
        "Sofía Morales",
        "Digital artist and illustrator. Color is my language.",
    ),
    (
        "james_philo",
        "James Okonkwo",
        "Philosophy grad student. Asking the uncomfortable questions.",
    ),
    (
        "nina_bio",
        "Nina Petrov",
        "Marine biologist. Saving the oceans one reef at a time.",
    ),
    ("david_jazz", "David Kim", "Jazz pianist. Improvisation is structured freedom."),
    (
        "clara_teach",
        "Clara Dubois",
        "Primary school teacher. Kids are the best philosophers.",
    ),
    ("raj_math", "Raj Patel", "Mathematician. Beauty in proofs."),
    ("anna_write", "Anna Lindqvist", "Novelist and essayist. Words shape worlds."),
    (
        "yuki_cook",
        "Yuki Nakamura",
        "Home cook and food blogger. Recipes are love letters.",
    ),
    ("carlos_film", "Carlos Mendoza", "Independent filmmaker. Stories that matter."),
    ("lena_psych", "Lena Fischer", "Psychologist. Mental health is health."),
    ("kwame_econ", "Kwame Asante", "Development economist. Equity is efficiency."),
    (
        "isla_garden",
        "Isla MacLeod",
        "Permaculture gardener. Growing food, growing community.",
    ),
]

# (name, description, is_news)
COMMUNITIES = [
    (
        "human-rights",
        "Defending dignity everywhere. News, cases, and action for human rights worldwide.",
        True,
    ),
    (
        "science",
        "Scientific discoveries, papers, and discussions. All disciplines welcome.",
        True,
    ),
    (
        "music",
        "Share what you're listening to, playing, or creating. All genres.",
        False,
    ),
    ("learning", "Resources, study tips, and motivation for lifelong learners.", False),
    (
        "climate-action",
        "Climate science, policy, and grassroots action. No denial, just solutions.",
        True,
    ),
    (
        "photography",
        "Share your shots, give feedback, discuss technique. All skill levels.",
        False,
    ),
    (
        "philosophy",
        "Big questions, thoughtful answers. From ancient wisdom to modern ethics.",
        False,
    ),
    (
        "open-source",
        "Free software, open protocols, digital rights. Code is politics.",
        False,
    ),
    (
        "history",
        "Learn from the past. Events, books, documentaries, and discussion.",
        True,
    ),
    (
        "art",
        "Visual art in all forms — painting, digital, sculpture, street art.",
        False,
    ),
    ("books", "Reading lists, reviews, and book club discussions.", False),
    ("cooking", "Recipes, techniques, and food culture from around the world.", False),
    (
        "mental-health",
        "Safe space for mental health discussion. You are not alone.",
        False,
    ),
    (
        "film",
        "Cinema discussion — indie, world cinema, classics, and new releases.",
        False,
    ),
    (
        "mathematics",
        "The queen of sciences. Puzzles, proofs, and mathematical beauty.",
        False,
    ),
    ("marine-life", "Oceans, reefs, marine biology. Protecting our blue planet.", True),
    ("jazz", "The art of improvisation. Recordings, gigs, theory, and history.", False),
    ("education", "Teaching methods, education policy, and classroom stories.", False),
    (
        "economics",
        "Markets, inequality, policy. Understanding how the world works.",
        True,
    ),
    (
        "permaculture",
        "Sustainable growing, food forests, soil health, and regenerative design.",
        False,
    ),
]

POSTS = [
    # (author_index, community_index, title, content)
    (
        0,
        0,
        "Universal Declaration turns 78",
        "Today marks 78 years since the UN adopted the Universal Declaration of Human Rights. How far have we come? What work remains?",
    ),
    (
        1,
        1,
        "New exoplanet in the habitable zone",
        "The James Webb telescope data confirms a rocky planet with water vapor in its atmosphere. This is genuinely exciting for the search for life.",
    ),
    (
        2,
        3,
        "Spaced repetition changed my life",
        "I started using spaced repetition for language learning 6 months ago. Went from zero to reading novels in Portuguese. Happy to share my approach.",
    ),
    (
        3,
        2,
        "What are you listening to this week?",
        "I've been deep into Radiohead's Kid A again. Twenty-six years old and it still sounds like the future. Drop your current obsession below.",
    ),
    (
        4,
        7,
        "Why I contribute to open source",
        "It's not about the code. It's about building things that belong to everyone. Here's what I learned from 5 years of OSS contributions.",
    ),
    (
        5,
        5,
        "Morning light in Lisbon",
        "Spent three weeks shooting nothing but morning light. The golden hour in Lisbon is something else entirely.",
    ),
    (
        6,
        4,
        "Arctic ice data for 2025",
        "Published our annual Arctic sea ice analysis. The trend continues to accelerate. Data and methodology linked in comments.",
    ),
    (
        7,
        8,
        "The forgotten history of mutual aid",
        "Before welfare states, communities organized mutual aid societies. This history matters for understanding our present.",
    ),
    (
        8,
        9,
        "Digital art tools for beginners",
        "Getting started with digital art? Here's my honest comparison of free tools: Krita, GIMP, and Inkscape. No gatekeeping.",
    ),
    (
        9,
        6,
        "Is privacy a right or a privilege?",
        "Governments and corporations treat privacy as something you earn through compliance. But the philosophical foundations say otherwise.",
    ),
    (
        10,
        15,
        "Coral reef restoration update",
        "Our team transplanted 2,000 coral fragments this season. Survival rate is 78% after 6 months. Cautiously optimistic.",
    ),
    (
        11,
        16,
        "Coltrane's sheets of sound",
        "Spent the morning transcribing Giant Steps for the hundredth time. Every time I find something new. That's the magic of Coltrane.",
    ),
    (
        12,
        17,
        "Teaching empathy through literature",
        "I've been using picture books to teach emotional intelligence to 7-year-olds. The results have been remarkable.",
    ),
    (
        13,
        14,
        "The beauty of Euler's identity",
        "e^(iπ) + 1 = 0. Five fundamental constants, three operations, one equation. Mathematics at its most elegant.",
    ),
    (
        14,
        10,
        "Books that changed how I see the world",
        "My top 5: Sapiens, The Left Hand of Darkness, Braiding Sweetgrass, The Dispossessed, and Man's Search for Meaning.",
    ),
    (
        15,
        11,
        "Japanese home cooking basics",
        "Forget restaurant sushi. Real Japanese home cooking is about rice, miso, pickles, and seasonal vegetables. Thread below.",
    ),
    (
        16,
        13,
        "Why indie film matters more than ever",
        "In an age of franchise fatigue, independent cinema is where the real storytelling happens. Here are 10 films from this year that prove it.",
    ),
    (
        17,
        12,
        "Burnout is not a badge of honor",
        "We need to stop glorifying overwork. Burnout is a systemic failure, not a personal one. Let's talk about real prevention.",
    ),
    (
        18,
        18,
        "Rethinking GDP as a measure of progress",
        "GDP measures economic activity, not well-being. What would a better metric look like? Some proposals from development economics.",
    ),
    (
        19,
        19,
        "Starting a food forest from scratch",
        "Year one progress on converting a quarter acre of lawn into a productive food forest. Mistakes made, lessons learned.",
    ),
    (
        6,
        1,
        "Feedback loops in climate systems",
        "Positive feedback loops are the scariest part of climate science. When warming causes more warming, where does it stop?",
    ),
    (
        1,
        14,
        "The math behind gravitational lensing",
        "Einstein predicted it, and we use it daily now. Here's the surprisingly elegant geometry behind how massive objects bend light.",
    ),
    (
        9,
        0,
        "Digital rights are human rights",
        "Access to information, freedom from surveillance, right to encryption — these aren't tech issues, they're human rights issues.",
    ),
    (
        2,
        6,
        "Socrates would have loved the internet",
        "Socratic dialogue was about questioning everything in public. Social media could be that — if we built it right. Like this place.",
    ),
    (
        4,
        1,
        "Open source in scientific research",
        "Reproducibility crisis? Open source your methods, data, and analysis. Science should be verifiable by anyone.",
    ),
    (
        14,
        6,
        "On solitude and thinking",
        "The best ideas come from boredom. We've optimized boredom out of existence and wonder why we feel intellectually stuck.",
    ),
    (
        7,
        3,
        "History podcasts worth your time",
        "Curated list of history podcasts that are actually well-researched and not just entertainment. Drop yours too.",
    ),
    (
        3,
        16,
        "The link between jazz and mathematics",
        "Coltrane studied geometry. Monk played with prime-number-based rhythms. Jazz and math share a deep structural beauty.",
    ),
    (
        17,
        3,
        "Learning to rest without guilt",
        "Productivity culture teaches us that rest is earned. Psychology says rest is a need. Here's how to unlearn the guilt.",
    ),
    (
        19,
        4,
        "Permaculture as climate adaptation",
        "Food forests sequester carbon, build soil, and produce food. Permaculture isn't just gardening — it's climate infrastructure.",
    ),
]

# Stories: (author_index, picsum_id, caption, hours_until_expiry)
# picsum_id maps to https://picsum.photos/id/{id}/600/800 for stable images
STORIES = [
    (0, 1015, "Justice never sleeps.", 20),
    (1, 1069, "Orion Nebula through my telescope tonight", 22),
    (2, 180, "New study notes — cognitive load theory", 18),
    (3, 452, "Late night jam session vibes", 10),
    (4, 0, "Debugging at sunset", 23),
    (5, 399, "Golden hour in Alfama district", 16),
    (6, 1036, "Arctic ice cores arrived at the lab", 21),
    (8, 1059, "Work in progress — digital portrait", 14),
    (9, 1067, "Reading Kierkegaard at the park", 19),
    (10, 1053, "Coral transplant day!", 12),
    (11, 96, "Piano keys and coffee", 8),
    (15, 292, "Today's miso soup from scratch", 6),
    (19, 28, "First harvest from the food forest!", 15),
    (5, 1039, "Shadows and geometry", 4),
    (1, 1062, "Star trails — 2 hour exposure", 3),
]

PASSWORD = "testpass123"


async def seed():
    async with AsyncSessionLocal() as db:
        # Check if already seeded
        from sqlalchemy import func, select

        count = (await db.execute(select(func.count(User.id)))).scalar_one()
        if count > 5:
            print(f"Database already has {count} users. Skipping seed.")
            return

        print("Seeding database...")

        # --- Create users ---
        hashed = hash_password(PASSWORD)
        cat_avatars = [f"/avatars/cat-{i:02d}.svg" for i in range(1, 21)]
        users = []
        for idx, (username, display_name, bio) in enumerate(USERS):
            u = User(
                username=username,
                email=f"{username}@test.pimpam.org",
                hashed_password=hashed,
                display_name=display_name,
                bio=bio,
                is_verified=True,
                karma=random.randint(10, 500),
                avatar_url=cat_avatars[idx % len(cat_avatars)],
            )
            db.add(u)
            users.append(u)

        await db.flush()
        print(f"  Created {len(users)} users")

        # --- Create communities ---
        communities = []
        for i, (name, description, is_news) in enumerate(COMMUNITIES):
            owner = users[i]
            c = Community(
                name=name,
                description=description,
                owner_id=owner.id,
                member_count=1,
                is_news=is_news,
            )
            db.add(c)
            communities.append(c)

        await db.flush()

        # Add owner memberships
        for i, c in enumerate(communities):
            db.add(
                CommunityMember(
                    community_id=c.id,
                    user_id=users[i].id,
                    role="owner",
                )
            )

        print(f"  Created {len(communities)} communities")

        # --- Add community memberships (each user joins 3-8 random communities) ---
        membership_count = 0
        for i, u in enumerate(users):
            # Pick random communities (excluding the one they own)
            other_communities = [c for j, c in enumerate(communities) if j != i]
            join_count = random.randint(3, 8)
            to_join = random.sample(
                other_communities, min(join_count, len(other_communities))
            )
            for c in to_join:
                db.add(
                    CommunityMember(
                        community_id=c.id,
                        user_id=u.id,
                    )
                )
                c.member_count += 1
                membership_count += 1

        await db.flush()
        print(f"  Created {membership_count} community memberships")

        # --- Add follows (each user follows 4-10 random others) ---
        follow_count = 0
        for i, u in enumerate(users):
            others = [o for j, o in enumerate(users) if j != i]
            to_follow = random.sample(others, random.randint(4, 10))
            for other in to_follow:
                db.add(
                    Follow(
                        follower_id=u.id,
                        followed_id=other.id,
                    )
                )
                follow_count += 1

        await db.flush()
        print(f"  Created {follow_count} follows")

        # --- Create posts ---
        post_count = 0
        for author_idx, community_idx, title, content in POSTS:
            p = Post(
                author_id=users[author_idx].id,
                community_id=communities[community_idx].id,
                title=title,
                content=content,
            )
            db.add(p)
            post_count += 1

        await db.flush()
        print(f"  Created {post_count} posts")

        # --- Create stories ---
        now = datetime.now(timezone.utc)
        story_count = 0
        for author_idx, picsum_id, caption, hours_left in STORIES:
            s = Story(
                author_id=users[author_idx].id,
                image_url=f"https://picsum.photos/id/{picsum_id}/600/800",
                caption=caption,
                expires_at=now + timedelta(hours=hours_left),
            )
            db.add(s)
            story_count += 1

        await db.flush()
        print(f"  Created {story_count} stories")

        # --- Connect existing user (donbenito) to the new content ---
        existing = (
            await db.execute(select(User).where(User.username == "donbenito"))
        ).scalar_one_or_none()

        if existing:
            # Give them an avatar if they don't have one
            if not existing.avatar_url:
                existing.avatar_url = random.choice(cat_avatars)
            # Follow 12 of the new users
            for u in random.sample(users, 12):
                db.add(Follow(follower_id=existing.id, followed_id=u.id))
            # Have 8 new users follow donbenito back
            for u in random.sample(users, 8):
                db.add(Follow(follower_id=u.id, followed_id=existing.id))
            # Join 10 communities
            for c in random.sample(communities, 10):
                db.add(CommunityMember(community_id=c.id, user_id=existing.id))
                c.member_count += 1
            await db.flush()
            print("  Connected donbenito: 12 follows, 8 followers, 10 communities")

        await db.commit()
        print("\nSeed complete!")
        print(f"  Login with any username (e.g. elena_rights) and password: {PASSWORD}")


if __name__ == "__main__":
    asyncio.run(seed())
