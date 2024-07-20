import re
from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector
import os
from werkzeug.utils import secure_filename
from flask import request, jsonify

app = Flask(__name__)
app.secret_key = 'your secret key'

UPLOAD_FOLDER = 'static/uploads/'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

ITEMS_PER_PAGE = 3

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return render_template('dashboard.html', filename=filename)

try:
    connection = mysql.connector.connect(
        host='localhost',
        user="root",
        password='Lath@2810',  # Replace with your password
        database='Socialmedia_db'
    )
    cursor = connection.cursor(dictionary=True)
except mysql.connector.Error as e:
    print("Error connecting to MySQL:", e)

@app.route('/')
@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        password = request.form['password']
        try:
            qry = "SELECT * FROM users WHERE username = %s AND password = %s"
            cursor.execute(qry, (username, password))
            account = cursor.fetchone()
            if account:
                session['loggedin'] = True
                session['userid'] = account['userid'] # Assuming the first column is the ID
                session['username'] = account['username']  # Assuming the second column is the username
                msg = 'Logged in successfully!'
                return redirect(url_for('Profile'))
            else:
                msg = 'Incorrect username/password!'
                return render_template('login.html', msg=msg)
        except mysql.connector.Error as e:
            print("Error executing SQL query:", e)
            msg = 'An error occurred. Please try again later.'
            return render_template('login.html', msg=msg)
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('userid', None)
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    msg = ''
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        media = request.files['media']
        
        if media:
            media_filename = os.path.join(app.config['UPLOAD_FOLDER'], media.filename)
            file_path=media.save(media_filename)
        
        print("Form data:", username, password, email, file_path)
        if not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            msg = 'Invalid email address!'
        elif not re.match(r'[A-Za-z0-9]+', username):
            msg = 'Username must contain only characters and numbers!'
        elif not username or not password or not email:
            msg = 'Please fill out the form!'
        else:
            cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
            account = cursor.fetchone()
            if account:
                msg = 'Account already exists!'
            else:
                cursor.execute('INSERT INTO users (username, password, email,photo) VALUES (%s, %s, %s, %s)', (username, password, email,file_path))
                connection.commit()
        msg = 'You have successfully registered!'
    return render_template('register.html', msg=msg)

@app.route('/posts')
def posts():
    msg = ' '
    if 'loggedin' in session:
        page = int(request.args.get('page', 1))
        offset = (page - 1) * ITEMS_PER_PAGE
        userid = session['userid']
        
        # Query to get the total number of items
        cursor.execute('SELECT COUNT(*) AS count FROM posts')
        total_items = cursor.fetchone()['count']
        total_pages = (total_items + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
        
        # Query to get the items for the current page, including follow status
        cursor.execute('''
            SELECT p.*, u.username, COUNT(l.userid) AS likes_count 
FROM posts AS p 
LEFT JOIN users AS u ON u.userid = p.userid 
LEFT JOIN likes AS l ON l.postid = p.postid 
WHERE p.postid = %s
GROUP BY p.postid, u.username 
ORDER BY p.postid DESC
            LIMIT %s OFFSET %s
        ''', (userid, ITEMS_PER_PAGE, offset))
        
        value = cursor.fetchall()
        
        return render_template("Newsfeed.html", msg=msg, data=value, page=page, total_pages=total_pages)
    return redirect(url_for('login'))



@app.route('/editprofile/<int:id>', methods=['POST', 'GET'])
def editprofile(id):
    if 'loggedin' in session:
        if request.method == 'POST':
            username = request.form['name']
            password = request.form['password']
            email = request.form['email']
            place = request.form['place']
            text = request.form['text']
            userid = session['userid']
            file = request.files['media']
            file_path = None
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
            
            print("Form data:", username, password, email, place, text, file_path)
            
            try:
                cursor.execute('UPDATE users SET username = %s, password = %s, email = %s, place = %s, text = %s, photo = %s WHERE userid = %s', 
                               (username, password, email, place, text, file_path, userid))
                connection.commit()
                print("Data updated successfully")
            except mysql.connector.Error as e:
                print("Error executing SQL query:", e)
            return redirect(url_for('Profile'))
        
        cursor.execute('SELECT * FROM users WHERE userid = %s', (id,))
        value = cursor.fetchone()
        print(value)
        if value:
            return render_template('editprofile.html', user=value)
    return redirect(url_for('login'))


@app.route('/Profile')
def Profile():
    if 'loggedin' in session:
        userid = session['userid']
        print('Data fetchting')
        cursor.execute('SELECT * FROM users WHERE userid=%s', (userid,))
        value = cursor.fetchone()
        return render_template('Profile.html', user=value)
    return redirect(url_for('login'))

@app.route('/createpost', methods=['POST', 'GET'])
def createpost():
    if 'loggedin' in session:
        if request.method == 'POST':
            content = request.form['content']
            userid = session['userid']
            file = request.files['media']
            feed = request.form['feed']
            filename = None
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
            try:
                cursor.execute('INSERT INTO posts (userid, content, media_url, feed) VALUES (%s, %s, %s, %s)', 
                               (userid, content, filename, feed))
                connection.commit()
                return redirect(url_for('myposts'))
            except mysql.connector.Error as e:
                print("Error executing SQL query:", e)
        return render_template('createpost.html')
    return redirect(url_for('login'))

        
@app.route('/myposts')
def myposts():
    if 'loggedin' in session:
        userid = session['userid']
        print('Data fetching')
        cursor.execute('SELECT p.*, u.username FROM posts AS p LEFT JOIN users AS u ON u.userid = p.userid WHERE p.userid = %s ORDER BY p.postid DESC;', (userid,))
        value = cursor.fetchall()
        return render_template('myposts.html', data=value)
    return redirect(url_for('login'))

@app.route('/editposts/<int:id>',methods=['GET','POST'])
def editposts(id):
    if 'loggedin' in session:
        if request.method == 'POST':
            content = request.form['content']
            file = request.files['media']
            filename = None

            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)

            print("Form data:", id, content, filename)

            try:
                if filename:
                    cursor.execute('UPDATE posts SET content = %s, media_url = %s WHERE postid = %s', 
                                   (content, filename, id))
                else:
                    cursor.execute('UPDATE posts SET content = %s WHERE postid = %s', 
                                   (content, id))
                connection.commit()
                print("Data updated successfully")
            except mysql.connector.Error as e:
                print("Error executing SQL query:", e)

            return redirect(url_for('singlepost', id=id))  # Assuming 'singlepost' takes an 'id' parameter
        else:
            cursor.execute('SELECT * FROM posts WHERE postid = %s', (id,))
            post = cursor.fetchone()
            if post:
                return render_template('editposts.html', post=post)
            else:
                return "Post not found", 404

@app.route('/singlepost/<int:id>')
def singlepost(id):
    if 'loggedin' in session:
        userid = session['userid']
        print('Data fetching')
        cursor.execute('SELECT p.*, u.username FROM posts as p LEFT JOIN users as u ON u.userid=p.userid WHERE p.postid = %s', (id,))
        value = cursor.fetchall()
        return render_template('post.html', data=value)
    return redirect(url_for('login'))

@app.route('/deletepost/<int:id>')
def deletepost(id):
    if 'loggedin' in session:
        try:
            cursor.execute('DELETE FROM posts WHERE postid = %s', (id,))
            connection.commit()
        except mysql.connector.Error as e:
            print("Error executing SQL query:", e)
        return redirect(url_for('myposts'))
    return redirect(url_for('login'))

@app.route('/search_template')
def search_template():
    flag = 'T'
    return render_template('Searchpost.html', flag=flag)

@app.route('/search_post', methods=['GET'])
def search_post():
    if 'loggedin' in session:
        text = request.args.get('text')
        if text is None:
            text = ''  # Set title to an empty string if it is None
        cursor.execute('SELECT * FROM posts WHERE content LIKE %s ', ('%' + text + '%',))
        value = cursor.fetchall()
        return render_template('searchpost.html', data=value)
    return redirect(url_for('login'))

@app.route('/search_templates')
def search_templates():
    flag = 'T'
    return render_template('Searchuser.html', flag=flag)

@app.route('/search_user', methods=['GET'])
def search_user():
    if 'loggedin' in session:
        username = request.args.get('name')
        if username is None:
            username = ''  # Set title to an empty string if it is None
        cursor.execute('SELECT * FROM users WHERE username LIKE %s ', (username,))
        print('Username : ',username)
        value = cursor.fetchall()
        return render_template('searchuser.html', data=value)
    return redirect(url_for('login'))

from flask import request, jsonify

@app.route('/ajax_like', methods=['POST'])
def ajax_like():
    if 'loggedin' in session:
        data = request.get_json()
        postid = data['postid']
        userid = session['userid']
        
        # Check if the like already exists
        cursor.execute('SELECT * FROM likes WHERE postid = %s AND userid = %s', (postid, userid))
        like = cursor.fetchone()
        
        if like:
            # Unlike the post if already liked
            cursor.execute('DELETE FROM likes WHERE postid = %s AND userid = %s', (postid, userid))
            connection.commit()
            return jsonify(status='success', message='Unliked the post.')
        else:
            # Like the post if not already liked
            cursor.execute('INSERT INTO likes (postid, userid) VALUES (%s, %s)', (postid, userid))
            connection.commit()
            return jsonify(status='success', message='Liked the post.')
    return jsonify(status='error', message='You must be logged in to like a post.')


@app.route('/ajax_follow', methods=['POST'])
def ajax_follow():
    if 'loggedin' in session:
        data = request.get_json()
        follower_id = session['userid']
        followed_id = data['userid']
        
        # Check if already following
        cursor.execute('SELECT * FROM follows WHERE followerid = %s AND userid = %s', (follower_id, followed_id))
        follow = cursor.fetchone()
        
        if follow:
            # Unfollow
            cursor.execute('DELETE FROM follows WHERE followerid = %s AND userid = %s', (follower_id, followed_id))
            connection.commit()
            return jsonify({'status': 'success', 'message': 'Unfollowed successfully'})
        else:
            # Follow
            cursor.execute('INSERT INTO follows (followerid, userid) VALUES (%s, %s)', (follower_id, followed_id))
            connection.commit()
            return jsonify({'status': 'success', 'message': 'Followed successfully'})
    
    return jsonify({'status': 'error', 'message': 'You need to log in to follow users'})



    
if __name__ == '__main__':
    app.run(debug=True)