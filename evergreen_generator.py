import os
import json
import time
import random
import urllib.parse
import requests
from config import GEMINI_API_KEY, OUTPUT_DIR, VIDEO_WIDTH, VIDEO_HEIGHT
from media_extractor import create_ambient_vertical_canvas
from PIL import Image, ImageDraw

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

EVERGREEN_STATE_FILE = os.path.join(os.path.dirname(__file__), "evergreen_state.json")

CATEGORIES = [
    {
        "id": "history",
        "name": "🏛️ வரலாற்று மர்மம்",
        "theme_desc": "Ancient Tamil civilization (Cholas, Pandyas, Cheras), Thanjavur temple architectural marvels, lost cities, Indus Valley, or world historical mysteries.",
        "badge_tag": "🏛️ வரலாற்றுச் சுவாரசியம்",
        "hashtags": "#TamilHistory #வரலாறு #CholaDynasty #AncientTamil #Mystery #Reels"
    },
    {
        "id": "gk",
        "name": "💡 வியக்கவைக்கும் தகவல்",
        "theme_desc": "Did You Know? Bizarre general knowledge facts, fascinating human body secrets, psychology, or unbelievable world records.",
        "badge_tag": "💡 உங்களுக்குத் தெரியுமா?",
        "hashtags": "#DidYouKnow #TamilGK #பொதுஅறிவு #AmazingFacts #Knowledge #Reels"
    },
    {
        "id": "science",
        "name": "🔬 அறிவியல் உலகம்",
        "theme_desc": "Deep space mysteries (Black Holes, James Webb discoveries, Neutron stars), deep ocean trenches, bizarre wildlife adaptations, or quantum physics in simple terms.",
        "badge_tag": "🔬 அறிவியல் ஆச்சரியம்",
        "hashtags": "#ScienceFacts #Space #Universe #அறிவியல் #Nature #Reels"
    },
    {
        "id": "story",
        "name": "✨ ஞானச் சிறுகதை",
        "theme_desc": "One-minute wisdom story, inspirational Zen tale, Tenali Raman wit, or deep life-lesson story that leaves viewers motivated.",
        "badge_tag": "✨ ஒரு நிமிட ஞானக் கதை",
        "hashtags": "#TamilStories #Motivation #ZenStory #வாழ்க்கைத்_தத்துவம் #Wisdom #Reels"
    }
]

# Rich, pre-curated fallback library (20 topics) in case of offline/network issues
CURATED_FALLBACK_BANK = [
    {
        "category": "history",
        "topic_id": "thanjavur_brihadisvara_temple_shadow",
        "headline": "தஞ்சைப் பெரிய கோவில்: ஆயிரம் ஆண்டுகள் கடந்தும் வியக்கவைக்கும் கட்டிடக்கலை ரகசியம்!",
        "voiceover_script": "ஆயிரம் ஆண்டுகளுக்கு முன்பு எந்தவித நவீன தொழில்நுட்பமும் இல்லாத காலத்தில், எண்பது டன் எடைகொண்ட ஒற்றைக்கல் விமானத்தை தஞ்சை பெரிய கோவிலின் உச்சியில் ராஜராஜ சோழன் எவ்வாறு ஏற்றினார் என்பது இன்றும் விடைதெரியாத மர்மமாக உள்ளது. நிலநடுக்கங்கள் மற்றும் புயல்களைத் தாங்கி இன்றும் கம்பீரமாக நிற்கும் இக்கோவில் தமிழர்களின் கட்டிடக்கலை உச்சத்திற்கு உலகளாவிய சான்றாகும்.",
        "visual_prompt": "Cinematic 9:16 vertical photograph of ancient Thanjavur Brihadisvara big temple gopuram, dramatic golden hour sunlight, majestic clouds, 8k photorealistic documentary style",
        "engagement_question": "சோழர்களின் இந்த அசாத்திய கட்டிடக்கலை சாதனை பற்றி நீங்கள் என்ன நினைக்கிறீர்கள்?"
    },
    {
        "category": "gk",
        "topic_id": "octopus_three_hearts_blue_blood",
        "headline": "ஆக்டோபஸ் பற்றிய இந்த வியக்கவைக்கும் உண்மை உங்களுக்குத் தெரியுமா?",
        "voiceover_script": "கடலின் விசித்திர உயிரினமான ஆக்டோபஸுக்கு மூன்று இதயங்கள் மற்றும் ஒன்பது மூளைகள் உள்ளன என்பது உங்களுக்குத் தெரியுமா? அதன் ரத்தம் மனிதர்களைப் போல சிவப்பு நிறத்தில் இல்லாமல் நீல நிறத்தில் இருக்கும். ஆபத்து ஏற்படும் போது தன் உடலின் நிறத்தையும் தோலின் அமைப்பையும் சில நொடிகளில் மாற்றிக்கொள்ளும் பேராற்றல் இதற்கு உண்டு.",
        "visual_prompt": "Cinematic 9:16 vertical underwater photograph of a glowing intelligent octopus with intricate tentacles, deep blue ocean, coral reef background, National Geographic quality, 8k",
        "engagement_question": "இயற்கையின் இந்த விசித்திர படைப்பு உங்களுக்கு ஆச்சரியத்தை ஏற்படுத்துகிறதா?"
    },
    {
        "category": "science",
        "topic_id": "black_hole_event_horizon_time_dilation",
        "headline": "கருந்துளைக்கு அருகில் சென்றால் காலம் நின்றுவிடுமா? விண்வெளி ஆச்சரியம்!",
        "voiceover_script": "விண்வெளியின் மிகப்பெரிய மர்மமான கருந்துளையின் ஈர்ப்பு விசை ஒளியைக் கூட தப்பவிடாத அளவுக்கு அதீத சக்தி வாய்ந்தது. ஐன்ஸ்டீனின் சார்பியல் தத்துவப்படி, கருந்துளையின் எல்லைப் பகுதிக்கு நீங்கள் சென்றால், அங்கு காலம் மிக மிக மெதுவாக நகரும். நீங்கள் அங்கு சில நிமிடங்கள் இருந்துவிட்டு பூமிக்குத் திரும்பினால், பூமியில் பல நூறு ஆண்டுகள் கடந்திருக்கும்.",
        "visual_prompt": "Cinematic 9:16 vertical rendering of a supermassive black hole with glowing fiery accretion disk and bent light rays, deep cosmos starfield, interstellar movie aesthetic, 8k",
        "engagement_question": "விண்வெளியின் இந்த விசித்திரமான காலப் பயணம் பற்றி உங்கள் கருத்து என்ன?"
    },
    {
        "category": "story",
        "topic_id": "zen_story_heavy_stone_burden",
        "headline": "வாழ்க்கையில் கவலைகளை சுமப்பவர்களுக்கான ஒரு நிமிட ஞானக் கதை!",
        "voiceover_script": "ஒரு ஞானி தன் சீடர்களிடம் ஒரு தம்ளர் தண்ணீரைக் காட்டி, இதன் எடை என்ன என்று கேட்டார். சீடர்கள் வெவ்வேறு எடையைக் கூறினர். ஞானி புன்னகைத்து, இதன் எடையை விட, இதை எவ்வளவு நேரம் தூக்கிப் பிடித்திருக்கிறீர்கள் என்பதே முக்கியம் என்றார். ஒரு நிமிடம் பிடித்தால் வலிக்காது, நாள் முழுவதும் பிடித்தால் கை மரத்துப் போகும். வாழ்க்கையின் கவலைகளும் அப்படித்தான், உடனடியாக இறக்கி வைக்கக் கற்றுக்கொள்ளுங்கள்.",
        "visual_prompt": "Aesthetic 9:16 vertical cinematic photograph of a serene Zen monk standing beside a tranquil mountain waterfall, warm morning sunlight, peaceful atmosphere, 8k fine art",
        "engagement_question": "இந்தக் கதையின் கருத்து உங்கள் வாழ்க்கைக்கு பொருந்துகிறதா?"
    },
    {
        "category": "history",
        "topic_id": "chola_navy_southeast_asia_expedition",
        "headline": "ஆயிரம் ஆண்டுகளுக்கு முன்பே கடல்கடந்து வென்ற ராஜேந்திர சோழனின் கடற்படை!",
        "voiceover_script": "பண்டைய உலக வரலாற்றில் மிக பலம் வாய்ந்த கடற்படையைக் கொண்டு வங்காள விரிகுடாவை சோழர்களின் ஏரியாக மாற்றியவர் ராஜேந்திர சோழர். நவீன கப்பல்கள் இல்லாத காலத்திலேயே ஆயிரக்கணக்கான போர் வீரர்களுடன் இந்தோனேசியா, மலேசியா மற்றும் இலங்கை நாடுகளுக்கு கடல் வழியாகச் சென்று வெற்றி பெற்ற சோழர் கடற்படையின் வீரம் தமிழர்களின் அழிக்க முடியாத வரலாற்றுப் பெருமையாகும்.",
        "visual_prompt": "Cinematic 9:16 vertical artwork of ancient Tamil Chola war galleys sailing across rough ocean waters at sunset, fluttering tiger flags, epic historical realism, 8k",
        "engagement_question": "சோழர்களின் கடல்சார் ஆதிக்கம் பற்றி பள்ளிகளில் அதிகம் கற்பிக்கப்பட வேண்டுமா?"
    },
    {
        "category": "gk",
        "topic_id": "human_brain_storage_capacity",
        "headline": "மனித மூளையின் அசாத்திய சக்தி: எத்தனை மெகாபைட் நினைவாற்றல் தெரியுமா?",
        "voiceover_script": "நவீன உலகின் அதிநவீன சூப்பர் கம்ப்யூட்டர்களை விட மனித மூளை பல மடங்கு சக்தி வாய்ந்தது என்று நரம்பியல் ஆய்வாளர்கள் கூறுகின்றனர். மனித மூளையின் சேமிக்கும் திறன் சுமார் இரண்டரை பெட்டாபைட்டுகள், அதாவது இருபத்தி ஐந்து லட்சம் கிகாபைட்டுகளுக்கு சமம். இது சுமார் முந்நூறு ஆண்டுகள் தொடர்ந்து ஒளிபரப்பாகும் உயர்தர வீடியோக்களைச் சேமிப்பதற்குச் சமமாகும்.",
        "visual_prompt": "Cinematic 9:16 vertical visualization of a glowing human brain with firing golden neural synapses and digital cosmic energy circuits, hyperdetailed, 8k",
        "engagement_question": "நமது மூளையின் இந்த வியக்கவைக்கும் சக்தியை நாம் முழுமையாகப் பயன்படுத்துகிறோமா?"
    },
    {
        "category": "science",
        "topic_id": "deep_ocean_mariana_trench_mystery",
        "headline": "மரியானா அகழி: உலகின் மிக ஆழமான இடத்தில் வாழும் விசித்திர உயிரினங்கள்!",
        "voiceover_script": "பூமியின் மிக ஆழமான பகுதியான பசிபிக் பெருங்கடலின் மரியானா அகழி பதினொரு கிலோமீட்டர் ஆழமுடையது. எவரெஸ்ட் சிகரத்தையே உள்ளே மூழ்கடித்தாலும் மேலும் இரண்டு கிலோமீட்டர் நீர் மேலே நிற்கும். சூரிய வெளிச்சமே இல்லாத மற்றும் அதீத நீர் அழுத்தம் உள்ள இந்த இருண்ட உலகிலும் ஒளிரும் விசித்திர உயிரினங்கள் வாழ்வது விஞ்ஞானிகளை வியப்பில் ஆழ்த்தியுள்ளது.",
        "visual_prompt": "Cinematic 9:16 vertical deep sea exploration documentary photo, research submersible spotlight revealing glowing ethereal translucent deep-sea creatures in dark abyss, 8k",
        "engagement_question": "விண்வெளியை விட பூமியின் கடல்களைப் பற்றி நாம் குறைவாகவே அறிந்துள்ளோமா?"
    },
    {
        "category": "story",
        "topic_id": "two_wolves_fighting_inside_heart",
        "headline": "நமக்குள்ளே போராடும் இரண்டு ஓநாய்கள்: பழங்குடி மக்களின் அரிய ஞானக் கதை!",
        "voiceover_script": "ஒரு வயதான தாத்தா தன் பேரனிடம், மனிதனின் மனதிற்குள் எப்போதும் இரண்டு ஓநாய்கள் சண்டையிட்டுக்கொண்டே இருக்கும் என்றார். ஒன்று கோபம், பொறாமை, பேராசை மற்றும் சுயநலம் கொண்டது. மற்றொன்று அன்பு, கருணை, அமைதி மற்றும் நம்பிக்கை கொண்டது. பேரன் கேட்டான், இதில் எந்த ஓநாய் வெற்றி பெறும் தாத்தா? தாத்தா புன்னகையுடன் சொன்னார், நீ எதற்கு தினமும் உணவு ஊட்டுகிறாயோ அதுவே வெற்றி பெறும்.",
        "visual_prompt": "Mystical 9:16 vertical digital painting of two ethereal wolves facing each other under a starry moonlit forest night sky, one glowing with warm golden light, one with dark smoke, 8k",
        "engagement_question": "உங்கள் மனதுக்குள் இன்று நீங்கள் எந்த குணத்திற்கு உணவு ஊட்டுகிறீர்கள்?"
    }
]

def load_evergreen_state():
    if os.path.exists(EVERGREEN_STATE_FILE):
        try:
            with open(EVERGREEN_STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"last_category_index": -1, "used_topics": []}

def save_evergreen_state(state):
    try:
        with open(EVERGREEN_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Notice: Failed to save evergreen state: {e}")

def get_next_category():
    state = load_evergreen_state()
    curr_idx = state.get("last_category_index", -1)
    next_idx = (curr_idx + 1) % len(CATEGORIES)
    state["last_category_index"] = next_idx
    save_evergreen_state(state)
    return CATEGORIES[next_idx]

def generate_evergreen_with_gemini(category_info, recent_topics):
    """
    Prompts Gemini Flash to create a high-engagement, shareable Tamil micro-content Reel:
    - 25-45 second spoken narrative in fluent, spoken Tamil (Valluvar neural voice)
    - No greetings like 'வணக்கம்', jumps straight into the captivating narrative
    - Detailed 9:16 vertical English prompt for Flux image generation
    """
    if not GEMINI_API_KEY:
        return None

    cat_id = category_info["id"]
    cat_desc = category_info["theme_desc"]

    prompt = f"""
You are an expert Tamil storyteller, historian, and viral content creator for Facebook Reels.
Create an exciting, mind-blowing, and highly shareable 30-40 second micro-Reel in Tamil.

CATEGORY: {category_info['name']} ({cat_id})
THEME INSPIRATION: {cat_desc}

DO NOT repeat any of these recently used topics:
{json.dumps(recent_topics[-15:], ensure_ascii=False)}

REQUIREMENTS:
1. "headline": A punchy, curiosity-inducing Tamil headline (8-12 words max) suitable for a 9:16 broadcast card.
2. "voiceover_script": A captivating, fast-paced narration in pure, spoken Tamil (~40-60 words, ~25-35 seconds of speech).
   - Hook the viewer in the VERY FIRST sentence with an intriguing question or statement.
   - Tell a complete, fascinating story or mind-blowing fact.
   - ABSOLUTELY NO greetings (NO "வணக்கம்", NO "இன்றைய"). Jump directly into the narrative.
   - NO outro CTAs (NO "கமெண்ட் செய்யுங்கள்", NO "லைக் செய்யுங்கள்"). End with a memorable, thought-provoking punchline.
3. "visual_prompt": A highly detailed English visual prompt for a 9:16 vertical AI image generator (Flux/SDXL).
   - Must be: "Cinematic 9:16 vertical photograph of [detailed scene], [lighting], [mood], 8k, photorealistic documentary style".
   - NO text, NO words, NO logos in the visual.
4. "engagement_question": A thoughtful question in Tamil asking viewers for their opinion/perspective.
5. "topic_id": A short unique slug in English (e.g. "sigiriya_palace_mystery", "human_eye_megapixels").

Return ONLY valid JSON matching this schema:
{{
  "headline": "...",
  "voiceover_script": "...",
  "visual_prompt": "...",
  "engagement_question": "...",
  "topic_id": "..."
}}
"""
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.8,
                "responseMimeType": "application/json"
            }
        }
        resp = requests.post(url, json=payload, timeout=18)
        if resp.status_code == 200:
            data = resp.json()
            raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
            res = json.loads(raw_text)
            if res.get("headline") and res.get("voiceover_script"):
                return res
    except Exception as e:
        print(f"Notice: Gemini evergreen generation failed: {e}")
    return None

def fetch_evergreen_visual(visual_prompt, category_id="gk"):
    """
    Downloads or renders a 9:16 vertical image for the evergreen reel:
    1. Tries Pollinations Flux AI generator (1080x1920) with prompt.
    2. Fallback to Unsplash / Wikimedia source.
    3. Fallback to ambient broadcast gradient canvas.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_filename = f"evergreen_visual_{int(time.time())}.jpg"
    out_path = os.path.join(OUTPUT_DIR, out_filename)
    temp_raw = os.path.join(OUTPUT_DIR, f"temp_ev_{int(time.time())}.jpg")

    # 1. Try Pollinations Flux (Fast & Free 9:16)
    if visual_prompt:
        try:
            clean_p = visual_prompt.replace("\n", " ").strip()[:200]
            encoded = urllib.parse.quote(clean_p)
            ai_url = f"https://image.pollinations.ai/prompt/{encoded}?width=1080&height=1920&nologo=true&model=flux"
            resp = requests.get(ai_url, headers=HEADERS, timeout=18)
            if resp.status_code == 200 and len(resp.content) > 10000:
                with open(temp_raw, "wb") as f:
                    f.write(resp.content)
                create_ambient_vertical_canvas(temp_raw, out_path)
                if os.path.exists(temp_raw):
                    os.remove(temp_raw)
                if os.path.exists(out_path) and os.path.getsize(out_path) > 10000:
                    print(f"🎨 Successfully generated AI Flux visual for: {clean_p[:40]}...")
                    return out_path
        except Exception as e:
            print(f"Notice: Pollinations Flux visual notice: {e}")

    # 2. Try High-Quality Unsplash Editorial Fallback
    category_fallbacks = {
        "history": "https://images.unsplash.com/photo-1590059390046-5381d6d23192?w=1080&h=1920&fit=crop&q=80",
        "science": "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=1080&h=1920&fit=crop&q=80",
        "gk": "https://images.unsplash.com/photo-1507668077129-56e32842fceb?w=1080&h=1920&fit=crop&q=80",
        "story": "https://images.unsplash.com/photo-1518495973542-4542c06a5843?w=1080&h=1920&fit=crop&q=80"
    }
    fb_url = category_fallbacks.get(category_id, category_fallbacks["gk"])
    try:
        resp = requests.get(fb_url, headers=HEADERS, timeout=12)
        if resp.status_code == 200 and len(resp.content) > 10000:
            with open(temp_raw, "wb") as f:
                f.write(resp.content)
            create_ambient_vertical_canvas(temp_raw, out_path)
            if os.path.exists(temp_raw):
                os.remove(temp_raw)
            return out_path
    except Exception as e:
        print(f"Notice: Unsplash fallback notice: {e}")

    # 3. Clean Obsidian Studio Canvas Fallback
    base = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), (12, 16, 24))
    draw = ImageDraw.Draw(base)
    for y in range(VIDEO_HEIGHT):
        ratio = y / VIDEO_HEIGHT
        draw.line([(0, y), (VIDEO_WIDTH, y)], fill=(int(12 + 18*ratio), int(16 + 24*ratio), int(24 + 40*ratio)))
    base.save(out_path, "JPEG", quality=90)
    return out_path

def get_evergreen_story():
    """
    Retrieves the next evergreen story in rotation:
    - Rotates category: history -> gk -> science -> story
    - Calls Gemini Flash to generate fresh, non-repeated content
    - Falls back to curated library if offline
    """
    state = load_evergreen_state()
    used = set(state.get("used_topics", []))
    category = get_next_category()

    # Try Gemini generation first
    story_data = generate_evergreen_with_gemini(category, list(used))
    if story_data:
        topic_id = story_data.get("topic_id") or f"{category['id']}_{int(time.time())}"
        story_data["category_id"] = category["id"]
        story_data["category_info"] = category
        state["used_topics"].append(topic_id)
        if len(state["used_topics"]) > 200:
            state["used_topics"] = state["used_topics"][-200:]
        save_evergreen_state(state)
        return story_data

    # Fallback to curated library
    available = [item for item in CURATED_FALLBACK_BANK if item["topic_id"] not in used]
    if not available:
        # Reset used topics if all exhausted
        state["used_topics"] = []
        save_evergreen_state(state)
        available = CURATED_FALLBACK_BANK

    chosen = random.choice(available)
    cat_match = next((c for c in CATEGORIES if c["id"] == chosen["category"]), CATEGORIES[1])
    chosen["category_id"] = chosen["category"]
    chosen["category_info"] = cat_match

    state["used_topics"].append(chosen["topic_id"])
    save_evergreen_state(state)
    return chosen
