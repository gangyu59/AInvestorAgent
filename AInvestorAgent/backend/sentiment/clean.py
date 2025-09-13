from datetime import datetime, timezone

def normalize_items(items: list[dict]) -> list[dict]:
    out = []
    for it in items:
        ts = it.get("published_at") or ""
        try:
            dt = datetime.fromisoformat(ts.replace("Z","+00:00"))
        except Exception:
            dt = datetime.now(timezone.utc)
        out.append({
            "title": (it.get("title") or "").strip(),
            "summary": (it.get("summary") or "").strip(),
            "url": (it.get("url") or "").strip(),
            "source": (it.get("source") or "").strip(),
            "published_at": dt,
        })
    return out
