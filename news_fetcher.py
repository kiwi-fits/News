import feedparser
import requests
import re
from bs4 import BeautifulSoup
from config import NEWS_FEEDS

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

# Blocked domains, sources, and generic portal slogans
BLOCKED_PATTERNS = [
    "newsfirst.lk",
    "newsfirst",
    "news 1st",
    "news1st",
    "நியூஸ்பர்ஸ்ட்",
    "powerofthepeople"
]

GENERIC_HOMEPAGE_PHRASES = [
    "home |",
    "truth first",
    "online tamil news",
    "tamil news live",
    "breaking news live",
    "epaper",
    "இ-பேப்பர்"
]

def scrape_direct_adaderana(limit=10):
    """Scrapes breaking stories directly from Ada Derana Tamil homepage."""
    stories = []
    seen = set()
    try:
        r = requests.get("https://tamil.adaderana.lk/", headers=HEADERS, timeout=10)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            for a in soup.find_all("a", href=True):
                href = a["href"]
                raw_t = re.sub(r"\s+", " ", a.get_text()).strip()
                t = re.sub(r"^(NEWS ALERT|BREAKING|முக்கிய செய்தி)\s*", "", raw_t, flags=re.I)
                t = re.sub(r"\b\d+[hm]\s+ago.*$", "", t).strip()
                tamil_chars = len(re.findall(r"[\u0b80-\u0bff]", t))
                if tamil_chars > 8 and "/news/" in href and href not in seen:
                    seen.add(href)
                    full_link = "https://tamil.adaderana.lk" + href if href.startswith("/") else href
                    # Extract title first sentence if mashed together
                    parts = t.split("!")
                    clean_title = (parts[0] + "!").strip() if len(parts) > 1 and len(parts[0]) > 15 else t[:120].strip()
                    stories.append({
                        "title": clean_title,
                        "summary": t,
                        "full_text": "",
                        "link": full_link,
                        "source": "Ada Derana Tamil (அட தெரண)",
                        "category": "breaking",
                        "image_url": None
                    })
                    if len(stories) >= limit:
                        break
    except Exception as e:
        print(f"Notice: Direct Ada Derana fetch error: {e}")
    return stories

def scrape_direct_virakesari(limit=10):
    """Scrapes breaking local news directly from Virakesari."""
    stories = []
    seen = set()
    try:
        r = requests.get("https://www.virakesari.lk/category/local", headers=HEADERS, timeout=10)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            for a in soup.find_all("a", href=True):
                href = a["href"]
                raw_t = re.sub(r"\s+", " ", a.get_text()).strip()
                t = re.sub(r"\d{1,2}\s+[A-Za-z]+,?\s+\d{4}.*$", "", raw_t).strip()
                tamil_chars = len(re.findall(r"[\u0b80-\u0bff]", t))
                if tamil_chars > 8 and "/article/" in href and href not in seen:
                    seen.add(href)
                    full_link = href if href.startswith("http") else "https://www.virakesari.lk" + href
                    stories.append({
                        "title": t,
                        "summary": t,
                        "full_text": "",
                        "link": full_link,
                        "source": "Virakesari (வீரகேசரி)",
                        "category": "local",
                        "image_url": None
                    })
                    if len(stories) >= limit:
                        break
    except Exception as e:
        print(f"Notice: Direct Virakesari fetch error: {e}")
    return stories

def scrape_direct_tamilwin(limit=10):
    """Scrapes breaking news directly from Tamilwin."""
    stories = []
    seen = set()
    try:
        r = requests.get("https://www.tamilwin.com/", headers=HEADERS, timeout=10)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            for a in soup.find_all("a", href=True):
                href = a["href"]
                t = re.sub(r"\s+", " ", a.get_text()).strip()
                tamil_chars = len(re.findall(r"[\u0b80-\u0bff]", t))
                if tamil_chars > 8 and ("/article/" in href or "/news/" in href) and href not in seen:
                    seen.add(href)
                    full_link = href if href.startswith("http") else "https://www.tamilwin.com" + href
                    stories.append({
                        "title": t,
                        "summary": t,
                        "full_text": "",
                        "link": full_link,
                        "source": "Tamilwin (தமிழ்வின்)",
                        "category": "breaking",
                        "image_url": None
                    })
                    if len(stories) >= limit:
                        break
    except Exception as e:
        print(f"Notice: Direct Tamilwin fetch error: {e}")
    return stories

def clean_html(raw_html):
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    text = soup.get_text(separator=" ")
    text = re.sub(r"\s+", " ", text).strip()
    return text

def extract_full_article_content(article_url):
    """
    Scrapes the target webpage to retrieve the entire news article body text.
    Filters out navigation, ads, headers, and social sharing widgets.
    """
    if not article_url:
        return ""
    if any(bp in article_url.lower() for bp in ["newsfirst"]):
        return ""
    try:
        resp = requests.get(article_url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            return ""

        soup = BeautifulSoup(resp.content, "html.parser")

        # Decompose scripts, styles, navigation, headers, footers
        for tag in soup(["script", "style", "nav", "header", "footer", "aside", "form"]):
            tag.decompose()

        # Target main article container if available
        container = soup.find("article") or soup.find(class_=re.compile(r"story-body|article-body|news-content|post-content|entry-content", re.I))
        target_root = container if container else soup

        paragraphs = []
        for p in target_root.find_all("p"):
            txt = p.get_text().strip()
            # Filter out copyright, short boilerplate, share links
            if len(txt) > 35 and not any(bad in txt.lower() for bad in ["copyright", "all rights reserved", "follow us", "subscribe", "bbc news தமிழ்"]):
                paragraphs.append(txt)

        full_story = "\n\n".join(paragraphs[:10])
        return full_story.strip()
    except Exception as e:
        print(f"Notice: Article scraping error: {e}")
        return ""

def fetch_latest_news(limit_per_feed=10, fetch_full_body=False):
    """
    Fetches latest Tamil news articles across trusted broadcasters.
    Prioritizes direct native scrapers (Ada Derana, Virakesari, Tamilwin)
    followed by high-reliability RSS feeds (Thinakaran, BBC News Tamil).
    """
    articles = []
    seen_links = set()

    # 1. Direct native scrapes from top Sri Lankan broadcasters
    direct_sources = [
        scrape_direct_adaderana(limit=limit_per_feed),
        scrape_direct_virakesari(limit=limit_per_feed),
        scrape_direct_tamilwin(limit=limit_per_feed)
    ]

    for source_stories in direct_sources:
        for s in source_stories:
            link = s.get("link", "").strip()
            title = s.get("title", "").strip()
            if not title or not link or link in seen_links:
                continue
            seen_links.add(link)
            if fetch_full_body:
                s["full_text"] = extract_full_article_content(link)
            articles.append(s)

    # 2. RSS Feeds (Thinakaran, BBC News Tamil, Google News)
    for feed_info in NEWS_FEEDS:
        name = feed_info["name"]
        url = feed_info["url"]
        category = feed_info.get("category", "breaking")

        # Skip RSS if already covered natively
        if "adaderana" in name.lower() or "virakesari" in name.lower():
            continue

        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            if resp.status_code != 200:
                continue

            feed = feedparser.parse(resp.content)
            for entry in feed.entries[:limit_per_feed]:
                link = entry.get("link", "").strip()
                title = entry.get("title", "").strip()
                summary = clean_html(entry.get("summary") or entry.get("description") or "")

                if not title or not link or link in seen_links:
                    continue

                # Exclude any blocked sites or generic taglines (e.g. Newsfirst)
                lower_title = title.lower()
                lower_link = link.lower()
                lower_name = name.lower()
                if any(bp in lower_title or bp in lower_link or bp in lower_name for bp in BLOCKED_PATTERNS):
                    continue

                # Exclude generic homepage/portal branding titles
                if any(gp in lower_title for gp in GENERIC_HOMEPAGE_PHRASES):
                    continue

                # Must contain genuine Tamil text (minimum 5 Tamil characters) to exclude English obituaries, ads, and portal headers
                tamil_char_count = len(re.findall(r'[\u0b80-\u0bff]', title))
                if tamil_char_count < 5:
                    continue

                seen_links.add(link)

                # Extract image if present in RSS entry
                img_url = None
                if "media_content" in entry and entry.media_content:
                    img_url = entry.media_content[0].get("url")
                elif "links" in entry:
                    for l in entry.links:
                        if "image" in l.get("type", ""):
                            img_url = l.get("href")
                            break

                full_text = ""
                if fetch_full_body:
                    full_text = extract_full_article_content(link)

                articles.append({
                    "title": title,
                    "summary": summary,
                    "full_text": full_text or summary,
                    "link": link,
                    "source": name,
                    "category": category,
                    "image_url": img_url
                })
        except Exception as e:
            print(f"Notice: Failed to fetch {name}: {e}")

    return articles
