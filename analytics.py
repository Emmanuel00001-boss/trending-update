import json, os, threading, re
from datetime import datetime, date, timedelta
from collections import defaultdict

ANALYTICS_FILE = os.path.join(os.path.dirname(__file__), "analytics.json")
ONLINE_FILE    = os.path.join(os.path.dirname(__file__), "online.json")
lock = threading.Lock()

# ── Load / Save ──────────────────────────────────
def load_analytics():
    if os.path.exists(ANALYTICS_FILE):
        with open(ANALYTICS_FILE) as f:
            return json.load(f)
    return {"visits": []}

def save_analytics(data):
    with lock:
        with open(ANALYTICS_FILE, "w") as f:
            json.dump(data, f, indent=2)

def load_online():
    if os.path.exists(ONLINE_FILE):
        with open(ONLINE_FILE) as f:
            return json.load(f)
    return {}

def save_online(data):
    with lock:
        with open(ONLINE_FILE, "w") as f:
            json.dump(data, f, indent=2)

# ── Country flag ─────────────────────────────────
def country_flag(code):
    flags = {
        "ng":"🇳🇬","us":"🇺🇸","gb":"🇬🇧","gh":"🇬🇭","za":"🇿🇦",
        "ke":"🇰🇪","ca":"🇨🇦","au":"🇦🇺","in":"🇮🇳","de":"🇩🇪",
        "fr":"🇫🇷","br":"🇧🇷","it":"🇮🇹","es":"🇪🇸","jp":"🇯🇵",
        "cn":"🇨🇳","ru":"🇷🇺","mx":"🇲🇽","eg":"🇪🇬","et":"🇪🇹",
        "tz":"🇹🇿","ug":"🇺🇬","rw":"🇷🇼","cm":"🇨🇲","sn":"🇸🇳",
        "ci":"🇨🇮","ao":"🇦🇴","dz":"🇩🇿","ma":"🇲🇦","tn":"🇹🇳",
        "sd":"🇸🇩","ly":"🇱🇾","mz":"🇲🇿","zm":"🇿🇲","zw":"🇿🇼",
        "bj":"🇧🇯","bf":"🇧🇫","ml":"🇲🇱","ne":"🇳🇪","td":"🇹🇩",
        "pk":"🇵🇰","bd":"🇧🇩","id":"🇮🇩","ph":"🇵🇭","sg":"🇸🇬",
        "ae":"🇦🇪","sa":"🇸🇦","tr":"🇹🇷","nl":"🇳🇱","be":"🇧🇪",
        "se":"🇸🇪","no":"🇳🇴","fi":"🇫🇮","pl":"🇵🇱","pt":"🇵🇹",
        "ie":"🇮🇪","nz":"🇳🇿","ar":"🇦🇷","co":"🇨🇴","cl":"🇨🇱",
    }
    return flags.get(code.lower() if code else "", "🌍")

# ── Detect device type from User-Agent ───────────
def detect_device(ua):
    ua = ua.lower()
    if any(x in ua for x in ["iphone","android","mobile","blackberry","windows phone"]):
        return "📱 Mobile"
    elif any(x in ua for x in ["ipad","tablet"]):
        return "📟 Tablet"
    else:
        return "💻 Desktop"

# ── Detect traffic source from Referer ───────────
def detect_source(referer):
    if not referer or referer == "":
        return "Direct", "🔗"
    r = referer.lower()
    if "google" in r:       return "Google",    "🔍"
    if "facebook" in r:     return "Facebook",  "📘"
    if "instagram" in r:    return "Instagram", "📸"
    if "twitter" in r or "t.co" in r or "x.com" in r:
                            return "Twitter/X", "🐦"
    if "whatsapp" in r:     return "WhatsApp",  "💬"
    if "telegram" in r:     return "Telegram",  "✈️"
    if "youtube" in r:      return "YouTube",   "▶️"
    if "bing" in r:         return "Bing",      "🔎"
    if "yahoo" in r:        return "Yahoo",     "🟣"
    if "tiktok" in r:       return "TikTok",    "🎵"
    if "linkedin" in r:     return "LinkedIn",  "💼"
    return "Other",  "🌐"

# ── Get full geo info from IP ─────────────────────
def get_geo(ip):
    if ip in ("127.0.0.1", "::1", "localhost", ""):
        return {
            "country": "Local", "country_code": "local",
            "city": "Your Computer", "region": "",
            "flag": "🖥️", "isp": "Local"
        }
    try:
        import urllib.request
        url = f"http://ip-api.com/json/{ip}?fields=status,country,countryCode,regionName,city,isp,org"
        req = urllib.request.Request(url, headers={"User-Agent": "TrendingUpdate/1.0"})
        with urllib.request.urlopen(req, timeout=4) as r:
            d = json.loads(r.read())
            if d.get("status") == "success":
                code = d.get("countryCode", "")
                return {
                    "country":      d.get("country", "Unknown"),
                    "country_code": code,
                    "city":         d.get("city", "Unknown"),
                    "region":       d.get("regionName", ""),
                    "flag":         country_flag(code),
                    "isp":          d.get("org") or d.get("isp", "Unknown"),
                }
    except:
        pass
    return {"country":"Unknown","country_code":"","city":"Unknown","region":"","flag":"🌍","isp":"Unknown"}

# ── Record a visit ────────────────────────────────
def record_visit(ip, page, user_agent="", referer=""):
    geo    = get_geo(ip)
    device = detect_device(user_agent)
    source, source_icon = detect_source(referer)
    now    = datetime.now()
    data   = load_analytics()

    visit = {
        "ip":          ip,
        "page":        page,
        "country":     geo["country"],
        "country_code":geo["country_code"],
        "city":        geo["city"],
        "region":      geo["region"],
        "flag":        geo["flag"],
        "isp":         geo["isp"],
        "device":      device,
        "source":      source,
        "source_icon": source_icon,
        "referer":     referer[:120] if referer else "",
        "time":        now.isoformat(),
        "date":        now.strftime("%Y-%m-%d"),
        "hour":        now.hour,
    }

    data["visits"].append(visit)
    if len(data["visits"]) > 15000:
        data["visits"] = data["visits"][-15000:]
    save_analytics(data)

    # Update online list
    online = load_online()
    online[ip] = {
        "time":        now.isoformat(),
        "page":        page,
        "country":     geo["country"],
        "city":        geo["city"],
        "flag":        geo["flag"],
        "device":      device,
        "source":      source,
        "source_icon": source_icon,
    }
    cutoff = now - timedelta(minutes=3)
    online = {k: v for k, v in online.items()
              if datetime.fromisoformat(v["time"]) > cutoff}
    save_online(online)

# ── Full analytics summary ────────────────────────
def get_summary():
    data   = load_analytics()
    online = load_online()
    visits = data.get("visits", [])
    today  = date.today().isoformat()

    # Clean stale online
    now    = datetime.now()
    cutoff = now - timedelta(minutes=3)
    online = {k: v for k, v in online.items()
              if datetime.fromisoformat(v["time"]) > cutoff}
    save_online(online)

    today_visits = [v for v in visits if v.get("date") == today]

    # Visits per day (last 7 days)
    day_counts = defaultdict(int)
    for v in visits:
        day_counts[v.get("date", "")] += 1
    days = []
    for i in range(6, -1, -1):
        d = (date.today() - timedelta(days=i)).isoformat()
        days.append({"date": d, "count": day_counts[d]})

    # Visits per hour today
    hour_counts = defaultdict(int)
    for v in today_visits:
        hour_counts[v.get("hour", 0)] += 1
    hours = [{"hour": h, "count": hour_counts[h]} for h in range(24)]

    # Top countries
    country_counts = defaultdict(lambda: {"count": 0, "flag": "🌍"})
    for v in visits:
        c = v.get("country", "Unknown")
        country_counts[c]["count"] += 1
        country_counts[c]["flag"]   = v.get("flag", "🌍")
    top_countries = sorted(
        [{"country": k, "count": v["count"], "flag": v["flag"]}
         for k, v in country_counts.items()],
        key=lambda x: x["count"], reverse=True
    )[:10]

    # Top cities
    city_counts = defaultdict(lambda: {"count": 0, "flag": "🌍", "country": ""})
    for v in visits:
        city = v.get("city", "Unknown")
        city_counts[city]["count"]   += 1
        city_counts[city]["flag"]     = v.get("flag", "🌍")
        city_counts[city]["country"]  = v.get("country", "")
    top_cities = sorted(
        [{"city": k, "count": v["count"], "flag": v["flag"], "country": v["country"]}
         for k, v in city_counts.items() if k not in ("Unknown","")],
        key=lambda x: x["count"], reverse=True
    )[:10]

    # Traffic sources
    source_counts = defaultdict(lambda: {"count": 0, "icon": "🌐"})
    for v in visits:
        s = v.get("source", "Direct")
        source_counts[s]["count"] += 1
        source_counts[s]["icon"]   = v.get("source_icon", "🌐")
    top_sources = sorted(
        [{"source": k, "count": v["count"], "icon": v["icon"]}
         for k, v in source_counts.items()],
        key=lambda x: x["count"], reverse=True
    )[:8]

    # Device breakdown
    device_counts = defaultdict(int)
    for v in visits:
        device_counts[v.get("device", "💻 Desktop")] += 1
    devices = [{"device": k, "count": v}
               for k, v in sorted(device_counts.items(), key=lambda x: -x[1])]

    # Top pages
    page_counts = defaultdict(int)
    for v in visits:
        page_counts[v.get("page", "/")] += 1
    top_pages = sorted(
        [{"page": k, "count": v} for k, v in page_counts.items()],
        key=lambda x: x["count"], reverse=True
    )[:10]

    # Recent 50 visitors
    recent = sorted(visits, key=lambda x: x.get("time", ""), reverse=True)[:50]

    return {
        "online_now":    len(online),
        "online_list":   list(online.values()),
        "today_visits":  len(today_visits),
        "total_visits":  len(visits),
        "days":          days,
        "hours":         hours,
        "top_countries": top_countries,
        "top_cities":    top_cities,
        "top_sources":   top_sources,
        "devices":       devices,
        "top_pages":     top_pages,
        "recent":        recent,
    }
