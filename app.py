from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from werkzeug.utils import secure_filename
from datetime import datetime
import json, os, uuid, re, threading

app = Flask(__name__)
app.secret_key = "trending-update-secret-2026"

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "static", "uploads")
DATA_FILE     = os.path.join(os.path.dirname(__file__), "data.json")
SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "settings.json")
ALLOWED_EXT   = {"png", "jpg", "jpeg", "gif", "webp"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

CATEGORIES = ["All","Politics","Business","Technology","Sports","Entertainment","Health","World","Obituary","Found Dead","Accident"]


# ── Data helpers ─────────────────────────────────
def load_posts():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f: return json.load(f)
    return []

def save_posts(posts):
    with open(DATA_FILE, "w") as f: json.dump(posts, f, indent=2)

def load_settings():
    defaults = {
        "site_name": "Trending Update",
        "tagline": "Breaking News & Latest Updates",
        "facebook_page": "", "adsterra_header": "",
        "adsterra_sidebar": "", "adsterra_footer": "",
        "google_verification": "", "admin_password": "admin123",
    }
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE) as f:
            defaults.update(json.load(f))
    return defaults

def save_settings(s):
    with open(SETTINGS_FILE, "w") as f: json.dump(s, f, indent=2)

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT

def slugify(text):
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")[:80]

# ── Analytics middleware ──────────────────────────
def get_real_ip():
    if request.headers.get("X-Forwarded-For"):
        return request.headers["X-Forwarded-For"].split(",")[0].strip()
    return request.remote_addr or "127.0.0.1"

@app.after_request
def track_visit(response):
    # Only track public pages, not admin/static
    path = request.path
    if (response.status_code == 200 and
        not path.startswith("/admin") and
        not path.startswith("/static") and
        not path.startswith("/api") and
        request.method == "GET"):
        try:
            from analytics import record_visit
            ip      = get_real_ip()
            ua      = request.headers.get("User-Agent", "")
            referer = request.headers.get("Referer", "")
            threading.Thread(target=record_visit, args=(ip, path, ua, referer), daemon=True).start()
        except: pass
    return response

# ── Public routes ────────────────────────────────
@app.route("/")
def home():
    posts    = load_posts()
    settings = load_settings()
    cat      = request.args.get("cat", "All")
    search   = request.args.get("q", "")
    if cat and cat != "All":
        posts = [p for p in posts if p.get("category") == cat]
    if search:
        posts = [p for p in posts if search.lower() in p.get("title","").lower()
                 or search.lower() in p.get("content","").lower()]
    posts    = sorted(posts, key=lambda x: x.get("created_at",""), reverse=True)
    featured = posts[0] if posts else None
    return render_template("home.html", posts=posts, featured=featured,
                           settings=settings, categories=CATEGORIES, active_cat=cat, search=search)

@app.route("/post/<slug>")
def post(slug):
    posts   = load_posts()
    settings= load_settings()
    article = next((p for p in posts if p.get("slug") == slug), None)
    if not article: return redirect(url_for("home"))
    # Increment views
    article["views"] = article.get("views", 0) + 1
    save_posts(posts)
    related = [p for p in posts if p.get("category") == article.get("category")
               and p.get("slug") != slug][:3]
    return render_template("post.html", post=article, related=related,
                           settings=settings, categories=CATEGORIES)

@app.route("/category/<cat>")
def category(cat):
    return redirect(url_for("home", cat=cat))

# ── Admin routes ─────────────────────────────────
@app.route("/admin", methods=["GET","POST"])
def admin_login():
    if session.get("admin"): return redirect(url_for("admin_dashboard"))
    error = ""
    if request.method == "POST":
        settings = load_settings()
        if request.form.get("password") == settings.get("admin_password","admin123"):
            session["admin"] = True
            return redirect(url_for("admin_dashboard"))
        error = "Wrong password. Try again."
    return render_template("admin_login.html", error=error)

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    return redirect(url_for("admin_login"))

@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get("admin"): return redirect(url_for("admin_login"))
    posts    = sorted(load_posts(), key=lambda x: x.get("created_at",""), reverse=True)
    settings = load_settings()
    # Quick analytics for dashboard
    try:
        from analytics import get_summary
        analytics = get_summary()
    except:
        analytics = {"online_now":0,"today_visits":0,"total_visits":0}
    return render_template("admin_dashboard.html", posts=posts,
                           settings=settings, categories=CATEGORIES, analytics=analytics)

@app.route("/admin/analytics")
def admin_analytics():
    if not session.get("admin"): return redirect(url_for("admin_login"))
    settings = load_settings()
    try:
        from analytics import get_summary
        data = get_summary()
    except Exception as e:
        data = {"error": str(e), "online_now":0,"today_visits":0,"total_visits":0,
                "days":[],"top_countries":[],"top_pages":[],"recent":[]}
    return render_template("admin_analytics.html", data=data, settings=settings)

@app.route("/api/analytics")
def api_analytics():
    if not session.get("admin"): return jsonify({"error":"unauthorized"}), 401
    try:
        from analytics import get_summary
        return jsonify(get_summary())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/admin/new", methods=["GET","POST"])
def admin_new():
    if not session.get("admin"): return redirect(url_for("admin_login"))
    settings = load_settings()
    if request.method == "POST":
        posts  = load_posts()
        title  = request.form.get("title","").strip()
        content= request.form.get("content","").strip()
        cat    = request.form.get("category","General")
        tags   = request.form.get("tags","").strip()
        slug   = slugify(title) + "-" + str(uuid.uuid4())[:6]
        image_url = ""
        if "image" in request.files:
            file = request.files["image"]
            if file and file.filename and allowed_file(file.filename):
                ext      = file.filename.rsplit(".",1)[1].lower()
                filename = f"{uuid.uuid4().hex}.{ext}"
                file.save(os.path.join(UPLOAD_FOLDER, filename))
                image_url = f"/static/uploads/{filename}"
        posts.insert(0,{"id":str(uuid.uuid4()),"title":title,"content":content,
                        "category":cat,"tags":tags,"slug":slug,"image":image_url,
                        "created_at":datetime.now().isoformat(),"views":0})
        save_posts(posts)
        return redirect(url_for("admin_dashboard"))
    return render_template("admin_post_form.html", post=None, settings=settings,
                           categories=CATEGORIES, action="New")

@app.route("/admin/edit/<post_id>", methods=["GET","POST"])
def admin_edit(post_id):
    if not session.get("admin"): return redirect(url_for("admin_login"))
    posts   = load_posts()
    settings= load_settings()
    article = next((p for p in posts if p["id"] == post_id), None)
    if not article: return redirect(url_for("admin_dashboard"))
    if request.method == "POST":
        article["title"]      = request.form.get("title","").strip()
        article["content"]    = request.form.get("content","").strip()
        article["category"]   = request.form.get("category","General")
        article["tags"]       = request.form.get("tags","").strip()
        article["updated_at"] = datetime.now().isoformat()
        if "image" in request.files:
            file = request.files["image"]
            if file and file.filename and allowed_file(file.filename):
                ext      = file.filename.rsplit(".",1)[1].lower()
                filename = f"{uuid.uuid4().hex}.{ext}"
                file.save(os.path.join(UPLOAD_FOLDER, filename))
                article["image"] = f"/static/uploads/{filename}"
        save_posts(posts)
        return redirect(url_for("admin_dashboard"))
    return render_template("admin_post_form.html", post=article, settings=settings,
                           categories=CATEGORIES, action="Edit")

@app.route("/admin/delete/<post_id>", methods=["POST"])
def admin_delete(post_id):
    if not session.get("admin"): return redirect(url_for("admin_login"))
    save_posts([p for p in load_posts() if p["id"] != post_id])
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/settings", methods=["GET","POST"])
def admin_settings():
    if not session.get("admin"): return redirect(url_for("admin_login"))
    settings = load_settings()
    saved = False
    if request.method == "POST":
        for key in ["site_name","tagline","facebook_page","adsterra_header",
                    "adsterra_sidebar","adsterra_footer","google_verification"]:
            settings[key] = request.form.get(key,"")
        new_pass = request.form.get("new_password","").strip()
        if new_pass: settings["admin_password"] = new_pass
        save_settings(settings)
        saved = True
    return render_template("admin_settings.html", settings=settings, saved=saved)

if __name__ == "__main__":
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    port = int(os.environ.get("PORT", 5001))
    print("\n✅  Trending Update is running!")
    print(f"👉  Website:  http://0.0.0.0:{port}")
    print(f"🔐  Admin:    http://0.0.0.0:{port}/admin")
    print(f"📊  Analytics:http://0.0.0.0:{port}/admin/analytics")
    print("🔑  Password: admin123\n")
    app.run(host="0.0.0.0", port=port, debug=False)
