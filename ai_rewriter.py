import os
import re
import json
import requests
from config import GEMINI_API_KEY

def clean_source_name(title):
    for s in ["| வீரகேசரி", "- Virakesari", "- Ada Derana", "| News 1st", "- BBC News Tamil"]:
        title = title.replace(s, "")
    return re.sub(r"\s+", " ", title).strip()

def rewrite_with_gemini(headline, full_text, category="breaking"):
    """
    Calls Google Gemini to transform the ENTIRE news story into a compelling broadcast video script.
    """
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={GEMINI_API_KEY}"
        
        prompt = f"""
You are a top Tamil TV news anchor and broadcast scriptwriter.
Read the ENTIRE news article below and transform it into a captivating 30-40 second Facebook Reel news report.

NEWS ARTICLE:
Headline: {headline}
Category: {category}
Full Story Content:
{full_text[:2500]}

INSTRUCTIONS:
1. "reel_headline": A bold, punchy Tamil headline for the 9:16 vertical card (max 10-12 words).
2. "voiceover_script": A fluent, natural TV news anchor spoken script in pure Tamil (70 to 95 words, ~35 seconds).
   - Start with a strong attention hook ("வணக்கம், இன்றைய முக்கிய செய்தி...")
   - Explain the core developments, numbers, and quotes from the full article.
   - Speak in conversational broadcast Tamil (like a live TV presenter).
   - End with a prompt to comment.
3. "visual_prompt": A detailed English prompt describing a cinematic, photorealistic visual scene matching this story.
4. "engagement_question": A thought-provoking Tamil question for the comments section.

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
    Synthesizes a full broadcast script from the entire news article body:
    Extracts key narrative sentences across multiple paragraphs.
    """
    clean_h = clean_source_name(headline)
    
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

    voice_script = (
        f"வணக்கம்! இன்றைய முக்கிய செய்தித் தொகுப்பு. "
        f"{clean_h}. "
        f"{middle_text} "
        f"இந்த சம்பவம் குறித்த உங்கள் பார்வைகளை கீழே கமெண்ட் செய்யுங்கள். "
        f"உடனுக்குடன் உண்மைச் செய்திகளை அறிய எமது பக்கத்தை லைக் செய்து பின்தொடருங்கள்."
    )

    # Derive AI Visual Prompt
    lower_text = (clean_h + " " + full_text).lower()
    if any(k in lower_text for k in ["வானிலை", "மழை", "வெள்ளம்", "புயல்"]):
        visual_prompt = "Cinematic aerial view of dramatic monsoon storm clouds over tropical coastal palms, 8k broadcast news style"
    elif any(k in lower_text for k in ["பாராளுமன்ற", "அரசு", "ஜனாதிபதி", "அமைச்சர்", "தேர்தல்", "மோதி", "காந்தி"]):
        visual_prompt = "Cinematic photo of government leaders press conference, microphones and dramatic studio lighting, 8k news"
    elif any(k in lower_text for k in ["பொருளாதாரம்", "ரூபா", "விலை", "தங்கம்", "கோடி"]):
        visual_prompt = "Cinematic macro shot of currencies, bank vault and financial chart graphs, broadcast business news"
    elif any(k in lower_text for k in ["விபத்து", "ரயில்", "பேருந்து", "காவல்துறை", "கைது"]):
        visual_prompt = "Cinematic photo of city street with emergency police vehicle lights in evening, news photography"
    elif any(k in lower_text for k in ["கிரிக்கெட்", "விளையாட்டு", "கால்பந்து"]):
        visual_prompt = "Cinematic wide angle photo of packed sports stadium under floodlights, broadcast television footage"
    else:
        visual_prompt = "Cinematic photo of modern Sri Lanka urban city landscape, dramatic dusk lighting, broadcast television news style"

    return {
        "reel_headline": clean_h,
        "voiceover_script": voice_script,
        "visual_prompt": visual_prompt,
        "engagement_question": "இந்த செய்தி குறித்த உங்கள் கருத்தைப் பகிருங்கள்!"
    }

def process_story(article):
    """
    Main entry point: Extracts full body if needed, then rewrites into video script.
    """
    headline = article.get("title", "")
    full_text = article.get("full_text") or article.get("summary") or ""
    link = article.get("link", "")
    category = article.get("category", "breaking")

    # If full_text is short and link exists, scrape the full article body now
    if len(full_text) < 150 and link:
        from news_fetcher import extract_full_article_content
        scraped = extract_full_article_content(link)
        if scraped:
            full_text = scraped

    if GEMINI_API_KEY:
        ai_res = rewrite_with_gemini(headline, full_text, category)
        if ai_res:
            return ai_res

    return rewrite_with_mock(headline, full_text, category)
