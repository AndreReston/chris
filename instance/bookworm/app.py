from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
BASE_DIR = os.path.abspath(os.path.dirname(__file__))



app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static")
)
# Configure Flask to use the workspace `templates` and `static` folders
WORKSPACE_TEMPLATES = os.path.abspath(os.path.join(os.getcwd(), 'templates'))
# Static files for this app live under `instance/bookworm/static`
WORKSPACE_STATIC = os.path.abspath(os.path.join(os.getcwd(), 'instance', 'bookworm', 'static'))

app.secret_key = 'secretkey123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///wattpad_clone.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Use an absolute upload folder inside the project's `static/uploads`
app.config['UPLOAD_FOLDER'] = os.path.join(app.static_folder, 'uploads')
# Optional: base URL of an external reader site. If set, chapter links will go there.
# Example: 'https://reader.example.com' -> full chapter URL will be
# '{EXTERNAL_READER_BASE}/book/<book_id>/chapter/<chapter_id>'
app.config['EXTERNAL_READER_BASE'] = None
db = SQLAlchemy(app)

# -------------------- MODELS --------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    books = db.relationship('Book', backref='author', lazy=True)

class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    synopsis = db.Column(db.Text, nullable=False)
    cover_image = db.Column(db.String(200))
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    chapters = db.relationship('Chapter', backref='book', lazy=True)
    comments = db.relationship('Comment', backref='book', lazy=True)
    likes = db.relationship('BookLike', backref='book', lazy=True)

    @property
    def likes_count(self):
        return BookLike.query.filter_by(book_id=self.id, like_type='like').count()

    @property
    def dislikes_count(self):
        return BookLike.query.filter_by(book_id=self.id, like_type='dislike').count()

    @property
    def cover_url(self):
        """Return a browser-usable URL for the cover_image field.
        Handles remote URLs, absolute filesystem paths inside the static folder,
        or stored filenames under `static/uploads`.
        """
        val = self.cover_image
        if not val:
            return None
        
        if isinstance(val, str) and (val.startswith('http://') or val.startswith('https://') or val.startswith('//')):
            return val
        
        try:
            if os.path.isabs(val):
                rel = os.path.relpath(val, app.static_folder)
                return url_for('static', filename=rel.replace('\\', '/'))
        except Exception:
            pass
       
        try:
            return url_for('static', filename=f'uploads/{val}')
        except Exception:
            return None

class Chapter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    content = db.Column(db.Text, nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'))

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'))
    content = db.Column(db.Text, nullable=False)
    likes = db.Column(db.Integer, default=0)
    dislikes = db.Column(db.Integer, default=0)



class ChapterComment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    chapter_id = db.Column(db.Integer, db.ForeignKey('chapter.id'))
    content = db.Column(db.Text, nullable=False)
    likes = db.Column(db.Integer, default=0)
    dislikes = db.Column(db.Integer, default=0)

class BookLike(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'))
    like_type = db.Column(db.String(10))  # 'like' or 'dislike'



class ChapterLike(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    chapter_id = db.Column(db.Integer, db.ForeignKey('chapter.id'))
    like_type = db.Column(db.String(10))


@app.route('/')
def home():
    books = Book.query.all()
    return render_template('home.html', books=books)


@app.route('/signup', methods=['GET','POST'])
def signup():
    if request.method=='POST':
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        if User.query.filter_by(email=email).first():
            flash("Email already registered!")
            return redirect(url_for('signup'))
        user = User(username=username,email=email,password=password)
        db.session.add(user)
        db.session.commit()
        flash("Account created! Please log in.")
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password,password):
            session['user_id'] = user.id
            session['username'] = user.username
            flash("Logged in successfully!")
            return redirect(url_for('home'))
        else:
            flash("Invalid email or password")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully!")
    return redirect(url_for('home'))


@app.route('/create_book', methods=['GET','POST'])
def create_book():
    if 'user_id' not in session:
        flash("Please log in first")
        return redirect(url_for('login'))
    if request.method=='POST':
        title = request.form['title']
        synopsis = request.form['synopsis']
        
        cover_file = request.files.get('cover_file') or request.files.get('cover')
        cover_url = request.form.get('cover_url', '').strip()
        cover_filename = None
        if cover_file and cover_file.filename:
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            filename = secure_filename(cover_file.filename)
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            cover_file.save(save_path)
            cover_filename = filename
        elif cover_url:
            
            cover_filename = cover_url
        book = Book(title=title, synopsis=synopsis, cover_image=cover_filename, author_id=session['user_id'])
        db.session.add(book)
        db.session.commit()
        flash("Book created successfully!")
        return redirect(url_for('home'))
    return render_template('create_book.html')


@app.route('/create_chapter/<int:book_id>', methods=['GET','POST'])
def create_chapter(book_id):
    book = Book.query.get_or_404(book_id)
    if 'user_id' not in session or book.author_id != session['user_id']:
        flash("Unauthorized")
        return redirect(url_for('home'))
    if request.method=='POST':
        title = request.form['title']
        content = request.form['content']
        
        chapter = Chapter(title=title, content=content, book_id=book.id)
        db.session.add(chapter)
        db.session.commit()
        flash("Chapter added!")
        return redirect(url_for('view_book', book_id=book.id))
    return render_template('create_chapter.html', book=book)


@app.route('/book/<int:book_id>')
def view_book(book_id):
    book = Book.query.get_or_404(book_id)
    comments = Comment.query.filter_by(book_id=book.id).all()
    return render_template('view_book.html', book=book, comments=comments)



@app.route('/chapter/<int:chapter_id>')
def read_chapter(chapter_id):
    chapter = Chapter.query.get_or_404(chapter_id)
    book = chapter.book
    
    prev_chapter = Chapter.query.filter(Chapter.book_id==book.id, Chapter.id < chapter.id).order_by(Chapter.id.desc()).first()
    next_chapter = Chapter.query.filter(Chapter.book_id==book.id, Chapter.id > chapter.id).order_by(Chapter.id.asc()).first()
    
    like_users = User.query.join(ChapterLike, User.id==ChapterLike.user_id).filter(ChapterLike.chapter_id==chapter.id, ChapterLike.like_type=='like').all()
    dislike_users = User.query.join(ChapterLike, User.id==ChapterLike.user_id).filter(ChapterLike.chapter_id==chapter.id, ChapterLike.like_type=='dislike').all()
    like_user_list = [{'id': u.id, 'username': u.username} for u in like_users]
    dislike_user_list = [{'id': u.id, 'username': u.username} for u in dislike_users]

    
    comment_rows = db.session.query(ChapterComment, User).join(User, ChapterComment.user_id==User.id).filter(ChapterComment.chapter_id==chapter.id).order_by(ChapterComment.id.asc()).all()
    chapter_comments = []
    for cc, user in comment_rows:
        chapter_comments.append({
            'id': cc.id,
            'user_id': user.id,
            'username': user.username,
            'content': cc.content,
            'likes': cc.likes,
            'dislikes': cc.dislikes
        })

    likes = len(like_user_list)
    dislikes = len(dislike_user_list)

    return render_template('read_chapter.html', chapter=chapter, book=book, prev=prev_chapter, next=next_chapter, likes=likes, dislikes=dislikes, like_users=like_user_list, dislike_users=dislike_user_list, chapter_comments=chapter_comments)


@app.route('/comment/<int:book_id>', methods=['POST'])
def comment(book_id):
    if 'user_id' not in session:
        flash("Please log in first")
        return redirect(url_for('login'))
    content = request.form['content']
    new_comment = Comment(user_id=session['user_id'], book_id=book_id, content=content)
    db.session.add(new_comment)
    db.session.commit()
    flash("Comment posted!")
    return redirect(url_for('view_book', book_id=book_id))



@app.route('/chapter_comment/<int:chapter_id>', methods=['POST'])
def chapter_comment(chapter_id):
    if 'user_id' not in session:
        flash("Please log in first")
        return redirect(url_for('login'))
    content = request.form['content']
    new_comment = ChapterComment(user_id=session['user_id'], chapter_id=chapter_id, content=content)
    db.session.add(new_comment)
    db.session.commit()
    flash("Comment posted!")
    chap = Chapter.query.get_or_404(chapter_id)
    return redirect(url_for('read_chapter', chapter_id=chapter_id))


@app.route('/like_book/<int:book_id>')
def like_book(book_id):
    if 'user_id' not in session:
        flash("Login first!")
        return redirect(url_for('login'))
    like = BookLike.query.filter_by(user_id=session['user_id'], book_id=book_id).first()
    if like:
        like.like_type = 'like'
    else:
        db.session.add(BookLike(user_id=session['user_id'], book_id=book_id, like_type='like'))
    db.session.commit()
    return redirect(request.referrer)

@app.route('/dislike_book/<int:book_id>')
def dislike_book(book_id):
    if 'user_id' not in session:
        flash("Login first!")
        return redirect(url_for('login'))
    like = BookLike.query.filter_by(user_id=session['user_id'], book_id=book_id).first()
    if like:
        like.like_type = 'dislike'
    else:
        db.session.add(BookLike(user_id=session['user_id'], book_id=book_id, like_type='dislike'))
    db.session.commit()
    return redirect(request.referrer)

@app.route('/like_comment/<int:comment_id>')
def like_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    comment.likes += 1
    db.session.commit()
    return redirect(request.referrer)

@app.route('/dislike_comment/<int:comment_id>')
def dislike_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    comment.dislikes += 1
    db.session.commit()
    return redirect(request.referrer)



@app.route('/like_chapter/<int:chapter_id>')
def like_chapter(chapter_id):
    if 'user_id' not in session:
        flash("Login first!")
        return redirect(url_for('login'))
    like = ChapterLike.query.filter_by(user_id=session['user_id'], chapter_id=chapter_id).first()
    if like:
        like.like_type = 'like'
    else:
        db.session.add(ChapterLike(user_id=session['user_id'], chapter_id=chapter_id, like_type='like'))
    db.session.commit()
    return redirect(request.referrer)

@app.route('/dislike_chapter/<int:chapter_id>')
def dislike_chapter(chapter_id):
    if 'user_id' not in session:
        flash("Login first!")
        return redirect(url_for('login'))
    like = ChapterLike.query.filter_by(user_id=session['user_id'], chapter_id=chapter_id).first()
    if like:
        like.like_type = 'dislike'
    else:
        db.session.add(ChapterLike(user_id=session['user_id'], chapter_id=chapter_id, like_type='dislike'))
    db.session.commit()
    return redirect(request.referrer)



@app.route('/like_chapter_comment/<int:comment_id>')
def like_chapter_comment(comment_id):
    c = ChapterComment.query.get_or_404(comment_id)
    c.likes += 1
    db.session.commit()
    return redirect(request.referrer)

@app.route('/dislike_chapter_comment/<int:comment_id>')
def dislike_chapter_comment(comment_id):
    c = ChapterComment.query.get_or_404(comment_id)
    c.dislikes += 1
    db.session.commit()
    return redirect(request.referrer)


@app.route('/profile/<int:user_id>')
def profile(user_id):
    user = User.query.get_or_404(user_id)
    books = Book.query.filter_by(author_id=user.id).all()
    return render_template('profile.html', user=user, books=books)


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash("Login first!")
        return redirect(url_for('login'))
    books = Book.query.filter_by(author_id=session['user_id']).all()
    return render_template('dashboard.html', books=books)


@app.route('/search')
def search():
    query = request.args.get('q','')
    books = Book.query.filter(Book.title.contains(query)).join(User).all()
    return render_template('home.html', books=books)


@app.route('/book_data/<int:book_id>')
def book_data(book_id):
    book = Book.query.get_or_404(book_id)
    
    base = app.config.get('EXTERNAL_READER_BASE')
    for c in book.chapters:
        ch = {'id': c.id, 'title': c.title, 'content': c.content}
        if base:
           
            ch['external_url'] = f"{base.rstrip('/')}/book/{book.id}/chapter/{c.id}"
        else:
            ch['external_url'] = None
        chapters.append(ch)
    
    if book.cover_image:
        
        try:
            if os.path.isabs(book.cover_image):
                rel = os.path.relpath(book.cover_image, app.static_folder)
                cover_url = url_for('static', filename=rel.replace('\\', '/'))
            else:
                # treat stored value as filename under uploads
                cover_url = url_for('static', filename=f'uploads/{book.cover_image}')
        except Exception:
            cover_url = None

    return jsonify({
        'id': book.id,
        'title': book.title,
        'synopsis': book.synopsis,
        'cover_image': cover_url,
        'chapters': chapters
    })

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
