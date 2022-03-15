import os
import os.path
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, send_from_directory, url_for
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import guide, error, login_required
from werkzeug.utils import secure_filename

"""
Uses parts of CS50: Finance

http://cdn.cs50.net/2020/fall/psets/9/finance/finance.zip

Flask file I/O

https://flask.palletsprojects.com/en/1.1.x/patterns/fileuploads/
"""

# Configure application
app = Flask(__name__)

# Use path for /audio folder here
UPLOAD_FOLDER = '/home/ubuntu/project/harmony/audio'
ALLOWED_EXTENSIONS = {'mp3', 'wav'}

# Configure file upload folder
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///harmony.db")

GENRES = [
    "Alternative",
    "Blues",
    "Carribean",
    "Classical",
    "EDM",
    "Folk",
    "Funk",
    "Gospel",
    "Indie",
    "Jazz",
    "Latin",
    "Metal",
    "Pop",
    "Punk",
    "R&B",
    "Rap",
    "Reggae",
    "Rock"
]


@app.route("/")
@login_required
def home():
    """Show Homepage"""
    
    # Queries for posts of all users followed by user
    posts = db.execute("SELECT id, caption, type, time, user_id, name, extension FROM posts JOIN follow ON user_id=followed WHERE follower= ? ORDER BY time DESC", 
                       session["user_id"])
                       
    # Sets username
    for post in posts:
        post["username"] = db.execute("SELECT username FROM users WHERE id=?", post["user_id"])[0]["username"]

    return render_template("home.html", posts=posts)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""
    
    # Forget any user_id and username
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        
        username = request.form.get("username")
        password = request.form.get("password")

        # Username not submitted
        if not username:
            return guide("Must provide username", "/login")

        # Password not submitted
        elif not password:
            return guide("Must provide password", "/login")

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", username)

        # Username does not exist or password is incorrect
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], password):
            return guide("Incorrect username or password", "/login")

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        # Username is already taken
        if db.execute("SELECT username FROM users WHERE username = ?", username):
            return guide("Username is not available", "/register")

        # Username not submitted
        if not username:
            return guide("Must provide username", "/register")
            
        # Username is too long
        if len(username) > 15:
            return guide("Username too long", "/register")

        # Password not submitted
        elif not password:
            return guide("Must provide password", "/register")

        # Ensure passwords are the same
        elif password != request.form.get("confirmation"):
            return guide("Passwords must match", "/register")

        # Inserts username and password into SQL database
        db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", username, generate_password_hash(password))

        # Remember which user has logged in
        session["user_id"] = db.execute("SELECT id FROM users WHERE username = ?", username)[0]["id"]

        # Directs user to fill out additional information for profile
        return render_template("information.html", genres=GENRES, user_genres=[], bio="")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")
        
        
@app.route("/information", methods=["GET", "POST"])
@login_required
def information():
    """Records genres of interest and bio of user"""
    
    user_id = session["user_id"]
    
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        
        user_genres = request.form.getlist("genre")
        bio = request.form.get("bio")
        
        # Validates genres
        for genre in user_genres:
            if genre not in GENRES:
                return error("Invalid genre", 400)
        
        # Concatenates genres into single string
        genres = ", ".join(user_genres)
        
        # Updates user's bio and genres in SQL database
        db.execute("UPDATE users SET genres = ?, bio = ? WHERE id = ?", genres, bio, user_id)
        
        return redirect("/profile")
    
    # User reached route via GET (as by clicking a link or via redirect)    
    else:
        user_info = db.execute("SELECT bio, genres FROM users WHERE id = ?", user_id)[0]
        user_genres = str(user_info["genres"]).split(", ")
        
        # Pre-fills form with user's bio and genres of interest
        return render_template("information.html", genres=GENRES, user_genres=user_genres, bio=user_info["bio"])


@app.route("/profile")
@login_required
def profile():
    """Show user profile"""
    
    username = request.args.get("user")
    
    # User specified by form    
    if username:
        # Queries for user with matching username    
        rows = db.execute("SELECT * FROM users WHERE username = ?", username)
            
        # Ensures user exists
        if len(rows) != 1:
            return error("Could not find user", 400)
                
        user = rows[0]
        
        # Queries follow for current user following user
        following = db.execute("SELECT * FROM follow WHERE follower = ? AND followed = ?", session["user_id"], user["id"])
        
    # Defaults to current user
    else:
        user = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])[0]
        following = []
        
    # Queries for user's posts
    posts = db.execute("SELECT id, caption, type, time, name, extension FROM posts WHERE user_id = ? ORDER BY time DESC", user["id"])
        
    # Shows profile associated with user
    return render_template("profile.html", user=user, following=following, posts=posts)
    

# https://flask.palletsprojects.com/en/1.1.x/patterns/fileuploads/
# Returns file validity
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    
@app.route("/post", methods=["GET", "POST"])
@login_required
def post():
    """Create post
    
       Uses code from:
       
       https://flask.palletsprojects.com/en/1.1.x/patterns/fileuploads/
    """
    
    curr_user_id = session["user_id"]
    
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        
        file = request.files.get("audio")
        
        # Ensure file is selelcted
        if not file:
            return guide("Must select file", "/profile")
            
        # Ensure file has correct extension    
        if not allowed_file(file.filename):
            return guide("File must be .wav or .mp3", "/profile")
        
        if file.content_type == "audio/mpeg":
            extension = ".mp3"
        else:
            extension = ".wav"
        
        # Adds post to database
        db.execute("INSERT INTO posts (user_id, type, name, caption, extension) VALUES (?, ?, ?, ?, ?)", 
                   curr_user_id, file.content_type, file.filename, request.form.get("caption"), extension)
        
        # Creates unique file name to save
        filename = str(db.execute("SELECT id FROM posts WHERE name=?", file.filename)[0]["id"]) + extension
        
        # Updates filename
        db.execute("UPDATE posts SET name=? WHERE name=?", filename, file.filename)
            
        # Saves file in /audio
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                
        return redirect("/profile")
    
    # User reached route via GET (as by clicking a link or via redirect)    
    else:
        return redirect("/profile")
        
        
# Generates link for filename    
@app.route('/uploads/<filename>')
@login_required
def upload(filename):
    return send_from_directory(os.path.join(app.config['UPLOAD_FOLDER']), filename)
    
        
@app.route("/follow", methods=["GET", "POST"])
@login_required
def follow():
    """Follows or unfollows user"""
    
    # User reached via POST (as by submitting a form via POST)
    if request.method == "POST":
        
        curr_user_id = session["user_id"]
        
        # Gets command (follow or unfollow) with username (not current user)
        follow = request.form.get("follow").split(" ")
        
        # Validates form input 
        if len(follow) != 2: 
            return error("Invalid input", 400)
        
        command = follow[0]
        
        # Queries for user with matching username
        rows = db.execute("SELECT * FROM users WHERE username = ?", follow[1])
        
        # Ensures user exists
        if len(rows) != 1:
            return error("Could not find user", 400)
            
        user = rows[0]
        user_id = user["id"]
        
        # Ensures user is not current user
        if user_id == curr_user_id:
            return error("Cannot follow/unfollow yourself", 400)
        
        # Queries follow for current user following user
        following = db.execute("SELECT * FROM follow WHERE follower = ? AND followed = ?", curr_user_id, user_id)
        
        # Queries for user's posts
        posts = db.execute("SELECT id, caption, type, time, name, extension FROM posts WHERE user_id = ? ORDER BY time DESC", user["id"])
            
        if command == "follow":
            # User already followed
            if len(following) != 0:
                return error("Already following user", 400)
            # Updates follow and reloads profile
            else:
                db.execute("INSERT INTO follow (follower, followed) VALUES (?, ?)", curr_user_id, user_id)
                return render_template("profile.html", user=user, following=[{'follower': curr_user_id, 'followed': user_id}], posts=posts)
                
        if command == "unfollow":
            # User not followed
            if len(following) != 1:
                return error("Not following user", 400)
            # Updates follow and reloads profile
            else:
                db.execute("DELETE FROM follow WHERE follower = ? AND followed = ?", curr_user_id, user_id)
                return render_template("profile.html", user=user, following=[])
        
        # Command not follow or unfollow
        else:
            return error("Invalid command", 400)

    
@app.route("/messages", methods=["GET", "POST"])
@login_required
def messages():
    """Show messages"""
    
    curr_user_id = session["user_id"]
    
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        
        username = request.form.get("username")
        
        # Username not submitted
        if not username:
            return guide("Must provide username", "/messages")
        
        # Queries for user with matching username
        rows = db.execute("SELECT id, username FROM users WHERE username = ?", username)
        
        # Ensures user exists
        if len(rows) != 1:
            return error("Could not find user", 400)
            
        user = rows[0]
        user_id = user["id"]
        
        # Ensures user is not current user
        if user_id == curr_user_id:
            return error("Cannot message yourself", 400)
            
        messages = db.execute("SELECT * FROM messages WHERE (sender = ? AND recipient = ?) OR (sender = ? AND recipient = ?) ORDER BY time", 
                              curr_user_id, user_id, user_id, curr_user_id)
        
        return render_template("message.html", messages=messages, username=username)
        
    # User reached route via GET (as by clicking a link or via redirect)
    else:
        # Queries for users followed by current user
        following = db.execute("SELECT * FROM follow JOIN users ON followed = id WHERE follower = ? ORDER BY username ASC",
                               curr_user_id)
                               
        # Queries for all users that have sent or recieved messages from user
        users = set()
        for user in db.execute("SELECT * FROM messages JOIN users ON recipient = id WHERE sender = ?", curr_user_id):
            users.add(user['username'])
            
        for user in db.execute("SELECT * FROM messages JOIN users ON sender = id WHERE recipient = ?", curr_user_id):
            users.add(user['username'])
        
        return render_template("messages.html", following=following, users=sorted(list(users)))
        
        
@app.route("/message", methods=["GET", "POST"])
@login_required
def message():
    """Show messages with user"""
    
    curr_user_id = session["user_id"]
    
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        
        message = request.form.get("message")
        username = request.form.get("username")
        
        # Empty message
        if not message:
            return guide("Message cannot be empty", "/messages")
        
        # Queries for user with matching username
        rows = db.execute("SELECT id, username FROM users WHERE username = ?", username)
        
        # Ensures user exists
        if len(rows) != 1:
            return error("Could not find user", 400)
            
        user = rows[0]
        user_id = user["id"]
        
        # Ensures user is not current user
        if user_id == curr_user_id:
            return error("Cannot message yourself", 400)
            
        db.execute("INSERT INTO messages (message, sender, recipient) VALUES(?, ?, ?)",
                   message, curr_user_id, user_id)
            
        messages = db.execute("SELECT * FROM messages WHERE (sender = ? AND recipient = ?) OR (sender = ? AND recipient = ?) ORDER BY time", 
                              curr_user_id, user_id, user_id, curr_user_id)
        
        return render_template("message.html", messages=messages, username=username)
        
    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return redirect("/messages")
    

@app.route("/search", methods=["GET", "POST"])
@login_required
def search():
    """Show search results"""
    
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        
        search = request.form.get("search")
        
        # Search is empty
        if not search:
            return guide("Search cannot be empty", "/")
        
        # Queries for all users whose username contains search excluding current user
        results = db.execute("SELECT * FROM users WHERE username LIKE ? AND NOT id = ? ORDER BY username ASC",
                             '%' + search + '%', session["user_id"])
                             
        # Search results are empty
        if not results:
            return guide('No users matching "' + search + '"', "/")
        
        return render_template("searched.html", users=results, search=search)
    
    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return redirect("/")
        

def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return error(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)