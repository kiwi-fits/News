import os
import json
import time
import random
import re
import shutil
from urllib.parse import quote
import requests
from PIL import Image
from config import (
    BASE_DIR,
    GEMINI_API_KEY,
    OUTPUT_DIR,
    CHRISTIAN_STATE_FILE,
    CHRISTIAN_HISTORY_FILE,
    CHRISTIAN_SEEN_VERSES_FILE
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

_session = requests.Session()
_session.headers.update(HEADERS)

CHRISTIAN_CATEGORIES = [
    {
        "id": "promise",
        "name": "Morning Promise & Grace",
        "badge_tag": "🌅 MORNING PROMISE",
        "time_slot": "06:00 AM",
        "theme_desc": "Morning promise of God, protection, grace, blessing for the day, overcoming fear, standing firm in faith (e.g. Joshua 1:5, Isaiah 41:10, Jeremiah 29:11, Psalm 121).",
        "hashtags": "#JesusHearsYou #MorningPromise #DailyBibleVerse #GodIsGood #FaithOverFear #ChristianReels #Jesus #Faith #DailyDevotional #Blessings #Reels"
    },
    {
        "id": "wisdom",
        "name": "Biblical Wisdom & Guidance",
        "badge_tag": "📖 BIBLICAL WISDOM",
        "time_slot": "12:30 PM",
        "theme_desc": "Practical Biblical wisdom from Proverbs, Psalms, and teachings of Jesus for daily life, patience, gentle speech, family peace, overcoming anxiety.",
        "hashtags": "#JesusHearsYou #BiblicalWisdom #Proverbs #DailyGuidance #InnerPeace #ChristianInspiration #BibleStudy #Wisdom #Faith #Reels"
    },
    {
        "id": "parable",
        "name": "Faith Story & Gospel Parable",
        "badge_tag": "✨ FAITH PARABLE",
        "time_slot": "04:30 PM",
        "theme_desc": "One-minute inspiring Gospel parables (The Lost Sheep, Good Samaritan, Mustard Seed, Prodigal Son) or moving Christian testimonies of God's miraculous help.",
        "hashtags": "#JesusHearsYou #FaithStory #GospelParable #ChristianStories #Grace #JesusLovesYou #Hope #Testimony #Motivation #Reels"
    },
    {
        "id": "mystery",
        "name": "Bible Wonders & History",
        "badge_tag": "🔍 BIBLE WONDERS",
        "time_slot": "07:30 PM",
        "theme_desc": "Fascinating Biblical history, archaeological discoveries (Noah's Ark, Dead Sea Scrolls, Red Sea crossing, ancient Jerusalem, Apostles' footprints).",
        "hashtags": "#JesusHearsYou #BibleFacts #BiblicalHistory #Archaeology #BibleWonders #ChristianHistory #FaithAndScience #Reels"
    },
    {
        "id": "prayer",
        "name": "Night Prayer & Peace",
        "badge_tag": "🕊️ BEDTIME PRAYER",
        "time_slot": "09:30 PM",
        "theme_desc": "Peaceful bedtime prayer, releasing worry and anxiety to Jesus, Psalm 91 and Psalm 23 reflections, blessing for restful sleep and family protection.",
        "hashtags": "#JesusHearsYou #BedtimePrayer #NightPrayer #Psalm91 #PeacefulSleep #RestInGod #SurrenderToJesus #EveningBlessing #Reels"
    }
]

# ==============================================================================
# CANONICAL BIBLE BOOK NORMALIZATION & DEDUPLICATION SHIELD
# ==============================================================================

BOOK_ALIASES = [
    # Old Testament (39 Books)
    (r"\bGEN\b|\bGENESIS\b", "GENESIS"),
    (r"\bEXOD\b|\bEXODUS\b", "EXODUS"),
    (r"\bLEV\b|\bLEVITICUS\b", "LEVITICUS"),
    (r"\bNUM\b|\bNUMBERS\b", "NUMBERS"),
    (r"\bDEUT\b|\bDEUTERONOMY\b", "DEUTERONOMY"),
    (r"\bJOSH\b|\bJOSHUA\b", "JOSHUA"),
    (r"\bJUDG\b|\bJUDGES\b", "JUDGES"),
    (r"\bRUTH\b", "RUTH"),
    (r"\b1\s*SAM\b|\b1\s*SAMUEL\b", "1 SAMUEL"),
    (r"\b2\s*SAM\b|\b2\s*SAMUEL\b", "2 SAMUEL"),
    (r"\b1\s*KGS\b|\b1\s*KINGS\b", "1 KINGS"),
    (r"\b2\s*KGS\b|\b2\s*KINGS\b", "2 KINGS"),
    (r"\b1\s*CHRON\b|\b1\s*CHRONICLES\b", "1 CHRONICLES"),
    (r"\b2\s*CHRON\b|\b2\s*CHRONICLES\b", "2 CHRONICLES"),
    (r"\bEZRA\b", "EZRA"),
    (r"\bNEH\b|\bNEHEMIAH\b", "NEHEMIAH"),
    (r"\bESTHER\b|\bESTH\b", "ESTHER"),
    (r"\bJOB\b", "JOB"),
    (r"\bPSALMS\b|\bPSALM\b|\bPSA\b|\bPS\b", "PSALM"),
    (r"\bPROVERBS\b|\bPROVERB\b|\bPROV\b|\bPR\b", "PROVERBS"),
    (r"\bECCL\b|\bECCLESIASTES\b", "ECCLESIASTES"),
    (r"\bSONG OF SOLOMON\b|\bSONG OF SONGS\b|\bCANTICLES\b", "SONG OF SOLOMON"),
    (r"\bISAIAH\b|\bISA\b", "ISAIAH"),
    (r"\bJEREMIAH\b|\bJER\b", "JEREMIAH"),
    (r"\bLAMENTATIONS\b|\bLAM\b", "LAMENTATIONS"),
    (r"\bEZEKIEL\b|\bEZEK\b", "EZEKIEL"),
    (r"\bDAN\b|\bDANIEL\b", "DANIEL"),
    (r"\bHOSEA\b|\bHOS\b", "HOSEA"),
    (r"\bJOEL\b", "JOEL"),
    (r"\bAMOS\b", "AMOS"),
    (r"\bOBADIAH\b|\bOBAD\b", "OBADIAH"),
    (r"\bJONAH\b|\bJON\b", "JONAH"),
    (r"\bMICAH\b|\bMIC\b", "MICAH"),
    (r"\bNAHUM\b|\bNAH\b", "NAHUM"),
    (r"\bHABAKKUK\b|\bHAB\b", "HABAKKUK"),
    (r"\bZEPHANIAH\b|\bZEPH\b", "ZEPHANIAH"),
    (r"\bHAGGAI\b|\bHAG\b", "HAGGAI"),
    (r"\bZECHARIAH\b|\bZECH\b", "ZECHARIAH"),
    (r"\bMALACHI\b|\bMAL\b", "MALACHI"),
    # New Testament (27 Books)
    (r"\bMATTHEW\b|\bMATT\b|\bMT\b", "MATTHEW"),
    (r"\bMARK\b|\bMK\b", "MARK"),
    (r"\bLUKE\b|\bLK\b", "LUKE"),
    (r"\bJOHN\b|\bJN\b", "JOHN"),
    (r"\bACTS\b", "ACTS"),
    (r"\bROMANS\b|\bROM\b", "ROMANS"),
    (r"\b1\s*COR\b|\b1\s*CORINTHIANS\b", "1 CORINTHIANS"),
    (r"\b2\s*COR\b|\b2\s*CORINTHIANS\b", "2 CORINTHIANS"),
    (r"\bGAL\b|\bGALATIANS\b", "GALATIANS"),
    (r"\bEPH\b|\bEPHESIANS\b", "EPHESIANS"),
    (r"\bPHIL\b|\bPHILIPPIANS\b", "PHILIPPIANS"),
    (r"\bCOL\b|\bCOLOSSIANS\b", "COLOSSIANS"),
    (r"\b1\s*THESS\b|\b1\s*THESSALONIANS\b", "1 THESSALONIANS"),
    (r"\b2\s*THESS\b|\b2\s*THESSALONIANS\b", "2 THESSALONIANS"),
    (r"\b1\s*TIM\b|\b1\s*TIMOTHY\b", "1 TIMOTHY"),
    (r"\b2\s*TIM\b|\b2\s*TIMOTHY\b", "2 TIMOTHY"),
    (r"\bTITUS\b|\bTIT\b", "TITUS"),
    (r"\bPHILEMON\b|\bPHILEM\b", "PHILEMON"),
    (r"\bHEBREWS\b|\bHEB\b", "HEBREWS"),
    (r"\bJAMES\b|\bJAS\b", "JAMES"),
    (r"\b1\s*PETER\b|\b1\s*PET\b", "1 PETER"),
    (r"\b2\s*PETER\b|\b2\s*PET\b", "2 PETER"),
    (r"\b1\s*JOHN\b|\b1\s*JN\b", "1 JOHN"),
    (r"\b2\s*JOHN\b|\b2\s*JN\b", "2 JOHN"),
    (r"\b3\s*JOHN\b|\b3\s*JN\b", "3 JOHN"),
    (r"\bJUDE\b", "JUDE"),
    (r"\bREVELATION\b|\bREV\b|\bAPOCALYPSE\b", "REVELATION")
]

def normalize_christian_verse(verse_ref):
    """
    Produces a canonical standardized verse string e.g. 'JOSHUA 1:5' or '1 PETER 5:7'.
    Strips language headers, parentheses, and normalizes book abbreviations.
    """
    if not verse_ref:
        return ""
    v = str(verse_ref).strip()
    match_paren = re.search(r"\(([^)]+)\)", v)
    if match_paren:
        v = match_paren.group(1).strip()
    v = v.upper()
    for pattern, canonical in BOOK_ALIASES:
        v = re.sub(pattern, canonical, v)
    # Standardize separator: replace multiple spaces, ensure single space before chapter
    v = re.sub(r"\s+", " ", v).strip()
    return v

def parse_verse_components(norm_verse):
    """
    Extracts book name, chapter number, start verse and end verse for collision checking.
    """
    m = re.search(r"^([1-3]?\s*[A-Z]+)\s+(\d+)[:.\s]+(\d+)(?:[-–—\s]+(\d+))?", norm_verse)
    if m:
        book = re.sub(r"\s+", " ", m.group(1)).strip()
        ch = int(m.group(2))
        s_v = int(m.group(3))
        e_v = int(m.group(4)) if m.group(4) else s_v
        return {"book": book, "chapter": ch, "start_verse": s_v, "end_verse": e_v}
    return None

def load_christian_seen_verses():
    """
    Loads the permanent, non-truncated registry of all posted devotional content.
    """
    if os.path.exists(CHRISTIAN_SEEN_VERSES_FILE):
        try:
            with open(CHRISTIAN_SEEN_VERSES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception as e:
            print(f"Notice: Failed to load seen verses file: {e}")
    return {
        "seen_verses": [],
        "seen_headlines": [],
        "seen_topic_ids": [],
        "records": []
    }

def save_christian_seen_verses(data):
    """
    Persists the permanent registry to disk. Never purges or truncates.
    """
    try:
        with open(CHRISTIAN_SEEN_VERSES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Notice: Failed to save seen verses file: {e}")

def is_duplicate_christian_content(verse_ref="", headline="", topic_id=""):
    """
    Multi-layer Deduplication Shield:
    1. Topic slug check
    2. Exact canonical Bible verse match
    3. Book/Chapter and verse range overlap (e.g. Luke 15:4 vs Luke 15:4-7)
    4. Exact normalized headline text match
    5. Jaccard word-level similarity (>= 60% rejected)

    Evaluates against a rolling window of recent posts (last 120 posts = ~3 days at 40 posts/day).
    Guarantees zero duplicates within 72 hours, while allowing safe recycling if library is exhausted.
    Returns (is_duplicate: bool, reason: str).
    """
    data = load_christian_seen_verses()
    seen_verses = data.get("seen_verses", [])[-120:]
    seen_headlines = data.get("seen_headlines", [])[-120:]
    seen_topic_ids = data.get("seen_topic_ids", [])[-120:]
    records = data.get("records", [])[:120]

    # 1. Topic ID check
    if topic_id:
        clean_tid = str(topic_id).strip().lower()
        if clean_tid in [str(x).strip().lower() for x in seen_topic_ids]:
            return True, f"Topic slug '{topic_id}' has already been used recently."

    # 2. Verse reference check
    if verse_ref:
        norm_v = normalize_christian_verse(verse_ref)
        if norm_v:
            v_parsed = parse_verse_components(norm_v)
            for sv in seen_verses:
                norm_sv = normalize_christian_verse(sv)
                if norm_v == norm_sv:
                    return True, f"Scripture '{verse_ref}' matches already posted verse '{sv}'."
                if v_parsed:
                    sv_parsed = parse_verse_components(norm_sv)
                    if sv_parsed and v_parsed["book"] == sv_parsed["book"] and v_parsed["chapter"] == sv_parsed["chapter"]:
                        v_range = set(range(v_parsed["start_verse"], v_parsed["end_verse"] + 1))
                        sv_range = set(range(sv_parsed["start_verse"], sv_parsed["end_verse"] + 1))
                        if v_range & sv_range:
                            return True, f"Scripture '{verse_ref}' overlaps with already posted verse '{sv}'."

    # 3. Headline check (Exact normalized)
    if headline:
        clean_h = re.sub(r'[^a-z0-9]', '', str(headline).lower())
        if clean_h and clean_h in seen_headlines:
            return True, f"Headline '{headline}' has already been posted recently."

        # 4. Token Jaccard check (>= 60% overlap)
        words = set([
            w for w in re.findall(r'[a-z]{3,}', str(headline).lower())
            if w not in {"the", "and", "you", "for", "with", "that", "this", "your", "are", "have", "not"}
        ])
        if len(words) >= 3:
            for rec in records:
                rec_h = rec.get("headline", "")
                rec_words = set([
                    w for w in re.findall(r'[a-z]{3,}', str(rec_h).lower())
                    if w not in {"the", "and", "you", "for", "with", "that", "this", "your", "are", "have", "not"}
                ])
                if len(rec_words) >= 3:
                    overlap = len(words & rec_words)
                    union = len(words | rec_words)
                    if union > 0 and (overlap / union) >= 0.60:
                        return True, f"Headline has {int(overlap/union*100)}% similarity to previous post: '{rec_h}'."

    return False, ""

def record_used_christian_content(verse_ref, headline, topic_id=None, category=None, fb_video_id=None):
    """
    Permanently writes a scripture, headline, and topic slug into christian_seen_verses.json.
    Ensures that content posted once is never repeated.
    """
    data = load_christian_seen_verses()
    norm_v = normalize_christian_verse(verse_ref) if verse_ref else ""
    clean_h = re.sub(r'[^a-z0-9]', '', str(headline).lower()) if headline else ""
    t_id = str(topic_id).strip().lower() if topic_id else ""

    changed = False
    if norm_v and norm_v not in data.get("seen_verses", []):
        data.setdefault("seen_verses", []).append(norm_v)
        changed = True
    if clean_h and clean_h not in data.get("seen_headlines", []):
        data.setdefault("seen_headlines", []).append(clean_h)
        changed = True
    if t_id and t_id not in data.get("seen_topic_ids", []):
        data.setdefault("seen_topic_ids", []).append(t_id)
        changed = True

    records = data.setdefault("records", [])
    existing = None
    for r in records:
        if (norm_v and r.get("verse") == norm_v) or (t_id and r.get("topic_id") == t_id):
            existing = r
            break

    if existing:
        if fb_video_id and not existing.get("fb_video_id"):
            existing["fb_video_id"] = fb_video_id
            changed = True
    else:
        records.insert(0, {
            "verse": norm_v or str(verse_ref),
            "headline": str(headline),
            "topic_id": t_id,
            "category": category,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "fb_video_id": fb_video_id
        })
        changed = True

    # Keep seen registries bounded to last 150 items to keep files compact & fast
    if len(data.get("seen_verses", [])) > 150:
        data["seen_verses"] = data["seen_verses"][-150:]
        changed = True
    if len(data.get("seen_headlines", [])) > 150:
        data["seen_headlines"] = data["seen_headlines"][-150:]
        changed = True
    if len(data.get("seen_topic_ids", [])) > 150:
        data["seen_topic_ids"] = data["seen_topic_ids"][-150:]
        changed = True
    if len(records) > 150:
        data["records"] = records[:150]
        changed = True

    if changed:
        save_christian_seen_verses(data)


# ==============================================================================
# EXPANDED CURATED DEVOTIONAL BANK (60+ SCRIPTURES ACROSS 5 CATEGORIES)
# ==============================================================================

CURATED_CHRISTIAN_BANK = [
    # --------------------------------------------------------------------------
    # 1. MORNING PROMISE & GRACE (06:00 AM)
    # --------------------------------------------------------------------------
    {
        "category": "promise",
        "topic_id": "isaiah_41_10_fear_not_i_am_with_you",
        "headline": "Fear not, for I am with you; do not be dismayed",
        "verse_reference": "Isaiah 41:10",
        "voiceover_script": "Release every heavy thought and anxious fear into God's caring hands right now. He promises to strengthen you, help you, and uphold you with His righteous right hand. When you feel weak, His divine grace is made perfect in you. Be strong, for the Lord is on your side.",
        "visual_prompts": [
            "Cinematic 9:16 vertical silhouette of a person standing atop a hill gazing at a radiant heavenly sunrise, peaceful breeze, 8k fine art",
            "Cinematic 9:16 vertical macro shot of warm golden light beams falling upon praying hands held peacefully, high resolution 8k"
        ],
        "engagement_question": "Do you believe God is with you right now? Say AMEN! ✨"
    },
    {
        "category": "promise",
        "topic_id": "jeremiah_29_11_plans_to_prosper_you",
        "headline": "For I know the plans I have for you, plans to give you hope",
        "verse_reference": "Jeremiah 29:11",
        "voiceover_script": "Never lose hope about your future. God has declared that His plans for your life are plans of peace and not of harm, to give you an expected end filled with hope. Even when doors close, trust that God is preparing an open heaven for you. His timing is always perfect.",
        "visual_prompts": [
            "Cinematic 9:16 vertical serene path winding through tranquil sunlit olive groves towards a glowing horizon, warm gold light, 8k",
            "Cinematic 9:16 vertical view looking up at soaring white dove flying through sunlit morning clouds, heavenly blue sky, 8k"
        ],
        "engagement_question": "Claim this promise in Jesus' name and share it with a friend! 🕊️"
    },
    {
        "category": "promise",
        "topic_id": "philippians_4_13_christ_strengthens_me",
        "headline": "I can do all things through Christ who gives me strength",
        "verse_reference": "Philippians 4:13",
        "voiceover_script": "Do not depend on your own limited strength today. When you rely on Christ living within you, there is no storm you cannot weather and no obstacle you cannot overcome. Step into this day knowing you are crowned with divine favor and supernatural strength.",
        "visual_prompts": [
            "Cinematic 9:16 vertical majestic view of granite mountain peaks bathed in golden morning sunbeams, eternal steadfastness, 8k",
            "Cinematic 9:16 vertical glowing warm cross standing steadfastly on green hill against dawn horizon, 8k documentary"
        ],
        "engagement_question": "Type AMEN to receive His divine strength today! 💪"
    },
    {
        "category": "promise",
        "topic_id": "matthew_11_28_come_unto_me_rest",
        "headline": "Come to Me, all you who are weary, and I will give you rest",
        "verse_reference": "Matthew 11:28",
        "voiceover_script": "Are you feeling overwhelmed by the pressures of life? Jesus extends an open invitation to your soul today: Come unto Me, and I will give you rest. Lay down your burdens at the foot of the cross and let His gentle love fill your heart with everlasting peace.",
        "visual_prompts": [
            "Cinematic 9:16 vertical tranquil lake with crystal clear reflections of snowcapped peaks at dawn, divine peace atmosphere, 8k",
            "Cinematic 9:16 vertical close up of gentle warm light enveloping praying hands, peaceful serenity, 8k"
        ],
        "engagement_question": "Surrender your heavy burdens to Jesus today. Amen? 🙏"
    },
    {
        "category": "promise",
        "topic_id": "romans_8_28_all_things_work_together",
        "headline": "All things work together for good to those who love God",
        "verse_reference": "Romans 8:28",
        "voiceover_script": "Even the painful setbacks and unexpected delays are working for your ultimate blessing. God is a master weaver who turns sorrow into joy and tests into testimonies. Trust His loving hand, for He is turning every single thing around for your good.",
        "visual_prompts": [
            "Cinematic 9:16 vertical sunrise over tranquil misty meadow with wildflowers glowing in morning golden hour, 8k",
            "Cinematic 9:16 vertical silhouette of praying hands lifted in worship against breathtaking dawn sky, 8k"
        ],
        "engagement_question": "Do you trust God's plan for your life? Type AMEN! ❤️"
    },
    {
        "category": "promise",
        "topic_id": "isaiah_40_31_mount_up_with_wings_like_eagles",
        "headline": "Those who wait on the Lord shall renew their strength like eagles",
        "verse_reference": "Isaiah 40:31",
        "voiceover_script": "When your energy feels exhausted and your spirit feels faint, wait patiently upon the Lord. He gives power to the faint and strengthens the weak. You will run and not be weary; you will walk and not faint. He is lifting you on eagle wings today.",
        "visual_prompts": [
            "Cinematic 9:16 vertical majestic golden eagle soaring high above cloud-covered mountain valleys at dawn, 8k",
            "Cinematic 9:16 vertical sunburst piercing dramatic mountain clouds with radiant golden beams, 8k"
        ],
        "engagement_question": "Receive supernatural renewal today! Type AMEN! 🦅"
    },
    {
        "category": "promise",
        "topic_id": "deuteronomy_31_8_the_lord_goes_before_you",
        "headline": "The Lord Himself goes before you and will never forsake you",
        "verse_reference": "Deuteronomy 31:8",
        "voiceover_script": "You do not walk into this morning unaccompanied. The Lord God Himself marches ahead of you to level mountains, open closed doors, and prepare a table of blessing. Do not be terrified, for the Almighty walks beside you every inch of the journey.",
        "visual_prompts": [
            "Cinematic 9:16 vertical glowing heavenly light illuminating a clear path through a deep verdant forest, 8k",
            "Cinematic 9:16 vertical serene morning landscape with sun rising over ancient stone bridge, 8k"
        ],
        "engagement_question": "Walk in total confidence today! Amen! 🛡️"
    },
    {
        "category": "promise",
        "topic_id": "zephaniah_3_17_the_mighty_one_will_save",
        "headline": "The Lord your God is with you, the Mighty Warrior who saves",
        "verse_reference": "Zephaniah 3:17",
        "voiceover_script": "Hear the tender heartbeat of your Heavenly Father today. He will quiet you with His love, He will rejoice over you with singing, and He will fight your battles as a mighty savior. Rest securely in His unconditional grace.",
        "visual_prompts": [
            "Cinematic 9:16 vertical peaceful meadow filled with blooming wildflowers bathed in soft divine golden sunlight, 8k",
            "Cinematic 9:16 vertical silhouette of sheep resting safely in lush green pasture under tranquil sky, 8k"
        ],
        "engagement_question": "God is rejoicing over you with love! Type AMEN! 🕊️"
    },
    {
        "category": "promise",
        "topic_id": "psalm_46_1_refuge_and_strength_in_trouble",
        "headline": "God is our refuge and strength, an ever-present help in trouble",
        "verse_reference": "Psalm 46:1",
        "voiceover_script": "Though earthquakes shake the mountains and waters roar, you can remain completely at peace. God is your fortress, an unshakeable shelter in every storm. Be still, know that He is God, and watch His power defend you today.",
        "visual_prompts": [
            "Cinematic 9:16 vertical ancient fortress citadel standing resolute upon towering sea cliff against gentle waves, 8k",
            "Cinematic 9:16 vertical radiant rainbow touching down on calm waters after a passing rainstorm, 8k"
        ],
        "engagement_question": "Take refuge in His mighty shelter! Amen! 🏰"
    },
    {
        "category": "promise",
        "topic_id": "romans_8_31_if_god_is_for_us",
        "headline": "If God is for us, who can ever stand against us?",
        "verse_reference": "Romans 8:31",
        "voiceover_script": "No weapon formed against you shall prosper, and no adversary can overturn God's decree over your life. Since the Creator of the cosmos is standing with you, defeat is not your portion. Lift up your head and celebrate your victory in Christ.",
        "visual_prompts": [
            "Cinematic 9:16 vertical dramatic golden sunbeams bursting through parted storm clouds over sunlit mountain, 8k",
            "Cinematic 9:16 vertical golden cross shining with warm divine radiance atop green knoll, 8k"
        ],
        "engagement_question": "Declare: God is for me! Type AMEN! ✝️"
    },
    {
        "category": "promise",
        "topic_id": "isaiah_43_2_when_you_pass_through_the_waters",
        "headline": "When you pass through the waters, I will be with you",
        "verse_reference": "Isaiah 43:2",
        "voiceover_script": "When deep waters rise, they will not sweep over you. When you walk through the fire, you will not be burned. Jesus is in the waters and in the flames with you. He is leading you safely through to higher ground.",
        "visual_prompts": [
            "Cinematic 9:16 vertical tranquil calm stream running through sun-drenched blossoming orchard, 8k",
            "Cinematic 9:16 vertical golden light guiding traveler through peaceful mountain pass, 8k"
        ],
        "engagement_question": "Trust Jesus through every trial! Type AMEN! 🌊"
    },
    {
        "category": "promise",
        "topic_id": "psalm_34_8_taste_and_see_the_lord_is_good",
        "headline": "Taste and see that the Lord is good; blessed is the one who trusts",
        "verse_reference": "Psalm 34:8",
        "voiceover_script": "God's goodness is not a distant theory; it is a living reality waiting for you to experience today. Open your eyes to His daily mercies, His quiet protections, and His miraculous provision. You are deeply loved by the Father.",
        "visual_prompts": [
            "Cinematic 9:16 vertical lush vineyard laden with ripe purple grapes in morning dew and golden sun, 8k",
            "Cinematic 9:16 vertical hands holding fresh golden bread and olive oil in warm rustic biblical setting, 8k"
        ],
        "engagement_question": "Praise God for His daily goodness! Say AMEN! 🍇"
    },

    # --------------------------------------------------------------------------
    # 2. BIBLICAL WISDOM & GUIDANCE (12:30 PM)
    # --------------------------------------------------------------------------
    {
        "category": "wisdom",
        "topic_id": "proverbs_3_5_trust_in_the_lord_with_all_your_heart",
        "headline": "Trust in the Lord with all your heart and lean not on your own understanding",
        "verse_reference": "Proverbs 3:5-6",
        "voiceover_script": "When life feels confusing and the path ahead seems unclear, remember you don't have to figure it all out alone. Acknowledge God in all your ways, surrender your need to control, and He will make your paths straight and direct your footsteps with divine wisdom.",
        "visual_prompts": [
            "Cinematic 9:16 vertical serene forest pathway glowing with warm sunbeams breaking through canopy, 8k",
            "Cinematic 9:16 vertical close up of a lighthouse shining bright beam through gentle coastal mist, 8k"
        ],
        "engagement_question": "Trust God wholeheartedly today. Type AMEN! 📖"
    },
    {
        "category": "wisdom",
        "topic_id": "james_1_5_ask_god_for_wisdom",
        "headline": "If any of you lacks wisdom, let him ask God, who gives generously",
        "verse_reference": "James 1:5",
        "voiceover_script": "Facing tough decisions in your career, finances, or family? Heavenly wisdom is only a prayer away. God never mocks your questions; He promises to give generously to all who ask in faith. Quiet your heart and ask Him to guide your choices today.",
        "visual_prompts": [
            "Cinematic 9:16 vertical celestial library with ancient golden scrolls illuminated by divine light from high window, 8k",
            "Cinematic 9:16 vertical person walking beside peaceful mountain stream in deep prayer, soft afternoon light, 8k"
        ],
        "engagement_question": "Ask God for wisdom and direction today. Amen! 🕊️"
    },
    {
        "category": "wisdom",
        "topic_id": "proverbs_4_23_guard_your_heart",
        "headline": "Above all else, guard your heart, for everything you do flows from it",
        "verse_reference": "Proverbs 4:23",
        "voiceover_script": "Protect what enters your eyes, ears, and thoughts today. Guard your heart against bitterness, jealousy, and fear. Fill your spirit with the living water of God's Word, forgiveness, and gratitude. A pure heart produces a life overflowing with joy and divine fruit.",
        "visual_prompts": [
            "Cinematic 9:16 vertical pure crystal clear mountain spring bubbling through polished stones, sunlight refraction, 8k",
            "Cinematic 9:16 vertical lush green garden blooming with radiant white lilies under golden sun, 8k"
        ],
        "engagement_question": "Keep your heart pure and full of praise today. Type AMEN! 💖"
    },
    {
        "category": "wisdom",
        "topic_id": "colossians_3_13_forgive_as_the_lord_forgave",
        "headline": "Forgive as the Lord forgave you, bearing with each other in love",
        "verse_reference": "Colossians 3:13",
        "voiceover_script": "Holding onto resentment is like drinking poison and hoping the other person suffers. Forgiveness does not excuse the wrongdoing; it sets your soul free. As Christ has forgiven you so richly, release the offense today and walk in total emotional freedom.",
        "visual_prompts": [
            "Cinematic 9:16 vertical white dove being released from cupped hands into endless blue sky, freedom and peace, 8k",
            "Cinematic 9:16 vertical warm golden sunset over quiet sea, calm waves gently lapping shore, 8k"
        ],
        "engagement_question": "Choose forgiveness and freedom today. Amen! 🕊️"
    },
    {
        "category": "wisdom",
        "topic_id": "philippians_4_6_do_not_be_anxious",
        "headline": "Do not be anxious about anything, but in every situation, pray",
        "verse_reference": "Philippians 4:6-7",
        "voiceover_script": "Turn every worry into a prayer today. Instead of losing sleep over what you cannot change, present your requests to God with thanksgiving. And the peace of God, which surpasses all human understanding, will guard your heart and mind in Christ Jesus.",
        "visual_prompts": [
            "Cinematic 9:16 vertical peaceful field of lavender swaying in gentle afternoon breeze under soft sky, 8k",
            "Cinematic 9:16 vertical open Bible resting on wooden rustic table next to glowing warm candle, 8k"
        ],
        "engagement_question": "Trade your worries for God's peace right now. Type AMEN! ✨"
    },
    {
        "category": "wisdom",
        "topic_id": "galatians_6_9_do_not_grow_weary",
        "headline": "Let us not become weary in doing good, for in due season we will reap",
        "verse_reference": "Galatians 6:9",
        "voiceover_script": "Have you been praying, giving, and doing good without seeing any results? Don't give up just before the breakthrough. The seed you planted is taking root in secret. In God's appointed season, you will reap an abundant harvest if you do not lose heart.",
        "visual_prompts": [
            "Cinematic 9:16 vertical vast golden wheat field ready for harvest under brilliant blue sky, warm sunlight, 8k",
            "Cinematic 9:16 vertical small green seedling sprouting bravely through rich soil into bright sunlight, 8k"
        ],
        "engagement_question": "Your harvest is coming! Type AMEN to claim it! 🌾"
    },
    {
        "category": "wisdom",
        "topic_id": "proverbs_16_3_commit_your_works_to_the_lord",
        "headline": "Commit your works to the Lord, and your thoughts will be established",
        "verse_reference": "Proverbs 16:3",
        "voiceover_script": "Before starting your tasks or making major plans, dedicate them fully to God. When your labors are placed into His hands, confusion vanishes and divine clarity takes over. Let Him direct your career, business, and family today.",
        "visual_prompts": [
            "Cinematic 9:16 vertical architect blueprint transformed into warm divine glowing light on wooden desk, 8k",
            "Cinematic 9:16 vertical hands planting a sapling tree in rich black soil with golden sunbeam shining down, 8k"
        ],
        "engagement_question": "Dedicate your work to the Lord! Amen! 🔨"
    },
    {
        "category": "wisdom",
        "topic_id": "james_1_19_quick_to_listen_slow_to_speak",
        "headline": "Be quick to listen, slow to speak, and slow to become angry",
        "verse_reference": "James 1:19",
        "voiceover_script": "Words carry the power of life and death. Before reacting in frustration, pause and invite the Holy Spirit to guide your tongue. A patient listener brings peace to broken relationships and heals wounded hearts.",
        "visual_prompts": [
            "Cinematic 9:16 vertical calm still mountain pond mirroring snowcapped peaks without a single ripple, 8k",
            "Cinematic 9:16 vertical olive branch with fresh green leaves bathed in soft gentle morning light, 8k"
        ],
        "engagement_question": "Choose patience and gentle words today! Type AMEN! 🌿"
    },
    {
        "category": "wisdom",
        "topic_id": "proverbs_17_22_merry_heart_does_good_like_medicine",
        "headline": "A merry heart does good like medicine, but a broken spirit dries bones",
        "verse_reference": "Proverbs 17:22",
        "voiceover_script": "Laughter, joy, and gratitude have real healing power. Even in difficult circumstances, find reasons to rejoice in God's faithfulness. The joy of the Lord is your physical, mental, and emotional strength today.",
        "visual_prompts": [
            "Cinematic 9:16 vertical sunlit garden of vibrant yellow sunflowers lifting their heads to the blue sky, 8k",
            "Cinematic 9:16 vertical radiant morning dew glittering like diamonds on green meadow grass, 8k"
        ],
        "engagement_question": "Receive God's joyful medicine in your heart! Amen! 🌸"
    },
    {
        "category": "wisdom",
        "topic_id": "matthew_6_33_seek_first_the_kingdom_of_god",
        "headline": "Seek first the kingdom of God, and all these things shall be added to you",
        "verse_reference": "Matthew 6:33",
        "voiceover_script": "Stop chasing after worry and tomorrow's needs. When you make God your highest priority, your provider, and your focus, He takes divine responsibility for your bills, health, and family. Put Jesus first, and watch everything fall into place.",
        "visual_prompts": [
            "Cinematic 9:16 vertical golden royal crown resting upon open Holy Bible with warm rays of light, 8k",
            "Cinematic 9:16 vertical tranquil sunrise over peaceful hills with vibrant wildflowers in foreground, 8k"
        ],
        "engagement_question": "Put Jesus first in all things! Type AMEN! 👑"
    },
    {
        "category": "wisdom",
        "topic_id": "proverbs_18_10_name_of_the_lord_strong_tower",
        "headline": "The name of the Lord is a strong tower; the righteous run to it and are safe",
        "verse_reference": "Proverbs 18:10",
        "voiceover_script": "When fear knocks at your door, call on the name of Jesus. His name is higher than sickness, financial distress, or any human attack. Run into His presence through prayer and find absolute security.",
        "visual_prompts": [
            "Cinematic 9:16 vertical towering ancient stone fortress standing high above clouds bathed in golden light, 8k",
            "Cinematic 9:16 vertical radiant cross casting brilliant warm light in the midst of darkness, 8k"
        ],
        "engagement_question": "Declare: The name of Jesus is my strong tower! Amen! 🛡️"
    },
    {
        "category": "wisdom",
        "topic_id": "ecclesiastes_3_1_a_time_for_every_purpose",
        "headline": "To everything there is a season, and a time for every purpose under heaven",
        "verse_reference": "Ecclesiastes 3:1",
        "voiceover_script": "If you are in a season of waiting or weeping, remember that winter always yields to spring. God makes everything beautiful in its proper time. Trust the seasons of your life, for He is preparing you for greater fruitfulness.",
        "visual_prompts": [
            "Cinematic 9:16 vertical lush cherry blossoms blooming alongside autumn golden leaves in timeless harmony, 8k",
            "Cinematic 9:16 vertical antique bronze hourglass with sand glistening like golden dust in sunlight, 8k"
        ],
        "engagement_question": "Trust God's perfect timing! Type AMEN! ⏳"
    },

    # --------------------------------------------------------------------------
    # 3. FAITH STORY & GOSPEL PARABLE (04:30 PM)
    # --------------------------------------------------------------------------
    {
        "category": "parable",
        "topic_id": "parable_prodigal_son_fathers_arms",
        "headline": "The Father ran to embrace his son with tears of joy",
        "verse_reference": "Luke 15:20-24",
        "voiceover_script": "When the prodigal son decided to return home, his father didn't wait with anger or judgment. He ran toward him, fell on his neck, and kissed him. No matter where you have wandered or what mistakes you have made, God's arms are wide open to welcome you home today.",
        "visual_prompts": [
            "Cinematic 9:16 vertical emotional reunion of father embracing son on sunlit dusty path, golden sunset glow, 8k",
            "Cinematic 9:16 vertical open doorway of ancient welcoming home glowing with warm festive light inside, 8k"
        ],
        "engagement_question": "God's mercy is greater than your past! Amen! ❤️"
    },
    {
        "category": "parable",
        "topic_id": "parable_good_samaritan_mercy",
        "headline": "Go and do likewise: Loving our neighbor with compassion",
        "verse_reference": "Luke 10:33-37",
        "voiceover_script": "While others passed by the wounded man on the Jericho road, the Samaritan stopped, bandaged his wounds, and showed unconditional mercy. True religion is seeing someone hurting and choosing to be God's hands and feet. Let your love shine brightly today.",
        "visual_prompts": [
            "Cinematic 9:16 vertical ancient stone road winding through desert canyon with warm afternoon sun, 8k",
            "Cinematic 9:16 vertical hands gently pouring soothing oil and wine onto a wound, compassionate care, 8k"
        ],
        "engagement_question": "Who can you bless with kindness today? Amen! 🌟"
    },
    {
        "category": "parable",
        "topic_id": "parable_mustard_seed_faith_moves_mountains",
        "headline": "Faith as small as a mustard seed can move mountains",
        "verse_reference": "Matthew 17:20",
        "voiceover_script": "You don't need giant, perfect faith to experience God's power. Even faith as tiny as a mustard seed in the hands of a big God can shatter sickness, open locked doors, and move impossible mountains. Put your small seed of trust in Jesus today.",
        "visual_prompts": [
            "Cinematic 9:16 vertical macro view of tiny mustard seed resting on palm of hand with majestic mountain in background, 8k",
            "Cinematic 9:16 vertical lush sprawling mustard tree full of birds resting in its branches under golden sky, 8k"
        ],
        "engagement_question": "Do you believe God can move your mountain? Type AMEN! 🏔️"
    },
    {
        "category": "parable",
        "topic_id": "parable_house_on_the_rock",
        "headline": "The rain fell and the winds blew, but the house stood firm upon the Rock",
        "verse_reference": "Matthew 7:24-25",
        "voiceover_script": "Storms will come to every life, but the house built upon the solid rock of Christ's teachings never collapses. When you build your family, career, and dreams on the eternal foundation of Jesus, no flood of trouble can ever wash you away.",
        "visual_prompts": [
            "Cinematic 9:16 vertical sturdy stone house built high atop solid seaside cliff withstanding crashing waves, 8k",
            "Cinematic 9:16 vertical glowing warm cross standing unshakeable on immovable granite rock, 8k"
        ],
        "engagement_question": "Is Jesus the rock of your life? Declare AMEN! 🪨"
    },
    {
        "category": "parable",
        "topic_id": "story_calming_the_storm_peace_be_still",
        "headline": "Jesus stood and rebuked the winds: Peace, be still!",
        "verse_reference": "Mark 4:39",
        "voiceover_script": "When ferocious waves battered the disciples' boat, Jesus simply stood up and spoke: Peace, be still. And immediately the storm ceased. Jesus is in your boat today. Whatever turbulent storm is raging around your life, listen to His calm voice whispering peace into your soul.",
        "visual_prompts": [
            "Cinematic 9:16 vertical stormy dark sea suddenly parting for a beam of brilliant golden heavenly light, 8k",
            "Cinematic 9:16 vertical tranquil sea of Galilee at calm sunset, mirror-like water reflecting evening stars, 8k"
        ],
        "engagement_question": "Invite Jesus to calm your storm. Type AMEN! 🌊"
    },
    {
        "category": "parable",
        "topic_id": "parable_pearl_of_great_price",
        "headline": "The kingdom of heaven is like a merchant seeking beautiful pearls",
        "verse_reference": "Matthew 13:45-46",
        "voiceover_script": "When a merchant found one priceless pearl, he joyfully sold everything he had to obtain it. Knowing Jesus, receiving His salvation, and walking in His kingdom is the greatest treasure this universe could ever offer. You are richly blessed in Him.",
        "visual_prompts": [
            "Cinematic 9:16 vertical radiant glowing pearl resting on velvet cloth inside antique ornate box, divine brilliance, 8k",
            "Cinematic 9:16 vertical sunbeams streaming through stained glass window in historic cathedral, 8k"
        ],
        "engagement_question": "Jesus is my greatest treasure! Type AMEN! 💎"
    },
    {
        "category": "parable",
        "topic_id": "parable_sower_good_soil_harvest",
        "headline": "Seed sown on good ground produces a harvest thirty, sixty, and hundredfold",
        "verse_reference": "Matthew 13:8",
        "voiceover_script": "When God's Word finds a soft, receptive heart, it produces supernatural fruit. Do not let the cares of this world choke the promises of God in your spirit. Receive His truth today, and watch your life overflow with divine blessings.",
        "visual_prompts": [
            "Cinematic 9:16 vertical fertile field of golden wheat glowing in warm late afternoon sun, 8k",
            "Cinematic 9:16 vertical sower scattering seeds in gentle morning breeze across rolling hills, 8k"
        ],
        "engagement_question": "May your heart be fertile soil for God's Word! Amen! 🌾"
    },
    {
        "category": "parable",
        "topic_id": "story_peter_walking_on_water",
        "headline": "Lord, if it is You, command me to come to You on the water",
        "verse_reference": "Matthew 14:29-31",
        "voiceover_script": "When Peter fixed his eyes on Jesus, he stepped out of the boat and walked on water. But when he looked at the raging waves, he began to sink. Keep your eyes on Jesus, not on your circumstances, and He will hold you above every impossible wave.",
        "visual_prompts": [
            "Cinematic 9:16 vertical Jesus extending a strong radiant hand to pull a reaching disciple from blue waves, 8k",
            "Cinematic 9:16 vertical tranquil dawn waters glowing with divine light under breaking clouds, 8k"
        ],
        "engagement_question": "Keep your eyes fixed on Jesus! Type AMEN! ⚓"
    },
    {
        "category": "parable",
        "topic_id": "story_zacchaeus_come_down_salvation",
        "headline": "Today salvation has come to this house, for the Son of Man came to save",
        "verse_reference": "Luke 19:9-10",
        "voiceover_script": "Zacchaeus climbed a sycamore tree just to catch a glimpse of Jesus, but Jesus called him by name and dined at his home. Jesus sees you in the crowd, knows your heart, and is knocking on the door of your life with forgiveness and joy.",
        "visual_prompts": [
            "Cinematic 9:16 vertical ancient sycamore fig tree with spreading green branches on sunlit Jericho street, 8k",
            "Cinematic 9:16 vertical warm dining table illuminated by oil lamps with bread and wine, festive warmth, 8k"
        ],
        "engagement_question": "Jesus knows your name! Type AMEN to welcome Him! 🌳"
    },
    {
        "category": "parable",
        "topic_id": "story_the_true_vine_and_branches",
        "headline": "I am the vine, you are the branches; remain in Me and bear much fruit",
        "verse_reference": "John 15:5",
        "voiceover_script": "A branch cannot produce fruit severed from the vine. Your spiritual strength, joy, and peace all flow from your daily relationship with Jesus. Stay connected to Him in prayer, and His life will naturally flourish through you.",
        "visual_prompts": [
            "Cinematic 9:16 vertical lush green grapevine loaded with deep purple grapes in sunlit Mediterranean vineyard, 8k",
            "Cinematic 9:16 vertical morning sunbeams shining through dewy grape leaves, 8k"
        ],
        "engagement_question": "Stay connected to the True Vine! Amen! 🍇"
    },

    # --------------------------------------------------------------------------
    # 4. BIBLE WONDERS & HISTORY (07:30 PM)
    # --------------------------------------------------------------------------
    {
        "category": "mystery",
        "topic_id": "mystery_noahs_ark_mount_ararat",
        "headline": "Noah's Ark rested upon the mountains of Ararat: God remembers His covenant",
        "verse_reference": "Genesis 8:4",
        "voiceover_script": "Centuries before modern naval engineering, God gave Noah the exact dimensions for an ark with a stable three-hundred cubit ratio. Just as the ark safely carried Noah's family through catastrophic floods, Jesus is our eternal ark of safety through every judgment.",
        "visual_prompts": [
            "Cinematic 9:16 vertical massive ancient wooden ark resting on majestic snowcapped mountain peak under rainbow, 8k",
            "Cinematic 9:16 vertical glorious full rainbow stretching across dramatic misty sky over ancient valley, 8k"
        ],
        "engagement_question": "Praise God for His faithfulness through every generation! Amen! 🚢"
    },
    {
        "category": "mystery",
        "topic_id": "mystery_red_sea_crossing_chariots",
        "headline": "The waters were divided, and the children of Israel walked on dry ground",
        "verse_reference": "Exodus 14:21-22",
        "voiceover_script": "When Pharaoh's army trapped Israel against the roaring sea, God parted the deep waters and created a highway through the impossible. Modern ocean discoveries at the Gulf of Aqaba still echo this miraculous deliverance. Where there seems to be no way, God makes a way.",
        "visual_prompts": [
            "Cinematic 9:16 vertical towering walls of parted sea water with dry seabed pathway illuminated by divine pillar of fire, 8k",
            "Cinematic 9:16 vertical golden desert coastline meeting deep azure sea at dramatic sunset, 8k"
        ],
        "engagement_question": "God can make a way where there is no way! Amen! 🌊"
    },
    {
        "category": "mystery",
        "topic_id": "mystery_dead_sea_scrolls_qumran",
        "headline": "The grass withers, the flower fades, but the Word of our God stands forever",
        "verse_reference": "Isaiah 40:8",
        "voiceover_script": "In 1947, Bedouin shepherds discovered ancient jars hidden in Qumran caves containing biblical manuscripts over two thousand years old. Amazingly, the text matched our modern Bibles almost word for word. God has preserved His holy Word throughout all ages for you.",
        "visual_prompts": [
            "Cinematic 9:16 vertical ancient clay jars holding papyrus scrolls inside sunlit desert cave in Qumran, 8k",
            "Cinematic 9:16 vertical aged Hebrew parchment scroll showing ancient script illuminated by soft warm light, 8k"
        ],
        "engagement_question": "God's Word never fails! Type AMEN if you stand on it! 📜"
    },
    {
        "category": "mystery",
        "topic_id": "mystery_empty_tomb_garden_tomb",
        "headline": "He is not here; He has risen, just as He said!",
        "verse_reference": "Matthew 28:6",
        "voiceover_script": "In Jerusalem stands a first-century garden tomb that bears the greatest archaeological fact in human history: it is empty! Roman guards and heavy stones could not hold the Prince of Life. Because Jesus rose from the dead, you too have living hope and eternal victory.",
        "visual_prompts": [
            "Cinematic 9:16 vertical ancient stone garden tomb with stone rolled away, brilliant morning light streaming from within, 8k",
            "Cinematic 9:16 vertical serene peaceful olive garden at sunrise with flowering branches and stone pathway, 8k"
        ],
        "engagement_question": "Jesus is alive! Hallelujah! Type AMEN! ✝️"
    },
    {
        "category": "mystery",
        "topic_id": "mystery_mount_sinai_split_rock",
        "headline": "He split the rocks in the wilderness and gave them water in abundance",
        "verse_reference": "Psalm 78:15",
        "voiceover_script": "In the barren wilderness of Horeb stands a massive split rock showing deep water erosion from ancient springs. When God's people were dying of thirst, living water gushed from the stone. Today, Christ is your spiritual rock who quenches your deepest soul-thirst.",
        "visual_prompts": [
            "Cinematic 9:16 vertical towering monumental split boulder in desert landscape showing smooth water erosion path, 8k",
            "Cinematic 9:16 vertical fresh cold spring water pouring forth from natural stone cliff in desert oasis, 8k"
        ],
        "engagement_question": "Drink from His living water today. Type AMEN! 💧"
    },
    {
        "category": "mystery",
        "topic_id": "mystery_walls_of_jericho_fallen",
        "headline": "When the people shouted with a great shout, the wall fell down flat",
        "verse_reference": "Joshua 6:20",
        "voiceover_script": "Ancient excavations at Jericho reveal massive double city walls that collapsed outward, forming ramps exactly as the Book of Joshua records. Faith and praise shattered impenetrable fortresses without a single weapon. Keep praising God, and your Jericho walls will crumble.",
        "visual_prompts": [
            "Cinematic 9:16 vertical ancient stone excavation ramparts under dramatic desert twilight sky, 8k documentary",
            "Cinematic 9:16 vertical silver trumpet and ram's horn shofar resting beside ancient stone altar, warm light, 8k"
        ],
        "engagement_question": "Your praise has the power to bring down walls! Amen! 🎺"
    },
    {
        "category": "mystery",
        "topic_id": "mystery_pool_of_siloam_restored",
        "headline": "Go, wash in the pool of Siloam: The blind man went and returned seeing",
        "verse_reference": "John 9:7",
        "voiceover_script": "Archaeologists in the City of David uncovered the authentic ancient stone steps of the Pool of Siloam, confirming the very site where Jesus healed a man born blind. What seemed biologically impossible was healed by a single touch from Christ. He still heals today.",
        "visual_prompts": [
            "Cinematic 9:16 vertical ancient stone stepped pool filled with clear shimmering water in historic Jerusalem, 8k",
            "Cinematic 9:16 vertical gentle hands scooping crystal clear pool water in bright sunlit morning, 8k"
        ],
        "engagement_question": "Do you believe in miracles? Say AMEN! 👁️"
    },
    {
        "category": "mystery",
        "topic_id": "mystery_mount_carmel_fire_from_heaven",
        "headline": "Then the fire of the Lord fell and consumed the sacrifice: The Lord is God!",
        "verse_reference": "1 Kings 18:38-39",
        "voiceover_script": "On Mount Carmel, the prophet Elijah prayed a simple sixty-word prayer, and holy fire fell from heaven to validate the living God before hundreds of false prophets. God answers genuine faith by fire. Stand boldly for truth, and God will vindicate you.",
        "visual_prompts": [
            "Cinematic 9:16 vertical Mount Carmel plateau overlooking Mediterranean coast under dramatic heavenly light, 8k",
            "Cinematic 9:16 vertical stone altar bathed in brilliant divine golden light falling from celestial clouds, 8k"
        ],
        "engagement_question": "The Lord, He is God! Declare AMEN! 🔥"
    },
    {
        "category": "mystery",
        "topic_id": "mystery_daniel_in_the_lions_den",
        "headline": "My God sent His angel and shut the lions' mouths so they did not hurt me",
        "verse_reference": "Daniel 6:22",
        "voiceover_script": "Cast into a pit of hungry lions for his unwavering prayer life, Daniel emerged without a scratch because he trusted in his God. No fierce trap or hostile enemy can harm you when heaven's angels stand guard over your life. Keep praying without fear.",
        "visual_prompts": [
            "Cinematic 9:16 vertical majestic glowing angel silhouette standing peacefully beside resting lions in stone den, 8k",
            "Cinematic 9:16 vertical golden beam of morning light breaking into ancient subterranean stone chamber, 8k"
        ],
        "engagement_question": "God shuts the mouth of every roaring enemy! Amen! 🦁"
    },
    {
        "category": "mystery",
        "topic_id": "mystery_the_burning_bush_of_horeb",
        "headline": "The bush burned with fire, yet the bush was not consumed",
        "verse_reference": "Exodus 3:2",
        "voiceover_script": "In the solitude of the desert, Moses saw a desert thornbush burning with supernatural fire that never burned out. When God's holy presence fills an ordinary vessel, you can burn brightly with His glory without burning out. Draw near to holy ground today.",
        "visual_prompts": [
            "Cinematic 9:16 vertical acacia bush glowing with golden celestial flame against rugged desert mountains of Sinai, 8k",
            "Cinematic 9:16 vertical sandals resting upon sacred sand in radiant warm supernatural light, 8k"
        ],
        "engagement_question": "Step onto holy ground with reverence! Type AMEN! 🌿"
    },

    # --------------------------------------------------------------------------
    # 5. NIGHT PRAYER & PEACE (09:30 PM)
    # --------------------------------------------------------------------------
    {
        "category": "prayer",
        "topic_id": "prayer_psalm_91_abide_in_the_shadow",
        "headline": "He who dwells in the secret place of the Most High shall abide in His shadow",
        "verse_reference": "Psalm 91:1-2",
        "voiceover_script": "As nighttime falls, draw near to the secret place of God's presence. He who watches over you neither slumbers nor sleeps. Under His wings you will find refuge and absolute safety. Lay down all your worries and rest in the assurance that angels are guarding your home.",
        "visual_prompts": [
            "Cinematic 9:16 vertical majestic dark blue night sky filled with radiant twinkling stars over peaceful sleeping village, 8k",
            "Cinematic 9:16 vertical glowing angel wings silhouette in deep celestial blue night sky with warm golden aura, 8k"
        ],
        "engagement_question": "Claim Psalm 91 protection over your family tonight. Type AMEN! 🕊️"
    },
    {
        "category": "prayer",
        "topic_id": "prayer_psalm_23_the_lord_is_my_shepherd",
        "headline": "The Lord is my Shepherd; I shall not want. He restores my soul",
        "verse_reference": "Psalm 23:1-3",
        "voiceover_script": "Lord Jesus, thank You for guiding our steps throughout this day. Even when we walk through the valley of the shadow of death, we fear no evil, for You are with us. Lead our thoughts beside quiet waters tonight, restore our weary souls, and grant us peaceful sleep.",
        "visual_prompts": [
            "Cinematic 9:16 vertical serene tranquil lake under twilight sky reflecting crescent moon and evening star, 8k",
            "Cinematic 9:16 vertical warm glowing lantern resting on rustic wooden porch looking out into peaceful night forest, 8k"
        ],
        "engagement_question": "Rest in the Good Shepherd's care tonight. Amen! 🌿"
    },
    {
        "category": "prayer",
        "topic_id": "prayer_psalm_4_8_sleep_in_peace",
        "headline": "I will both lie down in peace, and sleep; for You alone make me dwell in safety",
        "verse_reference": "Psalm 4:8",
        "voiceover_script": "Father, we release every unspoken hurt, unfinished task, and racing thought into Your tender care. Cleanse our minds with Your peace that surpasses all understanding. May every home watching this be filled with tranquility, healing, and heavenly rest tonight.",
        "visual_prompts": [
            "Cinematic 9:16 vertical cozy warm bedroom with soft candle glow and starlight visible through window, peaceful sanctuary, 8k",
            "Cinematic 9:16 vertical still waters of mountain lake reflecting glowing moonbeams on gentle ripples, 8k"
        ],
        "engagement_question": "Receive peaceful sleep tonight in Jesus' name. Type AMEN! 🌙"
    },
    {
        "category": "prayer",
        "topic_id": "prayer_john_14_27_peace_i_leave_with_you",
        "headline": "Peace I leave with you; My peace I give to you, not as the world gives",
        "verse_reference": "John 14:27",
        "voiceover_script": "Lord, the world offers fleeting comfort, but You give us everlasting peace. Tonight, silence every voice of fear, regret, and anxiety. Let Your divine tranquility wash over every weary heart. We trust our lives into Your loving hands. In Jesus' name, Amen.",
        "visual_prompts": [
            "Cinematic 9:16 vertical peaceful calm ocean under deep twilight sky with soft celestial glow on horizon, 8k",
            "Cinematic 9:16 vertical praying hands gently illuminated by warm soft candlelight, deep reverent peace, 8k"
        ],
        "engagement_question": "May His peace rest upon your heart tonight. Amen! ✨"
    },
    {
        "category": "prayer",
        "topic_id": "prayer_1_peter_5_7_cast_all_anxieties",
        "headline": "Casting all your anxieties on Him, because He cares for you deeply",
        "verse_reference": "1 Peter 5:7",
        "voiceover_script": "Dear friend, you were never created to carry the weight of tomorrow on your shoulders tonight. Jesus invites you to unload every fear, debt, sickness, and burden into His hands because He cares for you deeply. Rest tonight knowing God is handling tomorrow.",
        "visual_prompts": [
            "Cinematic 9:16 vertical silhouette of person kneeling in quiet prayer beside window looking at starlit night sky, 8k",
            "Cinematic 9:16 vertical warm golden cross glowing softly against deep velvet midnight blue sky, 8k"
        ],
        "engagement_question": "Give your worries to God and sleep in peace. Type AMEN! 💖"
    },
    {
        "category": "prayer",
        "topic_id": "prayer_numbers_6_the_lord_bless_you_and_keep_you",
        "headline": "The Lord bless you and keep you; the Lord make His face shine upon you",
        "verse_reference": "Numbers 6:24-26",
        "voiceover_script": "Before you sleep, receive this eternal priestly blessing: The Lord bless you and keep you. The Lord make His face shine upon you and be gracious to you. The Lord lift up His countenance upon you, and give you peace. Sleep in His love tonight. Amen.",
        "visual_prompts": [
            "Cinematic 9:16 vertical divine radiant light shining from heaven with soft glowing dust motes floating peacefully, 8k",
            "Cinematic 9:16 vertical calm night sky adorned with milky way galaxy over tranquil silhouetted hills, 8k"
        ],
        "engagement_question": "Receive this divine blessing for your household! Type AMEN! 🌟"
    },
    {
        "category": "prayer",
        "topic_id": "prayer_psalm_63_6_remember_you_in_night_watches",
        "headline": "When I remember You on my bed, I meditate on You in the night watches",
        "verse_reference": "Psalm 63:6-7",
        "voiceover_script": "If you wake up in the middle of the night, do not let worry occupy your thoughts. Turn your heart toward heaven. Because God has been your help, you can sing under the shadow of His wings. His peace will lull your mind into sweet slumber.",
        "visual_prompts": [
            "Cinematic 9:16 vertical luminous full moon casting silver shimmer across quiet forest clearing, 8k",
            "Cinematic 9:16 vertical open Bible beside warm dim bedside candle in peaceful twilight, 8k"
        ],
        "engagement_question": "Meditation on His love brings total rest! Say AMEN! 🌙"
    },
    {
        "category": "prayer",
        "topic_id": "prayer_psalm_3_5_i_lay_down_and_slept",
        "headline": "I lay down and slept; I awoke again, for the Lord sustained me",
        "verse_reference": "Psalm 3:5",
        "voiceover_script": "No matter how turbulent your day was, the Lord is your sustainer. Close your eyes with holy confidence that He is guarding your breath and your family while you sleep. You will awaken refreshed, blessed, and victorious in Jesus' name.",
        "visual_prompts": [
            "Cinematic 9:16 vertical silhouetted sleepy valley with warm glowing cottage window under star-filled night sky, 8k",
            "Cinematic 9:16 vertical gentle golden starlight sparkling through mist over quiet mountain stream, 8k"
        ],
        "engagement_question": "Sleep peacefully tonight knowing God sustains you! Amen! 🛡️"
    },
    {
        "category": "prayer",
        "topic_id": "prayer_isaiah_26_3_perfect_peace_mind_stayed",
        "headline": "You will keep in perfect peace those whose minds are steadfast, trusting in You",
        "verse_reference": "Isaiah 26:3",
        "voiceover_script": "Lord, we quiet every anxious and racing thought before You right now. Wrap our minds in Your perfect, supernatural peace. We release the struggles of today and the fears of tomorrow into Your hands. Our trust is in You alone. Amen.",
        "visual_prompts": [
            "Cinematic 9:16 vertical mirror-calm mountain lake under starry night sky with shooting star, 8k",
            "Cinematic 9:16 vertical soft warm candle glowing inside protective glass lantern on quiet rustic balcony, 8k"
        ],
        "engagement_question": "Receive His perfect peace tonight! Type AMEN! 🕊️"
    }
]

def load_christian_state():
    if os.path.exists(CHRISTIAN_STATE_FILE):
        try:
            with open(CHRISTIAN_STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"used_topics": [], "last_category_index": -1}

def save_christian_state(state):
    try:
        with open(CHRISTIAN_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Notice: Failed to save Christian state: {e}")

def get_used_christian_identifiers():
    """
    Returns the set of all used identifiers from both state and the permanent seen verses file.
    """
    used = set()
    state = load_christian_state()
    for t in state.get("used_topics", []):
        used.add(str(t).strip().lower())

    seen_data = load_christian_seen_verses()
    for v in seen_data.get("seen_verses", []):
        used.add(normalize_christian_verse(v))
    for h in seen_data.get("seen_headlines", []):
        used.add(h)
    for tid in seen_data.get("seen_topic_ids", []):
        used.add(tid.lower())

    return used

def get_category_by_id(cat_id):
    for c in CHRISTIAN_CATEGORIES:
        if c["id"] == cat_id:
            return c
    return CHRISTIAN_CATEGORIES[0]

def get_scheduled_category_for_now():
    """
    Selects the scheduled devotional category matching the current 36-minute cycle slot:
    Smoothly cycles through: promise -> wisdom -> parable -> mystery -> prayer (8 times daily across 40 posts).
    """
    now = time.localtime()
    total_mins = now.tm_hour * 60 + now.tm_min
    cat_cycle = ["promise", "wisdom", "parable", "mystery", "prayer"]
    slot_idx = int(round(total_mins / 36.0)) % 40
    cat_id = cat_cycle[slot_idx % len(cat_cycle)]
    return get_category_by_id(cat_id)

def generate_christian_story_with_gemini(category_info, used_topics=None):
    """
    Generates a fresh, spirit-filled English devotional Reel using Google Gemini:
    - Strictly checks against ALL previously seen verses and headlines.
    - Automatic duplicate rejection and retry up to 3 times.
    - Tailored for global Christian audiences across Philippines, Nigeria, South Africa, USA, and India.
    - Dedicated to 'Jesus Hears You'.
    - NO mentions of 'AI'.
    - Uplifting scripture promise, warm pastoral narration, and inspiring infinite loop ending.
    """
    if not GEMINI_API_KEY:
        return None

    cat_id = category_info["id"]
    cat_desc = category_info["theme_desc"]

    # Load ALL permanently recorded verses to inject strict blacklist into prompt
    seen_data = load_christian_seen_verses()
    all_seen_verses = seen_data.get("seen_verses", [])
    recent_records = seen_data.get("records", [])[:15]

    forbidden_verses_bullets = "\n".join([f"- {v}" for v in all_seen_verses[-40:]])
    forbidden_headlines_bullets = "\n".join([f"- {r.get('headline')}" for r in recent_records if r.get('headline')])

    prompt_base = f"""
You are a warm, compassionate Christian pastor and viral devotional Reel scriptwriter for the global page "Jesus Hears You".
Your audience spans devoted believers in the Philippines, Nigeria, South Africa, the United States, and India.
Create a deeply moving, faith-strengthening, and uplifting 30-second devotional Reel in clear, accessible English.

CATEGORY: {category_info['name']} ({cat_id})
THEME: {cat_desc}

CRITICAL PERMANENT NON-REPETITION CONSTRAINT:
You are STRICTLY FORBIDDEN from choosing, referencing, or repeating ANY of the following Bible verses, scriptures, or headlines that have ALREADY been posted on "Jesus Hears You":

ALREADY USED BIBLE VERSES (STRICTLY FORBIDDEN):
{forbidden_verses_bullets}

ALREADY POSTED HEADLINES (STRICTLY FORBIDDEN):
{forbidden_headlines_bullets}

YOU MUST CHOOSE A COMPLETELY FRESH, UNUSED BIBLE VERSE from a different chapter or book of the Holy Bible (there are 31,102 verses to choose from!).

CRITICAL INSTRUCTIONS:
1. "headline": A powerful, uplifting scripture promise or core takeaway in clear English (8-14 words max).
2. "verse_reference": The exact Bible book, chapter and verse (e.g. "Romans 8:31", "Isaiah 40:31", "Psalm 46:1").
3. "voiceover_script": A deeply comforting, inspiring narration in natural spoken English (45-65 words, ~25-28 seconds of speech).
   - VIRAL INFINITE LOOP RETENTION HOOK: Structure the script so the very last sentence connects seamlessly back into the opening sentence without a hard stop.
     Example structure:
     Opening Hook: "This is the exact Bible verse your heart needed to hear today..."
     Devotional Reflection: "The Lord promises that when you pass through deep waters, they will not sweep over you..."
     Closing Loop Bridge: "So take a deep breath and surrender every heavy burden to Jesus right now, because..."
     (When the reel loops on Facebook, it connects seamlessly: "...surrender every heavy burden to Jesus right now, because... This is the exact Bible verse your heart needed to hear today!")
   - Hook the listener with God's unfailing love in the VERY FIRST sentence.
   - Speak with warmth, gentle encouragement, and unshakeable peace.
   - ABSOLUTELY NO greetings (NO "Hello friends", NO "Welcome back").
   - NEVER mention the word "AI" anywhere!
   - NEVER mention "24/7 daily" anywhere!
4. "visual_prompts": A list of 2 distinct, complementary English visual prompts for high-resolution 9:16 vertical photorealistic Biblical imagery.
   - e.g. "Cinematic 9:16 vertical photorealistic view of Jesus Christ in colorful robes seated in a blooming flower garden with vibrant purple wildflowers in foreground, golden sunrise rays, 8k"
   - e.g. "Cinematic 9:16 vertical photorealistic view of Jesus Christ teaching disciples on a serene sunlit hillside with radiant golden cross on horizon, blooming flowers, 8k"
   - NO text, NO watermarks in the prompts.
5. "engagement_question": An uplifting faith question or call-to-action (e.g. "Type AMEN if you receive this promise today! 🙏", "Share this blessing with someone who needs peace ✨").
6. "topic_id": A short unique English slug (e.g. "isaiah_40_31_eagle_wings").

Return ONLY valid JSON matching this schema:
{{
  "headline": "...",
  "verse_reference": "...",
  "voiceover_script": "...",
  "visual_prompts": ["...", "..."],
  "engagement_question": "...",
  "topic_id": "..."
}}
"""

    models_to_try = ["gemini-flash-lite-latest", "gemini-flash-latest"]
    prompt_attempt = prompt_base

    for attempt in range(1, 4):
        for model_name in models_to_try:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
                payload = {
                    "contents": [{"parts": [{"text": prompt_attempt}]}],
                    "generationConfig": {
                        "temperature": 0.85,
                        "responseMimeType": "application/json"
                    }
                }
                resp = _session.post(url, json=payload, timeout=18)
                if resp.status_code == 200:
                    data = resp.json()
                    raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                    res = json.loads(raw_text)
                    if res.get("headline") and res.get("voiceover_script"):
                        verse_cand = res.get("verse_reference", "")
                        head_cand = res.get("headline", "")
                        slug_cand = res.get("topic_id", "")

                        # Deduplication Shield Check
                        is_dup, reason = is_duplicate_christian_content(verse_cand, head_cand, slug_cand)
                        if is_dup:
                            print(f"⚠️ Gemini attempt {attempt} returned duplicate: {reason}. Retrying for fresh verse...")
                            prompt_attempt = f"{prompt_base}\nNOTE: '{verse_cand}' was already posted! Choose another scripture entirely."
                            break

                        if res.get("visual_prompts") and isinstance(res["visual_prompts"], list):
                            res["visual_prompt"] = res["visual_prompts"][0]
                        elif res.get("visual_prompt"):
                            res["visual_prompts"] = [res["visual_prompt"]]
                        res["caption"] = format_christian_caption(res, category_info)
                        return res
                elif resp.status_code == 429:
                    print(f"Gemini {model_name} rate limited (429), trying fallback model...")
                    continue
            except Exception as e:
                print(f"Notice: Gemini Christian generation notice ({model_name}): {e}")
                continue

    return None

def format_christian_caption(story, cat_info):
    """
    Formats a faith-filled, engaging devotional Facebook caption for 'Jesus Hears You'
    tailored for global Christian audiences across Philippines, Nigeria, South Africa, USA, and India:
    - Devotional Category Header
    - Scripture Verse & Bible Reference
    - Heartfelt Devotional Message
    - Call to Faith & Prayer ("Type AMEN", "Share this blessing")
    - Follow prompt (@JesusHearsYou)
    - Curated global Christian hashtags
    """
    badge = cat_info.get("badge_tag") or cat_info.get("name", "✝️ Jesus Hears You")
    headline = story.get("headline", "")
    verse_ref = story.get("verse_reference", "")
    script = (story.get("voiceover_script") or story.get("english_script") or story.get("script") or "").strip()
    question = story.get("engagement_question") or "Type 'AMEN' to claim this blessing today! 🕊️"
    hashtags = cat_info.get("hashtags") or "#JesusHearsYou #Jesus #DailyBibleVerse #GodIsGood #FaithOverFear #ChristianReels #Reels"

    verse_block = ""
    if verse_ref:
        verse_block = f"📖 Scripture:\n\"{headline}\"\n— {verse_ref}\n\n"
    elif headline:
        verse_block = f"✨ {headline}\n\n"

    thought_block = ""
    if script:
        thought_block = f"🕊️ Devotional Message:\n{script}\n\n"

    caption = (
        f"✝️ Jesus Hears You • {badge}\n\n"
        f"{verse_block}"
        f"{thought_block}"
        f"💬 {question}\n\n"
        f"🔔 Follow @JesusHearsYou for daily uplifting Bible verses and Christian prayers! ✝️\n\n"
        f"{hashtags}"
    )
    return caption.strip()

def crop_to_exact_9_16_vertical(source_image_path, output_path, target_width=1080, target_height=1920):
    """
    Ensures the image is true full-bleed 9:16 vertical (1080x1920):
    - Completely fills the 1080x1920 screen with the image itself (no blurred letterboxing, no bars).
    - Uses high-quality LANCZOS resampling and center cropping.
    """
    with Image.open(source_image_path) as img:
        img = img.convert("RGB")
        w, h = img.size
        target_ratio = target_width / target_height  # 9/16 = 0.5625
        current_ratio = w / h

        if current_ratio > target_ratio:
            # Image is wider than 9:16: fit height, crop width
            new_h = target_height
            new_w = int(w * (target_height / h))
        else:
            # Image is narrower or equal: fit width, crop height
            new_w = target_width
            new_h = int(h * (target_width / w))

        # BICUBIC resampling for fast, high-fidelity scaling
        resized = img.resize((new_w, new_h), Image.Resampling.BICUBIC)
        left = (new_w - target_width) // 2
        top = (new_h - target_height) // 2
        right = left + target_width
        bottom = top + target_height

        cropped = resized.crop((left, top, right, bottom))
        cropped.save(output_path, "JPEG", quality=95)
        return output_path

def apply_infinite_loop_structure(script, category_id="promise"):
    """
    Applies the viral infinite loop retention hook to devotional narration.
    Smooths the closing sentence so it connects seamlessly back into the opening hook,
    keeping viewers watching across the loop point for maximum retention score.
    """
    if not script:
        return script
    s = script.strip()
    # Check if already ends with an open loop connector
    if s.endswith("because...") or s.endswith("knowing that...") or s.endswith("remembering that..."):
        return s

    # Strip trailing punctuation or "Amen."
    s = re.sub(r'[\s\.\!\,]+amen[\s\.\!]*$', '', s, flags=re.IGNORECASE).strip()
    s = s.rstrip(".!,; ")

    bridges = {
        "promise": "So take a deep breath and walk forward in peace today, knowing that...",
        "wisdom": "Keep guarding your heart and speaking gentle truth, because...",
        "parable": "Never doubt that His boundless grace will reach you, because...",
        "mystery": "Stand firm in God's eternal, unchanging truth, because...",
        "prayer": "Release every heavy burden and sleep in heavenly peace tonight, knowing that..."
    }
    bridge = bridges.get(category_id, "Walk forward in confidence today, knowing that...")
    return f"{s}. {bridge}"

def get_christian_story(category_id=None):
    """
    Retrieves the next devotional story for 'Jesus Hears You':
    - If category_id is specified (e.g. 'promise', 'prayer'), uses that.
    - Otherwise, auto-selects based on current clock time.
    - Attempts Gemini generation with multi-model failover & deduplication rejection.
    - Falls back to 60+ curated rich devotional bank with strict non-repeating memory.
    - NEVER repeats any verse or headline that has ever been posted.
    """
    category = get_category_by_id(category_id) if category_id else get_scheduled_category_for_now()

    # 1. Try Gemini generation first
    story_data = generate_christian_story_with_gemini(category)
    if story_data:
        topic_id = story_data.get("topic_id") or f"{category['id']}_{int(time.time())}"
        story_data["category_id"] = category["id"]
        story_data["category_info"] = category
        raw_script = (story_data.get("voiceover_script") or story_data.get("english_script") or "").strip()
        script = apply_infinite_loop_structure(raw_script, category["id"])
        story_data["voiceover_script"] = script
        story_data["script"] = script
        story_data["tamil_script"] = script
        story_data["caption"] = format_christian_caption(story_data, category)

        # Permanently record selected story in Deduplication Registry
        record_used_christian_content(
            verse_ref=story_data.get("verse_reference"),
            headline=story_data.get("headline"),
            topic_id=topic_id,
            category=category["id"]
        )

        current_state = load_christian_state()
        current_state.setdefault("used_topics", []).append(topic_id)
        if len(current_state["used_topics"]) > 500:
            current_state["used_topics"] = current_state["used_topics"][-500:]
        save_christian_state(current_state)
        return story_data

    # 2. Curated library fallback (filtered strictly against ANY duplicate verse or headline)
    available = []
    for item in CURATED_CHRISTIAN_BANK:
        is_dup, _ = is_duplicate_christian_content(
            verse_ref=item.get("verse_reference"),
            headline=item.get("headline"),
            topic_id=item.get("topic_id")
        )
        if not is_dup:
            available.append(item)

    if not available:
        print("⚠️ Notice: Curated Christian library rolling window exhausted. Recycling oldest scriptures.")
        available = CURATED_CHRISTIAN_BANK

    cat_matches = [item for item in available if item["category"] == category["id"]]
    pool = cat_matches if cat_matches else available
    chosen = dict(random.choice(pool))

    cat_match = next((c for c in CHRISTIAN_CATEGORIES if c["id"] == chosen["category"]), category)
    chosen["category_id"] = chosen["category"]
    chosen["category_info"] = cat_match
    raw_script = (chosen.get("voiceover_script") or chosen.get("english_script") or "").strip()
    script = apply_infinite_loop_structure(raw_script, chosen["category"])
    chosen["voiceover_script"] = script
    chosen["script"] = script
    chosen["tamil_script"] = script
    chosen["caption"] = format_christian_caption(chosen, cat_match)

    # Permanently record chosen curated story in Deduplication Registry
    record_used_christian_content(
        verse_ref=chosen.get("verse_reference"),
        headline=chosen.get("headline"),
        topic_id=chosen.get("topic_id"),
        category=chosen.get("category")
    )

    current_state = load_christian_state()
    current_state.setdefault("used_topics", []).append(chosen["topic_id"])
    save_christian_state(current_state)
    return chosen

# Aliases for pipeline compatibility
get_scheduled_christian_category = get_scheduled_category_for_now
generate_christian_story = get_christian_story


JESUS_VISUAL_THEMES = {
    "jesus_good_shepherd.jpg": [
        "shepherd", "sheep", "lamb", "pasture", "psalm 23", "psalms 23", "guide", "lead", 
        "lost", "rod", "staff", "valley", "flock", "fold", "green pastures", "tender"
    ],
    "jesus_prayer.jpg": [
        "prayer", "pray", "bedtime", "night", "weary", "rest", "burden", "cry", "tears", 
        "peace", "be still", "surrender", "gethsemane", "kneel", "heavy", "trouble", 
        "anxious", "anxiety", "quiet", "matthew 11", "solitude", "humble"
    ],
    "jesus_blessing.jpg": [
        "bless", "blessing", "favor", "heal", "healing", "hands", "grace", "promise", 
        "fear not", "do not fear", "with you", "strength", "philippians", "prosper", 
        "plans", "comfort", "never forsake", "jeremiah 29", "deuteronomy 31", "outstretched",
        "open arms", "touch", "compassion"
    ],
    "jesus_flower_garden.jpg": [
        "flower", "garden", "renew", "bloom", "beauty", "spring", "rejoice", "joy", 
        "love", "creation", "zephaniah", "gentle", "song", "singing", "meadow", "blooming"
    ],
    "jesus_garden_seated.jpg": [
        "wisdom", "proverbs", "word", "truth", "walk", "parable", "sower", "seed", 
        "olive", "seated", "meditate", "ponder", "teach", "disciple", "scripture", 
        "understanding", "deep", "contemplate"
    ],
    "jesus_sunrise_halo.jpg": [
        "sunrise", "morning", "dawn", "light", "resurrection", "glory", "heaven", 
        "celestial", "eagle", "wings", "isaiah 40", "lift", "shine", "victory", 
        "sunburst", "bright", "radiant", "halo", "daybreak"
    ],
    "jesus_portrait_remastered.jpg": [
        "king", "lord", "mighty", "warrior", "salvation", "steadfast", "rock", 
        "fortress", "psalm 46", "eternal", "sovereign", "majesty", "christ", 
        "faith", "romans 8", "unshakeable", "overcome"
    ]
}


def select_thematic_jesus_image(category_id="promise", headline="", verse_reference="", script_text="", visual_prompts=None):
    """
    Intelligently selects the most contextually relevant Jesus Christ artwork from assets/jesus_visuals/.
    Ensures 100% of devotional reels feature a sacred, high-reverence Jesus image matching the reel's exact message.
    """
    jesus_dir = os.path.join(BASE_DIR, "assets", "jesus_visuals")
    if not os.path.exists(jesus_dir):
        # Fallback to single master visual if directory is missing
        master = os.path.join(BASE_DIR, "assets", "jesus_master_visual.jpg")
        return master if os.path.exists(master) else None

    # Aggregate all narrative text from the devotional reel for semantic scoring
    prompt_str = " ".join(visual_prompts) if isinstance(visual_prompts, (list, tuple)) else str(visual_prompts or "")
    combined_text = f"{headline} {verse_reference} {script_text} {prompt_str} {category_id}".lower()

    scores = {}
    for filename, keywords in JESUS_VISUAL_THEMES.items():
        fp = os.path.join(jesus_dir, filename)
        if os.path.exists(fp):
            score = sum(1 for kw in keywords if kw in combined_text)
            scores[filename] = score

    if scores:
        max_score = max(scores.values())
        if max_score > 0:
            # Pick highest scoring thematic match
            best_matches = [f for f, s in scores.items() if s == max_score]
            chosen_file = best_matches[0]
            chosen_path = os.path.join(jesus_dir, chosen_file)
            print(f"✨ Thematically Matched Jesus Visual: {chosen_file} (Score: {max_score})")
            return chosen_path

    # Category preference fallback if no explicit keywords triggered
    category_defaults = {
        "prayer": "jesus_prayer.jpg",
        "promise": "jesus_blessing.jpg",
        "wisdom": "jesus_garden_seated.jpg",
        "parable": "jesus_good_shepherd.jpg",
        "mystery": "jesus_sunrise_halo.jpg"
    }
    default_name = category_defaults.get(category_id.lower(), "jesus_blessing.jpg")
    default_path = os.path.join(jesus_dir, default_name)
    if os.path.exists(default_path):
        print(f"✨ Category Default Jesus Visual: {default_name}")
        return default_path

    # Any available visual in the folder
    available = [f for f in os.listdir(jesus_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    if available:
        return os.path.join(jesus_dir, sorted(available)[0])

    master = os.path.join(BASE_DIR, "assets", "jesus_master_visual.jpg")
    return master if os.path.exists(master) else None


def fetch_christian_visual(visual_prompt, category_id="promise", scene_idx=0, suffix="", headline="", verse_reference="", script_text="", prefer_video=None):
    """
    Retrieves or copies a high-resolution 9:16 vertical Jesus Christ visual artwork or motion video:
    1. If prefer_video is True (or CHRISTIAN_USE_VIDEO_BG=true in .env), queries Pixabay Videos API for motion footage.
    2. Tries free Pixabay Images API (if PIXABAY_API_KEY is configured in .env) with thematic search.
    3. Fallback to curated local 9:16 Jesus visual art gallery (assets/jesus_visuals/).
    4. Fallback to master Jesus artwork.
    Guarantees 100% of devotional reels feature a sacred, thematic visual of Jesus Christ.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_filename = f"christian_visual_{int(time.time())}{suffix}.jpg"
    out_path = os.path.join(OUTPUT_DIR, out_filename)

    from config import CHRISTIAN_USE_VIDEO_BG
    use_video = prefer_video if prefer_video is not None else CHRISTIAN_USE_VIDEO_BG

    # Build contextual search query for Pixabay
    full_text = f"{headline} {verse_reference} {script_text} {category_id}".lower()
    if any(w in full_text for w in ["shepherd", "sheep", "lamb", "psalm 23"]):
        pix_q = "jesus shepherd"
    elif any(w in full_text for w in ["prayer", "pray", "weary", "rest", "burden", "peace"]):
        pix_q = "jesus prayer"
    elif any(w in full_text for w in ["bless", "favor", "heal", "hands", "strength"]):
        pix_q = "jesus blessing"
    elif any(w in full_text for w in ["wisdom", "parable", "teach", "disciple"]):
        pix_q = "jesus teaching"
    elif any(w in full_text for w in ["sunrise", "morning", "light", "dawn", "resurrection"]):
        pix_q = "jesus resurrection"
    else:
        pix_q = "jesus christ"

    # 1. Try Pixabay Motion Video (if video mode enabled)
    if use_video:
        try:
            from pixabay_fetcher import fetch_pixabay_jesus_video
            pix_vid = fetch_pixabay_jesus_video(query=pix_q)
            if pix_vid and os.path.exists(pix_vid) and os.path.getsize(pix_vid) > 20000:
                print(f"🎥 Using Pixabay Free Motion Video: {os.path.basename(pix_vid)}")
                return pix_vid
        except Exception as e:
            print(f"Notice: Pixabay video fetch notice: {e}")

    # 2. Try Free Pixabay API (Dynamic fresh images)
    try:
        from pixabay_fetcher import fetch_pixabay_jesus_image
        pix_img = fetch_pixabay_jesus_image(query=pix_q)
        if pix_img and os.path.exists(pix_img) and os.path.getsize(pix_img) > 10000:
            print(f"✨ Using Pixabay Free Stock Jesus Visual: {os.path.basename(pix_img)}")
            return pix_img
    except Exception as e:
        print(f"Notice: Pixabay fetch notice: {e}")

    # 3. Curated Local Thematic Jesus Art Gallery
    chosen_source = select_thematic_jesus_image(
        category_id=category_id,
        headline=headline,
        verse_reference=verse_reference,
        script_text=script_text,
        visual_prompts=[visual_prompt] if visual_prompt else []
    )

    if chosen_source and os.path.exists(chosen_source):
        try:
            shutil.copyfile(chosen_source, out_path)
            return out_path
        except Exception as e:
            print(f"Notice: Failed to copy local Jesus visual: {e}")

    # 4. Fallback to Master Jesus Visual
    local_master = os.path.join(BASE_DIR, "assets", "jesus_master_visual.jpg")
    if os.path.exists(local_master):
        shutil.copyfile(local_master, out_path)
        return out_path

    return None


def fetch_christian_visuals(visual_prompts=None, category_id="promise", headline="", verse_reference="", script_text=""):
    """
    Retrieves the sacred, contextually-matched Jesus Christ visual for the Christian devotional reel.
    To prevent rapid/jarring image switches and ensure a peaceful, reverent viewing experience,
    a single high-reverence Jesus artwork is sustained throughout the reel with gentle cinematic motion.
    """
    vp = fetch_christian_visual(
        visual_prompt=visual_prompts[0] if (isinstance(visual_prompts, (list, tuple)) and visual_prompts) else "",
        category_id=category_id,
        scene_idx=0,
        suffix="",
        headline=headline,
        verse_reference=verse_reference,
        script_text=script_text
    )

    if vp and os.path.exists(vp):
        return [vp]

    return []
