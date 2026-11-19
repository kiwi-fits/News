import re

# Comprehensive dictionary for common English words, technology, news, politics, and social terms
ENGLISH_TO_TAMIL_DICT = {
    # Specifically requested by user
    "wonders": "ஒண்டெர்ஸ்",
    "wonder": "ஒண்டர்",
    "7wonders": "7 ஒண்டெர்ஸ்",

    # Tech & Social Media
    "ai": "ஏஐ",
    "artificial intelligence": "செயற்கை நுண்ணறிவு",
    "cctv": "சிசிடிவி",
    "dna": "டிஎன்ஏ",
    "gps": "ஜிபிஎஸ்",
    "sim": "சிம்",
    "wifi": "வைஃபை",
    "bluetooth": "புளூடூத்",
    "internet": "இன்டர்நெட்",
    "online": "ஆன்லைன்",
    "offline": "ஆஃப்லைன்",
    "mobile": "மொபைல்",
    "phone": "போன்",
    "smartphone": "ஸ்மார்ட்போன்",
    "laptop": "லேப்டாப்",
    "computer": "கம்ப்யூட்டர்",
    "software": "மென்பொருள்",
    "hardware": "வன்பொருள்",
    "app": "செயலி",
    "apps": "செயலிகள்",
    "website": "வலைத்தளம்",
    "link": "இணைப்பு",
    "facebook": "பேஸ்புக்",
    "whatsapp": "வாட்ஸ்அப்",
    "instagram": "இன்ஸ்டாகிராம்",
    "youtube": "யூடியூப்",
    "twitter": "ட்விட்டர்",
    "google": "கூகுள்",
    "apple": "ஆப்பிள்",
    "microsoft": "மைக்ரோசாப்ட்",
    "iphone": "ஐபோன்",
    "android": "ஆண்ட்ராய்டு",
    "video": "வீடியோ",
    "videos": "வீடியோக்கள்",
    "audio": "ஆடியோ",
    "photo": "புகைப்படம்",
    "photos": "புகைப்படங்கள்",
    "camera": "கேமரா",
    "selfie": "செல்ஃபி",
    "reel": "ரீல்",
    "reels": "ரீல்ஸ்",
    "post": "பதிவு",
    "posts": "பதிவுகள்",
    "story": "ஸ்டோரி",
    "stories": "ஸ்டோரிகள்",
    "status": "ஸ்டேட்டஸ்",
    "share": "பகிரவும்",
    "subscribe": "சப்ஸ்கிரைப்",
    "comment": "கருத்து",
    "comments": "கருத்துக்கள்",
    "like": "லைக்",
    "likes": "லைக்குகள்",
    "follow": "ஃபாலோ",
    "followers": "ஃபாலோவர்கள்",
    "viral": "வைரல்",
    "trending": "டிரெண்டிங்",
    "chat": "சாட்",
    "call": "கால்",
    "message": "மெசேஜ்",
    "messages": "மெசேஜ்கள்",
    "email": "மின்னஞ்சல்",
    "download": "பதிவிறக்கம்",
    "upload": "பதிவேற்றம்",
    "battery": "பேட்டரி",
    "charger": "சார்ஜர்",

    # Space & Science
    "nasa": "நாசா",
    "isro": "இஸ்ரோ",
    "space": "விண்வெளி",
    "rocket": "ராக்கெட்",
    "satellite": "செயற்கைக்கோள்",
    "orbit": "சுற்றுப்பாதை",
    "black hole": "கருந்துளை",
    "blackhole": "கருந்துளை",
    "galaxy": "கேலக்ஸி",
    "planet": "கிரகம்",
    "planets": "கிரகங்கள்",
    "earth": "பூமி",
    "mars": "செவ்வாய்",
    "moon": "நிலவு",
    "sun": "சூரியன்",
    "star": "நட்சத்திரம்",
    "stars": "நட்சத்திரங்கள்",
    "universe": "பிரபஞ்சம்",
    "james webb": "ஜேம்ஸ் வெப்",
    "telescope": "தொலைநோக்கி",
    "science": "அறிவியல்",
    "scientist": "விஞ்ஞானி",
    "scientists": "விஞ்ஞானிகள்",
    "research": "ஆராய்ச்சி",
    "discovery": "கண்டுபிடிப்பு",
    "robot": "ரோபோ",
    "robots": "ரோபோக்கள்",

    # Organizations & Government
    "un": "ஐநா",
    "uno": "ஐநா சபை",
    "who": "உலக சுகாதார அமைப்பு",
    "fbi": "எஃப்பிஐ",
    "cia": "சிஐஏ",
    "interpol": "இன்டர்போல்",
    "court": "நீதிமன்றம்",
    "high court": "உயர்நீதிமன்றம்",
    "supreme court": "உச்சநீதிமன்றம்",
    "judge": "நீதிபதி",
    "police": "போலீஸ்",
    "army": "ராணுவம்",
    "navy": "கடற்படை",
    "air force": "விமானப்படை",
    "president": "ஜனாதிபதி",
    "prime minister": "பிரதமர்",
    "minister": "அமைச்சர்",
    "ministers": "அமைச்சர்கள்",
    "cabinet": "அமைச்சரவை",
    "parliament": "நாடாளுமன்றம்",
    "mp": "நாடாளுமன்ற உறுப்பினர்",
    "mla": "சட்டமன்ற உறுப்பினர்",
    "government": "அரசாங்கம்",
    "governor": "ஆளுநர்",
    "election": "தேர்தல்",
    "vote": "வாக்கு",
    "voters": "வாக்காளர்கள்",
    "party": "கட்சி",
    "leader": "தலைவர்",
    "leaders": "தலைவர்கள்",

    # Infrastructure, Travel & Medical
    "hospital": "மருத்துவமனை",
    "doctor": "டாக்டர்",
    "doctors": "டாக்டர்கள்",
    "nurse": "செவிலியர்",
    "patient": "நோயாளி",
    "patients": "நோயாளிகள்",
    "medicine": "மருந்து",
    "medicines": "மருந்துகள்",
    "virus": "வைரஸ்",
    "corona": "கொரோனா",
    "covid": "கோவிட்",
    "vaccine": "தடுப்பூசி",
    "fever": "காய்ச்சல்",
    "ambulance": "ஆம்புலன்ஸ்",
    "icu": "தீவிர சிகிச்சைப் பிரிவு",
    "clinic": "கிளினிக்",
    "operation": "அறுவை சிகிச்சை",
    "surgery": "அறுவை சிகிச்சை",
    "bus": "பஸ்",
    "car": "கார்",
    "cars": "கார்கள்",
    "van": "வேன்",
    "lorry": "லாரி",
    "truck": "டிரக்",
    "train": "ரயில்",
    "flight": "விமானம்",
    "plane": "விமானம்",
    "airplane": "விமானம்",
    "airport": "விமான நிலையம்",
    "station": "நிலையம்",
    "railway": "ரயில்வே",
    "driver": "டிரைவர்",
    "pilot": "பைலட்",
    "petrol": "பெட்ரோல்",
    "diesel": "டீசல்",
    "gas": "எரிவாயு",
    "fuel": "எரிபொருள்",
    "road": "சாலை",
    "highway": "நெடுஞ்சாலை",
    "traffic": "போக்குவரத்து",
    "bridge": "பாலம்",

    # Finance, Numbers & Currency
    "bank": "வங்கி",
    "banks": "வங்கிகள்",
    "atm": "ஏடிஎம்",
    "loan": "கடன்",
    "tax": "வரி",
    "money": "பணம்",
    "cash": "ரொக்கம்",
    "rupee": "ரூபாய்",
    "rupees": "ரூபாய்",
    "dollar": "டாலர்",
    "dollars": "டாலர்கள்",
    "euro": "யூரோ",
    "gold": "தங்கம்",
    "silver": "வெள்ளி",
    "market": "சந்தை",
    "share market": "பங்குச் சந்தை",
    "stock": "பங்கு",
    "crore": "கோடி",
    "crores": "கோடி",
    "lakh": "லட்சம்",
    "lakhs": "லட்சம்",
    "million": "மில்லியன்",
    "millions": "மில்லியன்",
    "billion": "பில்லியன்",
    "billions": "பில்லியன்",
    "trillion": "டிரில்லியன்",
    "percent": "சதவீதம்",
    "percentage": "சதவீதம்",
    "km": "கிலோமீட்டர்",
    "kmh": "கிலோமீட்டர்",
    "kg": "கிலோகிராம்",
    "gram": "கிராம்",
    "grams": "கிராம்",
    "liter": "லிட்டர்",
    "liters": "லிட்டர்",
    "meter": "மீட்டர்",
    "meters": "மீட்டர்",

    # Sports
    "match": "போட்டி",
    "matches": "போட்டிகள்",
    "cricket": "கிரிக்கெட்",
    "football": "ஃபுட்பால்",
    "cup": "கோப்பை",
    "world cup": "உலகக் கோப்பை",
    "trophy": "கோப்பை",
    "team": "அணி",
    "teams": "அணிகள்",
    "player": "வீரர்",
    "players": "வீரர்கள்",
    "captain": "கேப்டன்",
    "coach": "பயிற்சியாளர்",
    "score": "ஸ்கோர்",
    "wicket": "விக்கெட்",
    "wickets": "விக்கெட்ஸ்",
    "run": "ரன்",
    "runs": "ரன்கள்",
    "over": "ஓவர்",
    "overs": "ஓவர்கள்",
    "six": "சிக்ஸர்",
    "four": "ஃபோர்",
    "century": "சதம்",
    "win": "வெற்றி",
    "loss": "தோல்வி",
    "final": "இறுதிப்போட்டி",
    "semi final": "அரையிறுதி",
    "champion": "சாம்பியன்",
    "champions": "சாம்பியன்கள்",
    "record": "சாதனை",
    "records": "சாதனைகள்",
    "olympics": "ஒலிம்பிக்",

    # Countries & Places
    "sri lanka": "இலங்கை",
    "srilanka": "இலங்கை",
    "india": "இந்தியா",
    "indian": "இந்திய",
    "colombo": "கொழும்பு",
    "jaffna": "யாழ்ப்பாணம்",
    "chennai": "சென்னை",
    "usa": "அமெரிக்கா",
    "america": "அமெரிக்கா",
    "uk": "இங்கிலாந்து",
    "china": "சீனா",
    "russia": "ரஷ்யா",
    "israel": "இஸ்ரேல்",
    "iran": "ஈரான்",
    "pakistan": "பாகிஸ்தான்",
    "technology": "தொழில்நுட்பம்",
    "tech": "தொழில்நுட்பம்",

    # Common English adjectives / everyday terms
    "super": "சூப்பர்",
    "mega": "மெகா",
    "ultra": "அல்ட்ரா",
    "star": "ஸ்டார்",
    "hero": "ஹீரோ",
    "history": "வரலாறு",
    "mystery": "மர்மம்",
    "secret": "ரகசியம்",
    "magic": "மேஜிக்",
    "world": "உலகம்",
    "new": "புதிய",
    "latest": "சமீபத்திய",
    "breaking": "முக்கிய",
    "breaking news": "முக்கிய செய்தி",
    "live": "நேரலை",
    "special": "சிறப்பு",
    "news": "செய்தி",
    "report": "அறிக்கை",
    "office": "அலுவலகம்",
    "school": "பள்ளி",
    "college": "கல்லூரி",
    "university": "பல்கலைக்கழகம்",
    "student": "மாணவர்",
    "students": "மாணவர்கள்",
    "teacher": "ஆசிரியர்",
    "exam": "தேர்வு",
    "exams": "தேர்வுகள்",
    "result": "முடிவு",
    "results": "முடிவுகள்",
    "alert": "எச்சரிக்கை",
    "warning": "எச்சரிக்கை",
    "danger": "ஆபத்து",
    "emergency": "அவசரநிலை",
    "accident": "விபத்து",
    "case": "வழக்கு",
    "arrest": "கைது"
}

# English uppercase letter names for acronym spelling (e.g. "FIR", "VIP", "USA", "UK")
LETTER_SPELL_MAP = {
    'A': 'ஏ', 'B': 'பி', 'C': 'சி', 'D': 'டி', 'E': 'இ',
    'F': 'எஃப்', 'G': 'ஜி', 'H': 'ஹெச்', 'I': 'ஐ', 'J': 'ஜே',
    'K': 'கே', 'L': 'எல்', 'M': 'எம்', 'N': 'என்', 'O': 'ஓ',
    'P': 'பி', 'Q': 'க்யூ', 'R': 'ஆர்', 'S': 'எஸ்', 'T': 'டி',
    'U': 'யு', 'V': 'வி', 'W': 'டபிள்யூ', 'X': 'எக்ஸ்', 'Y': 'ஒய்', 'Z': 'இசட்'
}

# Phonetic letter patterns for unknown English words
PHONETIC_PATTERNS = [
    (r'tion\b', 'ஷன்'),
    (r'sion\b', 'ஷன்'),
    (r'wonders\b', 'ஒண்டெர்ஸ்'),
    (r'wonder\b', 'ஒண்டர்'),
    (r'ing\b', 'யிங்'),
    (r'ed\b', 'ட்'),
    (r'er\b', 'அர்'),
    (r'or\b', 'அர்'),
    (r'ar\b', 'ஆர்'),
    (r'all\b', 'ஆல்'),
    (r'ght\b', 'ட்'),
    (r'ck', 'க்'),
    (r'sh', 'ஷ்'),
    (r'ch', 'ச்'),
    (r'th', 'த்'),
    (r'ph', 'ஃப்'),
    (r'wh', 'வ'),
    (r'ng', 'ங்'),
    (r'qu', 'க்வ'),
    (r'ee', 'ஈ'),
    (r'oo', 'ஊ'),
    (r'ea', 'ஈ'),
    (r'ai', 'ஐ'),
    (r'ay', 'ஏ'),
    (r'ou', 'அவு'),
    (r'ow', 'அவ்'),
    (r'b', 'ப்'),
    (r'c', 'க்'),
    (r'd', 'ட்'),
    (r'f', 'ஃப்'),
    (r'g', 'க்'),
    (r'h', 'ஹ்'),
    (r'j', 'ஜ்'),
    (r'k', 'க்'),
    (r'l', 'ல்'),
    (r'm', 'ம்'),
    (r'n', 'ன்'),
    (r'p', 'ப்'),
    (r'q', 'க்'),
    (r'r', 'ர்'),
    (r's', 'ஸ்'),
    (r't', 'ட்'),
    (r'v', 'வ்'),
    (r'w', 'வ்'),
    (r'x', 'க்ஸ்'),
    (r'y', 'ய்'),
    (r'z', 'ஸ்'),
    (r'a', 'அ'),
    (r'e', 'எ'),
    (r'i', 'இ'),
    (r'o', 'ஒ'),
    (r'u', 'உ')
]

def phonetic_fallback(word):
    """Fallback transliterator that converts any remaining English word into Tamil syllables."""
    w = word.lower()
    for pat, rep in PHONETIC_PATTERNS:
        w = re.sub(pat, rep, w)
    return w

def transliterate_english_to_tamil(text):
    """
    Cleanses and transliterates all English words, abbreviations, and symbols
    into natural spoken Tamil (Thanglish phonetics) so neural Tamil Edge-TTS
    reads every sentence smoothly without stumbling or skipping words.
    """
    if not text:
        return ""

    out = text

    # 1. Clean symbols to Tamil words
    out = out.replace("%", " சதவீதம் ")
    out = out.replace("$", " டாலர் ")
    out = out.replace("₹", " ரூபாய் ")
    out = out.replace("&", " மற்றும் ")
    out = out.replace("@", " அட் ")
    out = out.replace("#", " ")

    # 2. Separate glued digits and letters (e.g., '7wonders' -> '7 wonders', '4G' -> '4 G')
    out = re.sub(r'(\d+)([a-zA-Z]+)', r'\1 \2', out)
    out = re.sub(r'([a-zA-Z]+)(\d+)', r'\1 \2', out)

    # 3. Handle multi-word key phrases first (e.g. "black hole", "world cup", "breaking news")
    low_out = out.lower()
    for phrase, tamil_rep in sorted(ENGLISH_TO_TAMIL_DICT.items(), key=lambda x: -len(x[0])):
        if " " in phrase and phrase in low_out:
            # Case-insensitive phrase replacement
            pattern = re.compile(r'\b' + re.escape(phrase) + r'\b', re.IGNORECASE)
            out = pattern.sub(tamil_rep, out)

    # 4. Transliterate individual words
    def replace_word(match):
        raw_word = match.group(0)
        low = raw_word.lower()

        # Direct dictionary match
        if low in ENGLISH_TO_TAMIL_DICT:
            return ENGLISH_TO_TAMIL_DICT[low]

        # Acronyms (e.g. CCTV, FBI, USA, VIP, DMK)
        if raw_word.isupper() and 2 <= len(raw_word) <= 5:
            # Check if all letters are in spell map
            return "".join(LETTER_SPELL_MAP.get(c, c) for c in raw_word)

        # Single letters
        if len(raw_word) == 1:
            return LETTER_SPELL_MAP.get(raw_word.upper(), raw_word)

        # Phonetic syllables for unknown English words
        return phonetic_fallback(raw_word)

    out = re.sub(r'[a-zA-Z]+', replace_word, out)

    # 5. Clean up any duplicated spaces
    out = re.sub(r'[ \t]{2,}', ' ', out).strip()

    return out
