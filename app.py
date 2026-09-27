import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = 'skillforge_secret_key_2026_dev'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///skillforge.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

db = SQLAlchemy(app)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# -----------------------------------------------------------------------------
# Database Models
# -----------------------------------------------------------------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    branch = db.Column(db.String(100), nullable=True)
    year = db.Column(db.String(20), nullable=True)
    bio = db.Column(db.Text, nullable=True)
    profile_pic = db.Column(db.String(255), nullable=True, default='default_avatar.png')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    skills = db.relationship('Skill', backref='user', lazy=True, cascade="all, delete-orphan")
    projects = db.relationship('Project', backref='user', lazy=True, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Skill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    skill_name = db.Column(db.String(50), nullable=False)

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    tech_used = db.Column(db.String(200), nullable=True)
    github_link = db.Column(db.String(255), nullable=True)
    image = db.Column(db.String(255), nullable=True)
    likes = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# -----------------------------------------------------------------------------
# Context Processor
# -----------------------------------------------------------------------------
@app.context_processor
def inject_user():
    current_user = None
    if 'user_id' in session:
        current_user = User.query.get(session['user_id'])
    return dict(current_user=current_user)

# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------
@app.route('/')
def home():
    recent_projects = Project.query.order_by(Project.created_at.desc()).limit(6).all()
    user_count = User.query.count()
    project_count = Project.query.count()
    return render_template('home.html', recent_projects=recent_projects, user_count=user_count, project_count=project_count)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        branch = request.form.get('branch', '').strip()
        year = request.form.get('year', '').strip()
        bio = request.form.get('bio', '').strip()

        if not name or not email or not password:
            flash('Name, Email, and Password are required fields.', 'danger')
            return render_template('register.html')

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email address is already registered. Please login.', 'warning')
            return redirect(url_for('login'))

        new_user = User(
            name=name,
            email=email,
            branch=branch,
            year=year,
            bio=bio
        )
        new_user.set_password(password)

        # Profile Picture Upload
        if 'profile_pic' in request.files:
            file = request.files['profile_pic']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                unique_filename = f"user_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
                new_user.profile_pic = unique_filename

        db.session.add(new_user)
        db.session.commit()

        session['user_id'] = new_user.id
        session['user_name'] = new_user.name
        flash('Registration successful! Welcome to SkillForge.', 'success')
        return redirect(url_for('dashboard'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['user_name'] = user.name
            flash(f'Welcome back, {user.name}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'danger')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('home'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please login to access your dashboard.', 'warning')
        return redirect(url_for('login'))

    user = User.query.get_or_404(session['user_id'])
    return render_template('dashboard.html', user=user)

@app.route('/profile/edit', methods=['GET', 'POST'])
def edit_profile():
    if 'user_id' not in session:
        flash('Please login to edit your profile.', 'warning')
        return redirect(url_for('login'))

    user = User.query.get_or_404(session['user_id'])

    if request.method == 'POST':
        user.name = request.form.get('name', '').strip()
        user.branch = request.form.get('branch', '').strip()
        user.year = request.form.get('year', '').strip()
        user.bio = request.form.get('bio', '').strip()

        if 'profile_pic' in request.files:
            file = request.files['profile_pic']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                unique_filename = f"user_{user.id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
                user.profile_pic = unique_filename

        db.session.commit()
        session['user_name'] = user.name
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('edit_profile.html', user=user)

@app.route('/skills/add', methods=['POST'])
def add_skill():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    skill_name = request.form.get('skill_name', '').strip()
    if skill_name:
        # Check if already added
        existing = Skill.query.filter_by(user_id=session['user_id'], skill_name=skill_name).first()
        if not existing:
            new_skill = Skill(user_id=session['user_id'], skill_name=skill_name)
            db.session.add(new_skill)
            db.session.commit()
            flash(f'Skill "{skill_name}" added!', 'success')
        else:
            flash(f'Skill "{skill_name}" is already listed.', 'info')

    return redirect(url_for('dashboard'))

@app.route('/skills/delete/<int:skill_id>', methods=['POST'])
def delete_skill(skill_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    skill = Skill.query.get_or_404(skill_id)
    if skill.user_id == session['user_id']:
        db.session.delete(skill)
        db.session.commit()
        flash('Skill removed.', 'info')

    return redirect(url_for('dashboard'))

@app.route('/projects/new', methods=['GET', 'POST'])
def add_project():
    if 'user_id' not in session:
        flash('Please login to add a project.', 'warning')
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        tech_used = request.form.get('tech_used', '').strip()
        github_link = request.form.get('github_link', '').strip()

        if not title or not description:
            flash('Project title and description are required.', 'danger')
            return render_template('project_form.html', action='Add')

        project = Project(
            user_id=session['user_id'],
            title=title,
            description=description,
            tech_used=tech_used,
            github_link=github_link
        )

        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                unique_filename = f"proj_{session['user_id']}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
                project.image = unique_filename

        db.session.add(project)
        db.session.commit()
        flash('Project added successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('project_form.html', action='Add')

@app.route('/projects/edit/<int:project_id>', methods=['GET', 'POST'])
def edit_project(project_id):
    if 'user_id' not in session:
        flash('Please login to edit projects.', 'warning')
        return redirect(url_for('login'))

    project = Project.query.get_or_404(project_id)
    if project.user_id != session['user_id']:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        project.title = request.form.get('title', '').strip()
        project.description = request.form.get('description', '').strip()
        project.tech_used = request.form.get('tech_used', '').strip()
        project.github_link = request.form.get('github_link', '').strip()

        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                unique_filename = f"proj_{session['user_id']}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
                project.image = unique_filename

        db.session.commit()
        flash('Project updated successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('project_form.html', action='Edit', project=project)

@app.route('/projects/delete/<int:project_id>', methods=['POST'])
def delete_project(project_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    project = Project.query.get_or_404(project_id)
    if project.user_id == session['user_id']:
        db.session.delete(project)
        db.session.commit()
        flash('Project deleted.', 'info')

    return redirect(url_for('dashboard'))

@app.route('/projects/like/<int:project_id>', methods=['POST'])
def like_project(project_id):
    project = Project.query.get_or_404(project_id)
    project.likes += 1
    db.session.commit()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'likes': project.likes})

    return redirect(request.referrer or url_for('explore'))

@app.route('/explore')
def explore():
    search_query = request.args.get('q', '').strip()
    if search_query:
        # Search by project title, description, tech_used, or user's name/skills
        query = Project.query.join(User).filter(
            (Project.title.ilike(f'%{search_query}%')) |
            (Project.description.ilike(f'%{search_query}%')) |
            (Project.tech_used.ilike(f'%{search_query}%')) |
            (User.name.ilike(f'%{search_query}%')) |
            (User.branch.ilike(f'%{search_query}%'))
        ).order_by(Project.created_at.desc())
        projects = query.all()
    else:
        projects = Project.query.order_by(Project.created_at.desc()).all()

    return render_template('explore.html', projects=projects, search_query=search_query)

@app.route('/user/<int:user_id>')
def public_profile(user_id):
    user = User.query.get_or_404(user_id)
    return render_template('public_profile.html', user=user)

# -----------------------------------------------------------------------------
# Database Initializer & CLI command
# -----------------------------------------------------------------------------
def init_db():
    with app.app_context():
        db.create_all()
        # Seed dummy data if empty
        if User.query.count() == 0:
            seed_demo_data()

def seed_demo_data():
    u1 = User(
        name="Alex Rivera",
        email="alex@university.edu",
        branch="Computer Science & Engineering",
        year="3rd Year",
        bio="Passionate full-stack developer & AI enthusiast. Building web applications that solve real student problems."
    )
    u1.set_password("password123")

    u2 = User(
        name="Priya Sharma",
        email="priya@university.edu",
        branch="Robotics & Automation",
        year="4th Year",
        bio="Designing autonomous drones & embedded systems. Hardcore Python and C++ programmer."
    )
    u2.set_password("password123")

    db.session.add_all([u1, u2])
    db.session.commit()

    skills_u1 = ["Python", "Flask", "JavaScript", "Bootstrap 5", "SQL", "Git"]
    skills_u2 = ["C++", "ROS 2", "Python", "AutoCAD", "Arduino", "Computer Vision"]

    for s in skills_u1:
        db.session.add(Skill(user_id=u1.id, skill_name=s))

    for s in skills_u2:
        db.session.add(Skill(user_id=u2.id, skill_name=s))

    p1 = Project(
        user_id=u1.id,
        title="Campus Canteen Pre-order System",
        description="A web portal that allows students to pre-order food from campus canteens to avoid long queues during lunch breaks.",
        tech_used="Flask, SQLite, Bootstrap 5, JavaScript",
        github_link="https://github.com/example/canteen-app",
        likes=14
    )

    p2 = Project(
        user_id=u1.id,
        title="Smart Resume Analyzer",
        description="NLP tool that extracts keywords from job descriptions and matches them with student resumes to suggest targeted edits.",
        tech_used="Python, NLTK, Flask, HTML5",
        github_link="https://github.com/example/resume-analyzer",
        likes=27
    )

    p3 = Project(
        user_id=u2.id,
        title="Autonomous Obstacle Avoidance Rover",
        description="A 4-wheeled rover powered by Raspberry Pi and LiDAR sensors running ROS 2 node routines for real-time map generation.",
        tech_used="C++, ROS 2, Python, Raspberry Pi, LiDAR",
        github_link="https://github.com/example/rover-ros2",
        likes=42
    )

    db.session.add_all([p1, p2, p3])
    db.session.commit()

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
