"""
Seed script — populates the database with test users, communities, follows,
memberships, posts, comments, votes, hashtags, stories, and consent logs.

Usage:
    cd /path/to/pimpam
    source .venv/bin/activate
    python scripts/seed.py
"""

import asyncio
import random
import re
from datetime import datetime, timedelta, timezone

from app.core.security import hash_password
from app.db.base import *  # noqa: F401,F403 — register all models with SQLAlchemy
from app.db.session import AsyncSessionLocal
from app.models.comment import Comment
from app.models.community import Community, CommunityMember
from app.models.consent import ConsentLog
from app.models.follow import Follow
from app.models.hashtag import Hashtag, PostHashtag
from app.models.post import Post
from app.models.story import Story
from app.models.user import User
from app.models.vote import Vote

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
    (
        0,
        0,
        "Universal Declaration turns 78",
        "Today marks 78 years since the UN adopted the Universal Declaration of Human Rights. How far have we come? What work remains? #humanrights #UN",
    ),
    (
        1,
        1,
        "New exoplanet in the habitable zone",
        "The James Webb telescope data confirms a rocky planet with water vapor in its atmosphere. This is genuinely exciting for the search for life. #JWST #exoplanet #science",
    ),
    (
        2,
        3,
        "Spaced repetition changed my life",
        "I started using spaced repetition for language learning 6 months ago. Went from zero to reading novels in Portuguese. Happy to share my approach. #learning #languages",
    ),
    (
        3,
        2,
        "What are you listening to this week?",
        "I've been deep into Radiohead's Kid A again. Twenty-six years old and it still sounds like the future. Drop your current obsession below. #music #radiohead",
    ),
    (
        4,
        7,
        "Why I contribute to open source",
        "It's not about the code. It's about building things that belong to everyone. Here's what I learned from 5 years of OSS contributions. #opensource #foss",
    ),
    (
        5,
        5,
        "Morning light in Lisbon",
        "Spent three weeks shooting nothing but morning light. The golden hour in Lisbon is something else entirely. #photography #lisbon #goldenhour",
    ),
    (
        6,
        4,
        "Arctic ice data for 2025",
        "Published our annual Arctic sea ice analysis. The trend continues to accelerate. Data and methodology linked in comments. #climate #arctic #science",
    ),
    (
        7,
        8,
        "The forgotten history of mutual aid",
        "Before welfare states, communities organized mutual aid societies. This history matters for understanding our present. #history #mutualaid",
    ),
    (
        8,
        9,
        "Digital art tools for beginners",
        "Getting started with digital art? Here's my honest comparison of free tools: Krita, GIMP, and Inkscape. No gatekeeping. #art #digitalart #opensource",
    ),
    (
        9,
        6,
        "Is privacy a right or a privilege?",
        "Governments and corporations treat privacy as something you earn through compliance. But the philosophical foundations say otherwise. #privacy #philosophy #rights",
    ),
    (
        10,
        15,
        "Coral reef restoration update",
        "Our team transplanted 2,000 coral fragments this season. Survival rate is 78% after 6 months. Cautiously optimistic. #ocean #coral #conservation",
    ),
    (
        11,
        16,
        "Coltrane's sheets of sound",
        "Spent the morning transcribing Giant Steps for the hundredth time. Every time I find something new. That's the magic of Coltrane. #jazz #coltrane #music",
    ),
    (
        12,
        17,
        "Teaching empathy through literature",
        "I've been using picture books to teach emotional intelligence to 7-year-olds. The results have been remarkable. #education #empathy #teaching",
    ),
    (
        13,
        14,
        "The beauty of Euler's identity",
        "e^(iπ) + 1 = 0. Five fundamental constants, three operations, one equation. Mathematics at its most elegant. #math #euler",
    ),
    (
        14,
        10,
        "Books that changed how I see the world",
        "My top 5: Sapiens, The Left Hand of Darkness, Braiding Sweetgrass, The Dispossessed, and Man's Search for Meaning. #books #reading",
    ),
    (
        15,
        11,
        "Japanese home cooking basics",
        "Forget restaurant sushi. Real Japanese home cooking is about rice, miso, pickles, and seasonal vegetables. Thread below. #cooking #japanese #food",
    ),
    (
        16,
        13,
        "Why indie film matters more than ever",
        "In an age of franchise fatigue, independent cinema is where the real storytelling happens. Here are 10 films from this year that prove it. #film #indiefilm #cinema",
    ),
    (
        17,
        12,
        "Burnout is not a badge of honor",
        "We need to stop glorifying overwork. Burnout is a systemic failure, not a personal one. Let's talk about real prevention. #mentalhealth #burnout",
    ),
    (
        18,
        18,
        "Rethinking GDP as a measure of progress",
        "GDP measures economic activity, not well-being. What would a better metric look like? Some proposals from development economics. #economics #GDP #wellbeing",
    ),
    (
        19,
        19,
        "Starting a food forest from scratch",
        "Year one progress on converting a quarter acre of lawn into a productive food forest. Mistakes made, lessons learned. #permaculture #foodforest",
    ),
    (
        6,
        1,
        "Feedback loops in climate systems",
        "Positive feedback loops are the scariest part of climate science. When warming causes more warming, where does it stop? #climate #science",
    ),
    (
        1,
        14,
        "The math behind gravitational lensing",
        "Einstein predicted it, and we use it daily now. Here's the surprisingly elegant geometry behind how massive objects bend light. #math #physics #einstein",
    ),
    (
        9,
        0,
        "Digital rights are human rights",
        "Access to information, freedom from surveillance, right to encryption — these aren't tech issues, they're human rights issues. #digitalrights #humanrights #privacy",
    ),
    (
        2,
        6,
        "Socrates would have loved the internet",
        "Socratic dialogue was about questioning everything in public. Social media could be that — if we built it right. Like this place. #philosophy #socrates",
    ),
    (
        4,
        1,
        "Open source in scientific research",
        "Reproducibility crisis? Open source your methods, data, and analysis. Science should be verifiable by anyone. #opensource #science #reproducibility",
    ),
    (
        14,
        6,
        "On solitude and thinking",
        "The best ideas come from boredom. We've optimized boredom out of existence and wonder why we feel intellectually stuck. #philosophy #solitude #thinking",
    ),
    (
        7,
        3,
        "History podcasts worth your time",
        "Curated list of history podcasts that are actually well-researched and not just entertainment. Drop yours too. #history #podcasts #learning",
    ),
    (
        3,
        16,
        "The link between jazz and mathematics",
        "Coltrane studied geometry. Monk played with prime-number-based rhythms. Jazz and math share a deep structural beauty. #jazz #math #coltrane",
    ),
    (
        17,
        3,
        "Learning to rest without guilt",
        "Productivity culture teaches us that rest is earned. Psychology says rest is a need. Here's how to unlearn the guilt. #mentalhealth #rest #psychology",
    ),
    (
        19,
        4,
        "Permaculture as climate adaptation",
        "Food forests sequester carbon, build soil, and produce food. Permaculture isn't just gardening — it's climate infrastructure. #permaculture #climate",
    ),
]

COMMENTS = [
    # (post_index, author_index, content, parent_comment_index_or_None)
    (
        0,
        2,
        "78 years and we're still fighting the same fights. But progress is real — just slower than we want.",
        None,
    ),
    (
        0,
        9,
        "The philosophical grounding of the UDHR is fascinating. Natural law meets pragmatic consensus.",
        None,
    ),
    (0, 4, "We need to talk more about digital rights in this context.", 1),
    (
        1,
        6,
        "Water vapor is promising but we need to confirm it's not just atmospheric transit artifacts.",
        None,
    ),
    (
        1,
        13,
        "The math behind spectral analysis of exoplanet atmospheres is beautiful.",
        None,
    ),
    (1, 2, "How long until we can determine if there's actually life?", 0),
    (
        2,
        14,
        "Which app do you use? I've been trying Anki but the learning curve is steep.",
        None,
    ),
    (
        2,
        7,
        "I used this for memorizing historical dates and events. Game changer.",
        None,
    ),
    (3, 11, "Kid A walked so that half of modern electronic music could run.", None),
    (3, 5, "Currently obsessed with Khruangbin. That bass tone is everything.", None),
    (
        4,
        1,
        "Open source is also about transparency and trust. Closed source means blind trust.",
        None,
    ),
    (
        4,
        9,
        "There's a philosophical argument here about the commons and collective ownership.",
        None,
    ),
    (
        5,
        8,
        "Lisbon light is unreal. The tiles reflecting golden hour light... chef's kiss.",
        None,
    ),
    (
        5,
        19,
        "Photography and patience — two things the modern world needs more of.",
        None,
    ),
    (
        6,
        10,
        "The marine data correlates with what we're seeing in ocean temperature readings.",
        None,
    ),
    (6, 1, "Can you share the raw dataset? I'd love to run some models.", None),
    (6, 18, "The economic implications of accelerated ice loss are staggering.", 1),
    (
        7,
        0,
        "Mutual aid is having a renaissance right now. History repeating in the best way.",
        None,
    ),
    (
        8,
        4,
        "Krita is seriously underrated. It rivals Photoshop for digital painting.",
        None,
    ),
    (
        9,
        0,
        "Privacy is a precondition for freedom. You can't have one without the other.",
        None,
    ),
    (
        9,
        4,
        "Encryption is not just a right — it's a necessity for all other digital rights.",
        0,
    ),
    (10, 6, "78% survival rate is excellent. What's the species mix?", None),
    (
        11,
        3,
        "Giant Steps is the Everest of jazz. Every musician should attempt it at least once.",
        None,
    ),
    (
        13,
        1,
        "Euler's identity connects e, i, pi, 1, and 0. It feels like a message from the universe.",
        None,
    ),
    (
        14,
        12,
        "The Left Hand of Darkness changed how I teach about perspective-taking.",
        None,
    ),
    (
        15,
        10,
        "Japanese food culture's emphasis on seasonality is so aligned with sustainable eating.",
        None,
    ),
    (
        17,
        2,
        "This resonates deeply. We need structural solutions, not just individual coping strategies.",
        None,
    ),
    (
        17,
        12,
        "As a teacher, I see burnout everywhere in education. It starts in the system design.",
        0,
    ),
    (
        18,
        7,
        "Bhutan's Gross National Happiness index is an interesting alternative model.",
        None,
    ),
    (
        19,
        6,
        "Food forests are one of the most effective carbon sequestration methods we have.",
        None,
    ),
]

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

PASSWORD = "Test1234!"


def _extract_hashtags(text: str) -> set[str]:
    """Extract #hashtag names from text."""
    return {m.group(1).lower() for m in re.finditer(r"#(\w+)", text or "")}


async def seed():
    async with AsyncSessionLocal() as db:
        from sqlalchemy import func, select

        count = (await db.execute(select(func.count(User.id)))).scalar_one()
        if count > 5:
            print(f"Database already has {count} users. Skipping seed.")
            return

        print("Seeding database...")
        now = datetime.now(timezone.utc)

        # --- Create users ---
        hashed = hash_password(PASSWORD)
        cat_avatars = [f"/avatars/cat-{i:02d}.svg" for i in range(1, 21)]
        users = []
        for idx, (username, display_name, bio) in enumerate(USERS):
            u = User(
                username=username,
                email=f"{username}@example.com",
                hashed_password=hashed,
                display_name=display_name,
                bio=bio,
                is_verified=True,
                karma=random.randint(10, 500),
                avatar_url=cat_avatars[idx % len(cat_avatars)],
                created_at=now - timedelta(days=random.randint(30, 180)),
            )
            db.add(u)
            users.append(u)

        await db.flush()
        print(f"  Created {len(users)} users")

        # --- Consent logs ---
        for u in users:
            for consent_type in ("terms_of_service", "privacy_policy"):
                db.add(
                    ConsentLog(user_id=u.id, consent_type=consent_type, version="1.0")
                )
        await db.flush()
        print(f"  Created {len(users) * 2} consent logs")

        # --- Create communities ---
        communities = []
        for i, (name, description, is_news) in enumerate(COMMUNITIES):
            c = Community(
                name=name,
                description=description,
                owner_id=users[i].id,
                member_count=1,
                is_news=is_news,
            )
            db.add(c)
            communities.append(c)

        await db.flush()

        for i, c in enumerate(communities):
            db.add(
                CommunityMember(community_id=c.id, user_id=users[i].id, role="owner")
            )

        print(f"  Created {len(communities)} communities")

        # --- Community memberships ---
        membership_count = 0
        for i, u in enumerate(users):
            other_communities = [c for j, c in enumerate(communities) if j != i]
            to_join = random.sample(other_communities, random.randint(3, 8))
            for c in to_join:
                db.add(CommunityMember(community_id=c.id, user_id=u.id))
                c.member_count += 1
                membership_count += 1

        await db.flush()
        print(f"  Created {membership_count} community memberships")

        # --- Follows ---
        follow_count = 0
        for i, u in enumerate(users):
            others = [o for j, o in enumerate(users) if j != i]
            for other in random.sample(others, random.randint(4, 10)):
                db.add(Follow(follower_id=u.id, followed_id=other.id))
                follow_count += 1

        await db.flush()
        print(f"  Created {follow_count} follows")

        # --- Posts (with staggered timestamps) ---
        posts = []
        for idx, (author_idx, community_idx, title, content) in enumerate(POSTS):
            p = Post(
                author_id=users[author_idx].id,
                community_id=communities[community_idx].id,
                title=title,
                content=content,
                karma=1,
                created_at=now - timedelta(hours=random.randint(1, 72)),
            )
            db.add(p)
            posts.append(p)

        await db.flush()
        print(f"  Created {len(posts)} posts")

        # --- Author votes (implicit +1) ---
        for idx, (author_idx, *_) in enumerate(POSTS):
            db.add(
                Vote(user_id=users[author_idx].id, post_id=posts[idx].id, direction=1)
            )

        await db.flush()

        # --- Community votes (85% up, 15% down) ---
        vote_count = 0
        for i, p in enumerate(posts):
            author_idx = POSTS[i][0]
            voters = [u for j, u in enumerate(users) if j != author_idx]
            num_voters = random.randint(3, 12)
            for voter in random.sample(voters, min(num_voters, len(voters))):
                direction = 1 if random.random() < 0.85 else -1
                db.add(Vote(user_id=voter.id, post_id=p.id, direction=direction))
                p.karma += direction
                vote_count += 1

        await db.flush()
        print(f"  Created {vote_count} votes (+ {len(posts)} author votes)")

        # --- Comments ---
        comment_objects = []
        for post_idx, author_idx, content, parent_idx in COMMENTS:
            parent_id = (
                comment_objects[parent_idx].id if parent_idx is not None else None
            )
            depth = 0 if parent_idx is None else comment_objects[parent_idx].depth + 1
            c = Comment(
                post_id=posts[post_idx].id,
                author_id=users[author_idx].id,
                content=content,
                parent_id=parent_id,
                depth=depth,
                created_at=now - timedelta(hours=random.randint(0, 48)),
            )
            db.add(c)
            comment_objects.append(c)
            await db.flush()

        print(
            f"  Created {len(COMMENTS)} comments ({sum(1 for *_, p in COMMENTS if p is not None)} replies)"
        )

        # --- Hashtags ---
        all_tags: dict[str, Hashtag] = {}
        post_tag_links = 0
        for i, p in enumerate(posts):
            tags = _extract_hashtags(POSTS[i][3])  # from content
            for tag_name in tags:
                if tag_name not in all_tags:
                    h = Hashtag(name=tag_name, post_count=0)
                    db.add(h)
                    await db.flush()
                    all_tags[tag_name] = h
                ht = all_tags[tag_name]
                ht.post_count += 1
                db.add(PostHashtag(post_id=p.id, hashtag_id=ht.id))
                post_tag_links += 1

        await db.flush()
        print(
            f"  Created {len(all_tags)} hashtags, {post_tag_links} post-hashtag links"
        )

        # --- Stories ---
        story_count = 0
        for author_idx, picsum_id, caption, hours_left in STORIES:
            db.add(
                Story(
                    author_id=users[author_idx].id,
                    image_url=f"https://picsum.photos/id/{picsum_id}/600/800",
                    caption=caption,
                    expires_at=now + timedelta(hours=hours_left),
                )
            )
            story_count += 1

        await db.flush()
        print(f"  Created {story_count} stories")

        # --- Connect existing users (donbenito, juanito) ---
        for username, n_follow, n_followers, n_communities, is_admin in [
            ("donbenito", 12, 8, 10, True),
            ("juanito", 8, 5, 6, False),
        ]:
            existing = (
                await db.execute(select(User).where(User.username == username))
            ).scalar_one_or_none()
            if not existing:
                continue
            if not existing.avatar_url or existing.avatar_url.startswith("/avatars/"):
                existing.avatar_url = random.choice(cat_avatars)
            existing.is_admin = is_admin
            existing.is_verified = True
            # Follow seed users
            for u in random.sample(users, min(n_follow, len(users))):
                db.add(Follow(follower_id=existing.id, followed_id=u.id))
            # Get followers back
            for u in random.sample(users, min(n_followers, len(users))):
                db.add(Follow(follower_id=u.id, followed_id=existing.id))
            # Join communities
            for c in random.sample(communities, min(n_communities, len(communities))):
                db.add(CommunityMember(community_id=c.id, user_id=existing.id))
                c.member_count += 1
            # Consent logs
            for consent_type in ("terms_of_service", "privacy_policy"):
                db.add(
                    ConsentLog(
                        user_id=existing.id, consent_type=consent_type, version="1.0"
                    )
                )
            await db.flush()
            role = "admin" if is_admin else "regular"
            print(
                f"  Connected {username} ({role}): {n_follow} follows, {n_followers} followers, {n_communities} communities"
            )

        await db.commit()
        print("\nSeed complete!")
        print(f"  Login with any username and password: {PASSWORD}")
        print(f"  Seed users: {', '.join(u[0] for u in USERS[:5])}...")
        print("  Admin: donbenito | Regular: juanito")


if __name__ == "__main__":
    asyncio.run(seed())
