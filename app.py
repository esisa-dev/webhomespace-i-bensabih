import zipfile
from flask import Flask
from flask import redirect
from flask import request
import os
import subprocess
import logging
import crypt
import time
from flask import render_template, session, url_for, send_file
# create web app instance
app = Flask(__name__)

app.secret_key = 'idk_why_but_it_works_fine'
logging.basicConfig(filename='app.log', level=logging.INFO)

def files_count(user):
        cmd = f"find /home/{user} -path '*/\.*' -prune -o -type f -print | wc -l"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        output = result.stdout.strip().split('\n')
        if output[-1]:
            file_count = int(output[-1])
        else:
            file_count = 0
        return file_count
def user_space(home_dir):
        result = subprocess.run(['du', '-sh', home_dir], stdout=subprocess.PIPE)
        space_used = result.stdout.decode('utf-8').split('\t')[0]
        space_used_num = space_used[:-1]  # remove the last character (unit)
        return space_used_num
# handle root route
@app.route('/')
def root():
    
    if 'username' in session:
        home_dir = os.path.expanduser("/home/"+session['username'])
        # num_files = len([f for f in os.listdir(home_dir) if os.path.isfile(os.path.join(home_dir, f))])
        num_files=files_count(session['username'])
        num_dirs = len([f for f in os.listdir(home_dir) if os.path.isdir(os.path.join(home_dir, f))])
        # space_used = sum(os.path.getsize(os.path.join(home_dir, f)) for f in os.listdir(home_dir) if os.path.isfile(os.path.join(home_dir, f)))
    
        space_used=user_space(home_dir)
        return render_template('index.html', username=session['username'], home_dir=home_dir, num_files=num_files, num_dirs=num_dirs, space_used=space_used,current_working_directory=os.getcwd(),
         file_list=subprocess.check_output('ls ', shell=True).decode('utf-8').split('\n'),file_list_date=subprocess.check_output("ls -l | awk '{print $6" "$7, $8}' ", shell=True).decode('utf-8').split('\n'),file_list_size=subprocess.check_output("ls -lh | awk '{print $5}' ", shell=True).decode('utf-8').split('\n')) 

    else:
        return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if authenticate(username, password):
            session['username'] = username
            logging.info(f'User {username} logged in')
            home_directory = "/home/"+session['username']
            try:
                os.chdir(home_directory)
            except:
                pass
            return redirect(url_for('root'))
        else:
            return render_template('login.html', error='Invalid username or password')
    else:
        return render_template('login.html')

@app.route('/logout')
def logout():
    if 'username' in session:
        username = session['username']
        session.pop('username', None)
        logging.info(f'User {username} logged out')
    return redirect(url_for('login'))


@app.route('/navigate')
def navigate():
    try:
        os.chdir(request.args.get('path'))
        return redirect('/')
    except:
        return redirect('/')
    
  
@app.route('/search', methods=['POST'])
def search():
    try:
        
        if 'username' in session:
            search_query = request.form['search-term']
            home_dir = os.path.expanduser("/home/"+session['username'])
            results = []
            for root, dirs, files in os.walk(home_dir):
                for item in dirs + files:
                    item_path = os.path.join(root, item)
                    if search_query in item or search_query in item_path:
                        item_size = os.path.getsize(item_path) if os.path.isfile(item_path) else '-'
                        item_date = time.ctime(os.path.getmtime(item_path))
                        item_type = 'file' if os.path.isfile(item_path) else 'dir'
                        results.append((item_path, item_type, item_size, item_date))
            return render_template('search_results.html', query=search_query, results=results)
        else:
            return redirect(url_for('/'))
    except:
        return redirect('/')
@app.route('/view')
def view():
    try:
        if ('.'  in request.args.get('file')):
            with open(request.args.get('file')) as f:
                # return f.read().replace('\n', '<br>')
                return render_template('view_file.html', file_content=f.read())
        else:
            os.chdir(request.args.get('file'))
            return redirect('/')
    except:
            return redirect('/')

@app.route('/download')
def download():
    try:
        if 'username' in session:
            home_dir = os.path.expanduser("/home/"+session['username'])
            zip_filename = 'home_dir'+session['username']+'.zip'
            with zipfile.ZipFile(zip_filename, 'w') as zip_file:
                for root, dirs, files in os.walk(home_dir):
                    for file in files:
                        zip_file.write(os.path.join(root, file))
            return send_file(zip_filename, as_attachment=True)
        else:
            return redirect(url_for('login'))
    except:
        return redirect('/')
def authenticate(username, password):
    with open('/etc/shadow', 'r') as shadow_file:
        shadow_data = shadow_file.readlines()
        for line in shadow_data:
            if line.startswith(username):
                hash_data = line.split(':')[1].strip()
                break
        else:
            return False
        
    if crypt.crypt(password, hash_data) == hash_data:
        return True
    else:
        return False
    

if __name__ == '__main__':
    app.run(debug=True, threaded=True,port=8080)