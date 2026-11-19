import os
import re
import json
import requests
from config import GEMINI_API_KEY

def strip_intro_greetings(text):
    """
    Strips 'வணக்கம்! இன்றைய முக்கிய செய்தித் தொகுப்பு.' and similar generic TV greetings
    so the spoken voiceover jumps straight into the news narrative immediately.
    """
    if not text:
        return ""
    patterns = [
        r'^\s*வணக்கம்[!,.]?\s*இன்றைய\s+முக்கிய\s+செய்தித்\s*தொகுப்பு[!,.]?\s*',
        r'^\s*வணக்கம்[!,.]?\s*இன்றைய\s+முக்கிய\s+செய்தி[!,.]?\s*',
        r'^\s*வணக்கம்[!,.]?\s*',
        r'^\s*இன்றைய\s+முக்கிய\s+செய்தித்\s*தொகுப்பு[!,.]?\s*',
        r'^\s*இன்றைய\s+முக்கிய\s+செய்தி[!,.]?\s*'
    ]
    cleaned = text
    for p in patterns:
        cleaned = re.sub(p, '', cleaned, flags=re.IGNORECASE)
    return cleaned.strip()

def strip_outro_ctas(text):
    """
    Strips comment/like/follow CTAs from the spoken voiceover so it ends purely on the news facts.
    """
    if not text:
        return ""
    patterns = [
        r'இந்த\s+சம்பவம்\s+குறித்த\s+உங்கள்\s+பார்வைகளை.*$',
        r'இந்த\s+செய்தி\s+குறித்த\s+உங்கள்.*$',
        r'உங்கள்\s+பார்வைகளை\s+கீழே\s+கமெண்ட்.*$',
        r'உங்கள்\s+கருத்தை\s+கீழே\s+கமெண்ட்.*$',
        r'கீழே\s+கமெண்ட்\s+செய்யுங்கள்.*$',
        r'உடனுக்குடன்\s+உண்மைச்\s+செய்திகளை\s+அறிய.*$',
        r'எமது\s+பக்கத்தை\s+லைக்\s+செய்து\s+பின்தொடருங்கள்.*$',
        r'எமது\s+பக்கத்தை\s+பின்தொடருங்கள்.*$',
        r'லைக்\s+செய்து\s+பின்தொடருங்கள்.*$'
    ]
    cleaned = text
    for p in patterns:
        cleaned = re.sub(p, '', cleaned, flags=re.IGNORECASE)
    return cleaned.strip()

def strip_channel_names(text):
    """
    Strips external news channel names (Virakesari, Ada Derana, BBC, News 1st, Google News, etc.)
    and publisher tags from scripts, headlines, captions, and comments, preserving line breaks.
    """
    if not text:
        return ""
    channel_keywords = [
        "Google News", "Google", "கூகுள் செய்தி",
        "Virakesari", "வீரகேசரி",
        "Ada Derana", "அட தெரண", "அடதெரண",
        "BBC News Tamil", "BBC Tamil", "BBC", "பிபிசி தமிழ்", "பிபிசி",
        "News 1st", "News First", "நியூஸ்பர்ஸ்ட்", "நியூஸ் 1st", "நியூஸ் பர்ஸ்ட்",
        "Thinakaran", "தினகரன்",
        "Tamilwin", "தமிழ்வின்",
        "DinaMani", "தினமணி", "Dinamalar", "தினமலர்",
        "Daily Thanthi", "தினத்தந்தி", "Polimer News", "பாலிமர்",
        "Jaffna News", "IBC Tamil", "ஐபிசி தமிழ்",
        "Sri Lanka Navy", "Navy",
        "adaderanatamil.lk", "adaderanatamil", "tamil.adaderana", "adaderana.lk", "virakesari.lk", "newsfirst.lk", "bbc.com"
    ]
    cleaned = text
    # Strip any trailing publisher suffix (e.g., ' - DinaMani', ' - Polimer News', ' - tamil.adaderana')
    cleaned = re.sub(r'[\s|–-]+[A-Za-z0-9\s.]+$', '', cleaned).strip()
    for ch in channel_keywords:
        cleaned = re.sub(r'[\s|–-]*' + re.escape(ch) + r'[\s|–-]*', ' ', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b(tamil|sri lanka navy|navy|virakesari|adaderana)\b', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s*[-|–]\s*$', '', cleaned).strip()
    # PRESERVE LINE BREAKS: only collapse horizontal whitespace, keep double newlines intact
    cleaned = re.sub(r'[ \t]{2,}', ' ', cleaned)
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned).strip()
    return cleaned

def strip_headline_from_voice(voice_script, headline):
    """
    Ensures the voiceover script NEVER repeats or starts with the card headline
    WHEN there is substantive story body content.
    If there is NO body inside the news (only the headline exists),
    it simply reads the title/headline without appending boilerplate phrases.
    """
    clean_h = strip_channel_names(headline or "").strip(" .?!|–-:")
    script = (voice_script or "").strip()

    # 1. Direct prefix match - only strip if there is substantial remaining body text
    if clean_h and script.startswith(clean_h):
        remaining = script[len(clean_h):].lstrip(" .?!|–-:\n")
        if len(remaining) >= 20:
            script = remaining
        else:
            # No body remaining: simply read the title itself
            script = clean_h

    # 2. Check if the first sentence echoes or repeats the headline
    parts = re.split(r'[\n।!?]|\.(?!\d)', script)
    if len(parts) > 1 and clean_h:
        first_sent = strip_channel_names(parts[0]).strip(" .?!|–-:")
        h_words = set(clean_h.split())
        f_words = set(first_sent.split())
        overlap = len(h_words & f_words) / max(len(h_words), 1) if h_words else 0
        if first_sent == clean_h or first_sent in clean_h or overlap > 0.70:
            remaining = script[len(parts[0]):].lstrip(" .?!|–-:\n")
            if len(remaining) >= 20:
                script = remaining

    final_text = script.strip()
    # Fallback to the title if text is empty
    if not final_text:
        final_text = clean_h

    return final_text

def rewrite_with_gemini(headline, full_text, category="breaking"):
    """
    Calls Google Gemini to transform the news story into a compelling broadcast video script:
    - NO greetings like 'வணக்கம்'
    - NO external channel names
    - Pure, captivating broadcast storytelling without headline duplication or artificial duration caps
    """
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={GEMINI_API_KEY}"
        
        prompt = f"""
You are a top professional Tamil TV news anchor and broadcast scriptwriter.
Read the ENTIRE news article below and transform it into a complete, captivating broadcast news report.

NEWS ARTICLE:
Headline: {headline}
Category: {category}
Full Story Content:
{full_text[:4000]}

STRICT INSTRUCTIONS:
1. "reel_headline": A bold, punchy Tamil headline for the 9:16 vertical card (max 10-12 words).
   - NEVER include any external news channel name (Virakesari, Ada Derana, BBC, News 1st, Thinakaran, etc.).
2. "voiceover_script": A rich, comprehensive spoken broadcast news report in pure, fluent Tamil covering the ENTIRE story from the article.
   - ABSOLUTELY DO NOT repeat the card headline at the beginning! Jump immediately into the detailed story facts and background.
   - DO NOT artificially restrict the length (no 25-35s limit). Produce a full, detailed broadcast script covering all key developments, figures, quotes, and background mentioned in the news article.
   - Paraphrase creatively in your own words like an expert professional TV journalist.
   - CRITICAL RULE: DO NOT start with "வணக்கம்", "வணக்கம்! இன்றைய முக்கிய செய்தித் தொகுப்பு", "இன்றைய", or any greeting.
   - Start IMMEDIATELY with the substantive event narration.
   - NEVER mention any news source, website, or channel name anywhere in the voiceover.
   - CRITICAL RULE: DO NOT include any outro call-to-actions (asking for comments/likes/follows). End naturally with the final factual outcome.
3. "visual_prompt": A detailed English prompt describing a cinematic, photorealistic visual scene matching this story (clean, 8k resolution, NO text, NO watermarks, NO logos).
4. "engagement_question": A thought-provoking Tamil question for the comments section (do not mention channel names).

Return ONLY a valid JSON object with keys: "reel_headline", "voiceover_script", "visual_prompt", "engagement_question".
"""
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.4, "responseMimeType": "application/json"}
        }
        
        resp = requests.post(url, json=payload, timeout=18)
        if resp.status_code == 200:
            data = resp.json()
            raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(raw_text)
    except Exception as e:
        print(f"Gemini API notice: {e}. Falling back to full-text mock mode.")
    return None

def rewrite_with_mock(headline, full_text, category="breaking"):
    """
    Intelligent broadcast script generator from the full news article body.
    Extracts all substantial developments, facts, and quotes across the ENTIRE story
    into a complete broadcast report without restricting duration and WITHOUT repeating the headline.
    """
    clean_h = strip_channel_names(headline)
    
    # 1. Clean up text and normalize newlines
    text = (full_text or "").replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("ரூ.", "ரூபாய் ").replace("டொக்.", "டாக்டர் ").replace("திரு.", "திரு ")
    
    # 2. Extract meaningful sentences across the entire article body
    raw_sentences = re.split(r'[\n।!?]|\.(?!\d)', text)
    
    clean_sentences = []
    h_words = set(clean_h.split())
    
    for s in raw_sentences:
        s_clean = strip_channel_names(s).strip()
        # Must be a substantial sentence, not boilerplate
        if len(s_clean) < 25:
            continue
        if any(b in s_clean.lower() for b in ["copyright", "share", "click", "பதிவிறக்கம்", "தொடர்பு கொள்ளவும்", "the post", "appeared first on"]):
            continue
        
        # Check if sentence repeats the headline
        s_norm = s_clean.strip(" .?!|–-:")
        if s_norm == clean_h.strip(" .?!|–-:") or s_norm in clean_h:
            continue
        s_words = set(s_clean.split())
        if h_words and len(s_words & h_words) / max(len(h_words), 1) > 0.70 and len(s_words) <= len(h_words) + 3:
            continue
            
        clean_sentences.append(s_clean)
    
    # 3. Build the full narrative story without repeating the headline
    if clean_sentences:
        # Take all substantive sentences (up to 15) to cover the whole news report
        voice_script = ". ".join(clean_sentences[:15]).strip()
        if not voice_script.endswith("."):
            voice_script += "."
    else:
        # If there is no body inside the news, simply read the title/headline
        voice_script = clean_h

    # 4. Clean English visual prompt
    lower_text = (clean_h + " " + text).lower()
    if any(k in lower_text for k in ["வானிலை", "மழை", "வெள்ளம்", "புயல்"]):
        visual_prompt = "Cinematic aerial view of dramatic monsoon storm clouds over tropical coastal palms, 8k broadcast news style, clean no text"
    elif any(k in lower_text for k in ["பாராளுமன்ற", "அரசு", "ஜனாதிபதி", "அமைச்சர்", "தேர்தல்", "மோதி", "காந்தி", "அரசியல்"]):
        visual_prompt = "Cinematic photo of government leaders press conference, microphones and dramatic studio lighting, 8k news, clean no text"
    elif any(k in lower_text for k in ["பொருளாதாரம்", "ரூபா", "விலை", "தங்கம்", "கோடி"]):
        visual_prompt = "Cinematic macro shot of currencies, bank vault and financial chart graphs, broadcast business news, clean no text"
    elif any(k in lower_text for k in ["விபத்து", "ரயில்", "பேருந்து", "காவல்துறை", "கைது", "யானை", "மீட்பு"]):
        visual_prompt = "Cinematic photo of emergency rescue operations in tropical terrain, broadcast news style, clean no text"
    elif any(k in lower_text for k in ["கிரிக்கெட்", "விளையாட்டு", "கால்பந்து"]):
        visual_prompt = "Cinematic wide angle photo of packed sports stadium under floodlights, broadcast television footage, clean no text"
    else:
        visual_prompt = "Cinematic photo of modern Sri Lanka urban city landscape, dramatic dusk lighting, broadcast television news style, clean no text"

    return {
        "reel_headline": clean_h,
        "voiceover_script": voice_script,
        "visual_prompt": visual_prompt,
        "engagement_question": "இந்த செய்தி குறித்த உங்கள் கருத்தைப் பகிருங்கள்!"
    }

def process_story(article):
    """
    Main entry point: Scrapes the full article body if needed, then rewrites into video script.
    Guarantees no intro greetings in voiceover and no channel names.
    """
    headline = article.get("title", "")
    full_text = article.get("full_text") or article.get("summary") or ""
    link = article.get("link", "")
    category = article.get("category", "breaking")

    # Always ensure full article content is scraped from the source website
    if len(full_text) < 200 and link:
        from news_fetcher import extract_full_article_content
        scraped = extract_full_article_content(link)
        if scraped and len(scraped) > len(full_text):
            full_text = scraped

    res = None
    if GEMINI_API_KEY:
        res = rewrite_with_gemini(headline, full_text, category)

    if not res:
        res = rewrite_with_mock(headline, full_text, category)

    # Post-processing sanitization
    res["reel_headline"] = strip_channel_names(res.get("reel_headline", ""))
    # Remove 'வணக்கம்' and greetings strictly from the voiceover script
    cleaned_voice = strip_intro_greetings(res.get("voiceover_script", ""))
    # Remove outro CTAs (asking for comments/likes/follows)
    cleaned_voice = strip_outro_ctas(cleaned_voice)
    # Remove headline duplication from voiceover audio
    cleaned_voice = strip_headline_from_voice(cleaned_voice, res["reel_headline"])
    res["voiceover_script"] = strip_channel_names(cleaned_voice)
    res["engagement_question"] = strip_channel_names(res.get("engagement_question", ""))

    return res
