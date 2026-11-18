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

def strip_channel_names(text):
    """
    Strips external news channel names (Virakesari, Ada Derana, BBC, News 1st, Google News, etc.)
    and publisher tags from scripts, headlines, captions, and comments.
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
        "adaderana.lk", "virakesari.lk", "newsfirst.lk", "bbc.com"
    ]
    cleaned = text
    # Strip any trailing publisher suffix (e.g., ' - DinaMani', ' - Polimer News')
    cleaned = re.sub(r'\s*[-–|]\s*[A-Za-z0-9\s.]+$', '', cleaned).strip()
    for ch in channel_keywords:
        cleaned = re.sub(r'[\s|–-]*' + re.escape(ch) + r'[\s|–-]*', ' ', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s*[-|–]\s*$', '', cleaned).strip()
    cleaned = re.sub(r'\s{2,}', ' ', cleaned).strip()
    return cleaned

def rewrite_with_gemini(headline, full_text, category="breaking"):
    """
    Calls Google Gemini to transform the news story into a compelling broadcast video script:
    - NO greetings like 'வணக்கம்'
    - NO external channel names
    - Pure, captivating broadcast storytelling
    """
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={GEMINI_API_KEY}"
        
        prompt = f"""
You are a top professional Tamil TV news anchor and broadcast scriptwriter.
Read the news article below and transform it into a captivating 30-40 second Facebook Reel news report.

NEWS ARTICLE:
Headline: {headline}
Category: {category}
Full Story Content:
{full_text[:2500]}

STRICT INSTRUCTIONS:
1. "reel_headline": A bold, punchy Tamil headline for the 9:16 vertical card (max 10-12 words).
   - NEVER include any external news channel name (Virakesari, Ada Derana, BBC, News 1st, etc.).
2. "voiceover_script": A fluent, natural spoken script in pure conversational broadcast Tamil (70 to 90 words, ~35 seconds).
   - CRITICAL RULE: DO NOT start with "வணக்கம்", "வணக்கம்! இன்றைய முக்கிய செய்தித் தொகுப்பு", or any greeting.
   - Start IMMEDIATELY with the core breaking news event or direct narrative line.
   - NEVER mention any news source, website, or channel name anywhere in the voiceover.
   - Explain the core developments, key numbers, and quotes directly.
   - End with a thought-provoking prompt to comment.
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
    Fallback broadcast script generator without greetings or channel names.
    """
    clean_h = strip_channel_names(headline)
    
    # Protect abbreviations like ரூ. and டொக்.
    protected_text = (full_text or "").replace("ரூ.", "ரூபாய் ").replace("டொக்.", "டாக்டர் ").replace("திரு.", "திரு ")
    
    # Split story into paragraphs
    paragraphs = [p.strip() for p in protected_text.split("\n\n") if len(p.strip()) > 30]
    
    body_points = []
    if paragraphs:
        for p in paragraphs[:3]:
            sentences = [s.strip() for s in re.split(r"[।!?]|\.(?!\d)", p) if len(s.strip()) > 25]
            if sentences:
                body_points.append(sentences[0])
    
    if body_points:
        middle_text = ". ".join(body_points) + "."
    else:
        middle_text = clean_h

    # Direct narration without 'வணக்கம்'
    voice_script = (
        f"{clean_h}. "
        f"{middle_text} "
        f"இந்த சம்பவம் குறித்த உங்கள் பார்வைகளை கீழே கமெண்ட் செய்யுங்கள். "
        f"உடனுக்குடன் உண்மைச் செய்திகளை அறிய எமது பக்கத்தை லைக் செய்து பின்தொடருங்கள்."
    )

    # Clean English visual prompt
    lower_text = (clean_h + " " + full_text).lower()
    if any(k in lower_text for k in ["வானிலை", "மழை", "வெள்ளம்", "புயல்"]):
        visual_prompt = "Cinematic aerial view of dramatic monsoon storm clouds over tropical coastal palms, 8k broadcast news style, clean no text"
    elif any(k in lower_text for k in ["பாராளுமன்ற", "அரசு", "ஜனாதிபதி", "அமைச்சர்", "தேர்தல்", "மோதி", "காந்தி"]):
        visual_prompt = "Cinematic photo of government leaders press conference, microphones and dramatic studio lighting, 8k news, clean no text"
    elif any(k in lower_text for k in ["பொருளாதாரம்", "ரூபா", "விலை", "தங்கம்", "கோடி"]):
        visual_prompt = "Cinematic macro shot of currencies, bank vault and financial chart graphs, broadcast business news, clean no text"
    elif any(k in lower_text for k in ["விபத்து", "ரயில்", "பேருந்து", "காவல்துறை", "கைது"]):
        visual_prompt = "Cinematic photo of city street with emergency police vehicle lights in evening, news photography, clean no text"
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
    Main entry point: Extracts full body if needed, then rewrites into video script.
    Guarantees no intro greetings in voiceover and no channel names.
    """
    headline = article.get("title", "")
    full_text = article.get("full_text") or article.get("summary") or ""
    link = article.get("link", "")
    category = article.get("category", "breaking")

    if len(full_text) < 150 and link:
        from news_fetcher import extract_full_article_content
        scraped = extract_full_article_content(link)
        if scraped:
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
    res["voiceover_script"] = strip_channel_names(cleaned_voice)
    res["engagement_question"] = strip_channel_names(res.get("engagement_question", ""))

    return res
