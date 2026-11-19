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

def fetch_latest_news(limit_per_feed=5, fetch_full_body=False):
    """
    Fetches latest Tamil news articles across trusted broadcasters.
    If fetch_full_body is True, scrapes the entire article webpage.
    """
    articles = []
    seen_links = set()

    for feed_info in NEWS_FEEDS:
        name = feed_info["name"]
        url = feed_info["url"]
        category = feed_info.get("category", "breaking")

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
