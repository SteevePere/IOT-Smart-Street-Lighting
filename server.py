# -- IMPORTS --
from flask import Flask, request, jsonify
from flaskext.mysql import MySQL

# -- INIT OBJECTS --

mysql = MySQL()
app = Flask(__name__)

# -- APP CONFIG --

app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = 'Makaveli'
app.config['MYSQL_DATABASE_DB'] = 'pli_users'
app.config['MYSQL_DATABASE_HOST'] = '127.0.0.1'
mysql.init_app(app)

# -- MYSQL OBJECTS --

conn = mysql.connect()
cursor = conn.cursor()

# -- ROUTES --

#INDEX
@app.route('/', methods=['GET'])

def home():
    all_users = []
    cursor.execute("SELECT * FROM users")
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    for row in rows:
    	row = dict(zip(columns,row))
    	all_users.append(row)
    return jsonify({'users': all_users}),200

#LOGIN (get token)
@app.route('/signIn', methods=['GET'])

def signIn():
    user = []
    login = request.headers.get('login')
    password = request.headers.get('password')
    cursor.execute("SELECT * FROM users WHERE login = (%s) AND password = (%s)", (login, password))
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    for row in rows:
    	row = dict(zip(columns,row))
    	user.append(row)
    return jsonify({'users': user}),200

#ERROR ROUTE
@app.errorhandler(404)

def not_found(error):
	return jsonify({'code':404,'message': 'Not Found'}),404

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000)
