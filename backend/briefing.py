from datetime import datetime
import feedparser


NEWS_FEEDS = [
    "https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en",
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://hnrss.org/frontpage",
]


def get_world_briefing(limit: int = 4):
    items = []

    for feed_url in NEWS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)

            for entry in feed.entries[:3]:
                items.append(
                    {
                        "title": entry.get("title", "No title"),
                        "link": entry.get("link", ""),
                        "source": feed.feed.get("title", "News"),
                    }
                )
        except Exception:
            continue

    briefing_items = items[:limit]

    if not briefing_items:
        return {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "summary": "World briefing is temporarily unavailable.",
            "items": [],
        }

    return {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "summary": "Here are the top updates right now.",
        "items": briefing_items,
    }