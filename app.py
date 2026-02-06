# pyre-ignore-all-errors
import sys
import html
import urllib.parse
import types

# ------------------------------------------------------------------------------
# HOTFIX: Polyfill 'cgi' module for Python 3.13+ compatibility
# The 'cgi' module was removed in Python 3.13, but 'feedparser' still depends on it.
# This code creates a fake 'cgi' module so imports don't crash.
# ------------------------------------------------------------------------------
if "cgi" not in sys.modules:
    mock_cgi = types.ModuleType("cgi")
    mock_cgi.escape = html.escape
    mock_cgi.parse_qsl = urllib.parse.parse_qsl
    # Add other attributes if specifically needed by feedparser, but usually just import is enough
    sys.modules["cgi"] = mock_cgi
# ------------------------------------------------------------------------------

from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime
import mimetypes
import logging
import feedparser
import re
import csv
import socket
import requests
from werkzeug.utils import secure_filename

# Set global timeout for socket operations
socket.setdefaulttimeout(10)
logging.basicConfig(level=logging.DEBUG)

# Use absolute paths for templates and static files to ensure Render finds them correctly
template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates'))
static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'static'))
app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)

# Initialize Whitenoise for static file serving in production
from whitenoise import WhiteNoise
app.wsgi_app = WhiteNoise(app.wsgi_app, root=static_dir)

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default-key-for-dev')
# Use absolute path for database to avoid issues in production
basedir = os.path.abspath(os.path.dirname(__file__))
if not os.path.exists(os.path.join(basedir, 'instance')):
    os.makedirs(os.path.join(basedir, 'instance'))

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'instance', 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@app.errorhandler(500)
def handle_500(e):
    return f"Internal Server Error: {str(e)}", 500

@app.route('/debug-info')
def debug_info():
    return {
        "cwd": os.getcwd(),
        "instance_exists": os.path.exists('instance'),
        "templates_exists": os.path.exists('templates'),
        "templates_content": os.listdir('templates') if os.path.exists('templates') else [],
        "db_uri": app.config['SQLALCHEMY_DATABASE_URI']
    }

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

class Issue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    issue_type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    media_filename = db.Column(db.String(100), nullable=True)
    media_type = db.Column(db.String(20), nullable=True) # 'image' or 'video'
    date_reported = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    author = db.relationship('User', backref='reported_issues')
    likes = db.relationship('Like', backref='issue', lazy='dynamic')
    comments = db.relationship('Comment', backref='issue', lazy='dynamic')

class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    issue_id = db.Column(db.Integer, db.ForeignKey('issue.id'), nullable=False)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    issue_id = db.Column(db.Integer, db.ForeignKey('issue.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, default=datetime.utcnow)
    commenter = db.relationship('User', backref='comments')

class Story(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    media_filename = db.Column(db.String(100), nullable=True)
    media_type = db.Column(db.String(20), nullable=True) # 'image', 'video'
    caption = db.Column(db.String(200), nullable=True)
    category = db.Column(db.String(50), nullable=False) # 'Climate', 'Pollution', 'Wildlife', 'Water', 'Other'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    likes = db.Column(db.Integer, default=0)
    is_approved = db.Column(db.Boolean, default=True) # For moderation
    
    author = db.relationship('User', backref='stories')

    @property
    def is_expired(self):
        from datetime import timedelta
        return datetime.utcnow() > self.created_at + timedelta(hours=24)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def home():
    return render_template('index.html')

def get_active_stories():
    from datetime import timedelta
    cutoff = datetime.utcnow() - timedelta(hours=24)
    # Fetch active and approved stories
    active_stories = Story.query.filter(Story.created_at > cutoff, Story.is_approved == True).all()
    
    grouped = {}
    for story in active_stories:
        cat = story.category
        if cat not in grouped: grouped[cat] = []
        grouped[cat].append({
            "id": story.id,
            "img": url_for('static', filename='uploads/' + story.media_filename) if story.media_filename else "https://images.unsplash.com/photo-1472214103451-9374bd1c798e?w=800",
            "text": story.caption,
            "user": story.author.full_name,
            "avatar": story.author.full_name[0],
            "type": story.media_type
        })
    return grouped

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter((User.username == username) | (User.email == username)).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password', 'error')
            
    return render_template('login.html')

# Local "Sheet" Setup (CSV)
def add_user_to_sheet(full_name, email, username):
    file_exists = os.path.isfile('user_records.csv')
    
    try:
        with open('user_records.csv', 'a', newline='') as f:
            writer = csv.writer(f)
            # Write header if new file
            if not file_exists:
                writer.writerow(['Full Name', 'Email', 'Username', 'Signup Date'])
            
            # Write user data
            writer.writerow([full_name, email, username, datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
        return True
    except Exception as e:
        print(f"Error saving to CSV: {e}")
        return False

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return redirect(url_for('signup'))
            
        if User.query.filter_by(username=username).first() or User.query.filter_by(email=email).first():
            flash('Username or Email already exists', 'error')
            return redirect(url_for('signup'))
            
        new_user = User(
            full_name=full_name,
            email=email,
            username=username,
            password_hash=generate_password_hash(password)
        )
        db.session.add(new_user)
        db.session.commit()
        
        # Save to Local Record Sheet
        add_user_to_sheet(full_name, email, username)
        
        flash('Account created successfully! Please login.', 'success')
        return redirect(url_for('login'))
        
    return render_template('signup.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/greenmind')
def greenmind():
    query = request.args.get('q', '')
    
    # Base feeds + dynamic search if query exists
    if query:
        # Improved search query
        search_query = f"{query} environment news"
        feeds = [(f"https://news.google.com/rss/search?q={search_query}&hl=en-IN&gl=IN&ceid=IN:en", "Search Result")]
    else:
        # High-quality direct sources + Google News filtered search
        feeds = [
            ("http://feeds.bbci.co.uk/news/science_and_environment/rss.xml", "Climate Change"),
            ("https://www.sciencedaily.com/rss/earth_climate/climate_change.xml", "Climate Science"),
            ("https://www.theguardian.com/environment/rss", "Global Policy"),
            ("https://rss.dw.com/xml/rss-en-environment", "Climate Science"),
            ("https://news.google.com/rss/search?q=site:thehindu.com+environment&hl=en-IN&gl=IN&ceid=IN:en", "India Environment"),
            ("https://news.google.com/rss/search?q=site:nationalgeographic.com+environment+wildlife&hl=en-US&gl=US&ceid=US:en", "Wildlife"),
            ("https://news.google.com/rss/search?q=site:unep.org+news&hl=en-US&gl=US&ceid=US:en", "Global Policy"),
            ("https://news.google.com/rss/search?q=site:climate.nasa.gov+news&hl=en-US&gl=US&ceid=US:en", "Climate Science"),
            ("https://news.google.com/rss/search?q=site:indianexpress.com+environment&hl=en-IN&gl=IN&ceid=IN:en", "India News")
        ]
    
    educational_news = []
    
    # Category-based learning database for educational expansion
    learning_repo = {
        "Climate Change": {
            "exp": "Climate change or 'Mausam Badlav' is the shifting of our Prithvi's natural cooling and heating cycles. Due to excessive carbon emissions, our Mother Earth is warming up at an alarming rate, affecting every season in our country.",
            "impact": "In India, this means unpredictable monsoons, heatwaves in the North, and rising sea levels in coastal areas like Mumbai and Kolkata, affecting our 'Annadata' (farmers).",
            "learning": "We must embrace clean energy and plant more 'Hariyali' to keep our environment cool and stable."
        },
        "Pollution": {
            "exp": "Pollution is the 'Pradushan' that poisons our air, water, and soil. From urban smog to plastic in our sacred rivers, it's a challenge that affects every Indian home.",
            "impact": "It leads to health issues for our children and elders, and destroys the fertility of our soil, making it harder for anything to grow.",
            "learning": "Small steps like 'Swachhata' (cleanliness) and reducing plastic solve the root cause of this hazard."
        },
        "Green Tech": {
            "exp": "Green Tech is our modern 'Vaigyanik' solution—using solar power, wind energy, and electric vehicles to build a 'Green India' without hurting nature.",
            "impact": "It creates new 'Harit' (green) jobs and ensures that our progress doesn't come at the cost of our children's future health.",
            "learning": "Supporting local solar initiatives and choosing eco-friendly travel are the keys to our success."
        },
        "India Environment": {
            "exp": "India's environment is unique, from the Himalayas to the Indian Ocean. Protecting our biodiversity and keeping our air clean is a national priority for our 'Sone ki Chidiya'.",
            "impact": "Air quality index (AQI) issues and river pollution directly impact our quality of life and the longevity of our heritage.",
            "learning": "Joining 'Jan Andolan' (people's movements) for cleanliness and tree plantation is the duty of every citizen."
        },
        "Wildlife": {
            "exp": "Wildlife or 'Vanya Jeev' are the gems of our forests. From the Tigers of Bengal to the Elephants of Kerala, they maintain the 'Prakriti' (Nature) balance.",
            "impact": "Losing even one species disrupts the natural cycle that gives us clean water, rich soil, and fresh air.",
            "learning": "Co-existing peacefully with animals and respecting their forest homes is the true Indian way of life."
        },
        "Water & Resources": {
            "exp": "Water or 'Jal' is the lifeline of India. Our rivers like Ganga, Yamuna, and Krishna are not just water bodies but symbols of our life and culture.",
            "impact": "Water scarcity affects our 'Pani' supply and hurts our crops, leading to struggles for our rural brothers and sisters.",
            "learning": "Rainwater harvesting and preventing river pollution are essential to ensure 'Har Ghar Jal' for everyone."
        }
    }

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    
    for url, category in feeds:
        try:
            response = requests.get(url, headers=headers, timeout=8)
            if response.status_code == 200:
                feed = feedparser.parse(response.content)
                
                limit = 10 if query else 3 # Increased limit for search
                count = 0
                for entry in feed.entries:
                    if count >= limit: break
                    
                    # Enhanced Summary Extraction
                    summary = entry.get('summary', '') or entry.get('description', '')
                    # Remove Google News extra HTML links
                    if '<font size="-1">' in summary:
                        summary = summary.replace('<font size="-1">', '').replace('</font>', '')
                    
                    # Clean tags
                    clean_text = re.sub('<[^<]+?>', ' ', summary)
                    # Normalize whitespace
                    clean_text = " ".join(clean_text.split())
                    
                    # If summary is still too short/empty, use title as backup
                    if len(clean_text) < 20: 
                        clean_text = entry.title

                    # Try to extract an image URL
                    image_url = None
                    if 'media_content' in entry:
                         # ... (image logic) ...
                         image_url = entry.media_content[0]['url']
                    elif 'links' in entry:
                        for link in entry.links:
                            if 'image' in link.get('type', ''):
                                image_url = link.href
                    
                    # ... (keeping existing image fallback logic) ...
                    if not image_url:
                        # Use Unsplash Source API for dynamic keyword matching
                        # This tells Unsplash to give us a random photo matching these keywords
                        
                        # Extract key terms for better image matching
                        text_for_matching = (entry.title + " " + clean_text).lower()
                        keywords = []
                        if "india" in text_for_matching: keywords.append("india")
                        if "river" in text_for_matching or "water" in text_for_matching: keywords.append("river")
                        if "animal" in text_for_matching or "wildlife" in text_for_matching: keywords.append("wildlife")
                        if "forest" in text_for_matching: keywords.append("forest")
                        if "pollution" in text_for_matching: keywords.append("pollution")
                        if "plastic" in text_for_matching: keywords.append("plastic")
                        if "solar" in text_for_matching: keywords.append("solar-panel")
                        if "climate" in text_for_matching: keywords.append("climate-change")
                        
                        # If we have specific keywords, use them. Otherwise default to nature.
                        search_term = ",".join(keywords) if keywords else "nature,environment"
                        
                        # Use a unique seed (entry title hash) so the image stays consistent for the same news item
                        # but changes for different items.
                        import hashlib
                        unique_sig = hashlib.md5(entry.title.encode('utf-8')).hexdigest()[:5]
                        
                        image_url = f"https://source.unsplash.com/800x600/?{search_term}&sig={unique_sig}"

                    # Robust categorization
                    title_lower = entry.title.lower()
                    if "india" in title_lower:
                        category_key = "India Environment"
                    elif any(w in title_lower for w in ["water", "river", "ocean", "sea", "flood", "drought"]):
                        category_key = "Water & Resources"
                    elif any(w in title_lower for w in ["wildlife", "animal", "species", "forest"]):
                        category_key = "Wildlife"
                    elif any(w in title_lower for w in ["tech", "solar", "energy", "electric"]):
                        category_key = "Green Tech"
                    elif any(w in title_lower for w in ["pollution", "plastic", "air", "waste"]):
                        category_key = "Pollution"
                    else:
                        category_key = category if category in learning_repo else "Climate Change"
                        
                    edu = learning_repo.get(category_key, learning_repo["Climate Change"])

                    # Dynamic AI Enrichment
                    ai_insight = f"About your search: Analysis indicates that this development in {category_key} is a high-priority environmental trend. "
                    if query:
                        ai_insight += f"The search for '{query}' specifically matches recent spikes in global awareness regarding resource sustainability."

                    educational_news.append({
                        'title': entry.title,
                        'category': category_key,
                        'image': image_url,
                        'intro': clean_text[:250] + ( "..." if len(clean_text) > 250 else ""),
                        'explanation': edu['exp'],
                        'impact': edu['impact'],
                        'learning_point': edu['learning'],
                        'ai_insight': ai_insight,
                        'source_url': entry.link, 
                        'internal_url': url_for('greenmind_detail', news_url=entry.link, title=entry.title, image=image_url),
                        'date': datetime.now().strftime("%d %B %Y"),
                        'location': 'India' if 'india' in entry.title.lower() else 'Global'
                    })
                    count += 1
            else:
                app.logger.warning(f"Feed error {response.status_code} for {url}")
        except Exception as e:
            app.logger.error(f"GreenMind Fetch Error for {url}: {e}")
            
    # Final Fallback
    if not educational_news:
        educational_news.append({
            'title': "Nature's Resilience: A Global Commitment",
            'category': "Climate Change",
            'image': "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=800&q=80",
            'intro': "In the face of rising global challenges, communities worldwide are coming together to protect our shared home through innovative conservation and sustainable practices.",
            'explanation': learning_repo["Climate Change"]["exp"],
            'impact': learning_repo["Climate Change"]["impact"],
            'learning_point': learning_repo["Climate Change"]["learning"],
            'ai_insight': "Sustainability is the only path forward for a healthy planet.",
            'date': datetime.now().strftime("%d %B %Y"),
            'location': "Global"
        })
            
    return render_template('news.html', news=educational_news, search_query=query)


@app.route('/greenmind/detail')
def greenmind_detail():
    news_url = request.args.get('news_url')
    news_title = request.args.get('title', 'Environmental Report')
    news_image = request.args.get('image')
    if not news_url:
        return redirect(url_for('greenmind'))
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    try:
        response = requests.get(news_url, headers=headers, timeout=10)
        # We don't use iframe because most sites block it (X-Frame-Options: DENY)
        # Instead, we extract the primary text content for a "Focus Mode"
        html_content = response.text
        
        # Simple extraction of paragraphs to avoid "Connection Refused"
        paragraphs = re.findall(r'<p>(.*?)</p>', html_content)
        cleaned_text = [re.sub('<[^<]+?>', '', p) for p in paragraphs if len(p) > 50]
        
        # Limit to the most relevant paragraphs for the focus view
        article_body = []
        for i in range(min(len(cleaned_text), 12)):
            article_body.append(cleaned_text[i])
        
        return render_template('news_reader.html', 
                             body=article_body, 
                             title=news_title, 
                             image=news_image,
                             source_url=news_url)
    except Exception as e:
        app.logger.error(f"Reader Error: {e}")
        return render_template('news_reader.html', 
                             error=True, 
                             source_url=news_url)


@app.route('/report', methods=['GET', 'POST'])
@login_required
def report():
    if request.method == 'POST':
        location = request.form.get('location')
        issue_type = request.form.get('issue_type')
        description = request.form.get('description')
        
        media_file = request.files.get('media')
        filename = None
        mtype = None
        
        if media_file and media_file.filename != '':
            filename = secure_filename(media_file.filename)
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            filename = f"{timestamp}_{filename}"
            
            upload_folder = os.path.join(app.static_folder, 'uploads')
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)
            
            media_file.save(os.path.join(upload_folder, filename))
            
            # Determine media type
            mime = mimetypes.guess_type(filename)[0]
            if mime:
                if mime.startswith('image'): mtype = 'image'
                elif mime.startswith('video'): mtype = 'video'
        
        new_issue = Issue(
            user_id=current_user.id,
            location=location,
            issue_type=issue_type,
            description=description,
            media_filename=filename,
            media_type=mtype
        )
        db.session.add(new_issue)
        db.session.commit()
        flash('Issue reported to community! Everyone can now see and interact with it.', 'success')
        return redirect(url_for('community'))
        
    return render_template('report.html')

@app.route('/community')
def community():
    issues = Issue.query.order_by(Issue.date_reported.desc()).all()
    return render_template('community.html', issues=issues)

@app.route('/like/<int:issue_id>', methods=['POST'])
@login_required
def like_issue(issue_id):
    existing_like = Like.query.filter_by(user_id=current_user.id, issue_id=issue_id).first()
    if existing_like:
        db.session.delete(existing_like)
    else:
        new_like = Like(user_id=current_user.id, issue_id=issue_id)
        db.session.add(new_like)
    db.session.commit()
    return redirect(url_for('community'))

@app.route('/comment/<int:issue_id>', methods=['POST'])
@login_required
def comment_issue(issue_id):
    text = request.form.get('comment_text')
    if text:
        new_comment = Comment(user_id=current_user.id, issue_id=issue_id, text=text)
        db.session.add(new_comment)
        db.session.commit()
    return redirect(url_for('community'))

@app.route('/my-reports')
@login_required
def my_reports():
    user_reports = Issue.query.filter_by(user_id=current_user.id).order_by(Issue.date_reported.desc()).all()
    return render_template('my_reports.html', reports=user_reports)



@app.route('/climate')
def climate():
    return render_template('climate.html')

@app.route('/pollution')
def pollution():
    return render_template('pollution.html')

@app.route('/wildlife')
def wildlife():
    return render_template('wildlife.html')

@app.route('/upload-story', methods=['POST'])
@login_required
def upload_story():
    media_file = request.files.get('media')
    category = request.form.get('category')
    caption = request.form.get('caption')
    
    if not media_file or media_file.filename == '':
        flash('No media selected', 'error')
        return redirect(url_for('home'))
        
    filename = secure_filename(media_file.filename)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"story_{timestamp}_{filename}"
    
    upload_folder = os.path.join(app.static_folder, 'uploads')
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
        
    media_file.save(os.path.join(upload_folder, filename))
    
    # Simple media type detection
    mime = mimetypes.guess_type(filename)[0]
    mtype = 'image'
    if mime and mime.startswith('video'): mtype = 'video'
    
    new_story = Story(
        user_id=current_user.id,
        media_filename=filename,
        media_type=mtype,
        category=category,
        caption=caption
    )
    db.session.add(new_story)
    db.session.commit()
    flash('Story posted! It will be visible for 24 hours.', 'success')
    return redirect(url_for('home'))

@app.route('/story-reaction/<int:story_id>', methods=['POST'])
@login_required
def story_reaction(story_id):
    story = Story.query.get_or_404(story_id)
    story.likes += 1
    db.session.commit()
    return {"status": "success", "likes": story.likes}

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    # Use debug=False in production, debug=True only in development
    debug_mode = os.environ.get('FLASK_ENV', 'production') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
