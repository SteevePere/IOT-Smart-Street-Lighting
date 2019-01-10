# -- IMPORTS --
import hashlib
from flask import Flask, request, jsonify, redirect, url_for, render_template
from flaskext.mysql import MySQL
from flask_influxdb import InfluxDB

# -- INIT OBJECTS --

app = Flask(__name__)
mysql = MySQL()
influx_db = InfluxDB(app=app)

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
@app.route('/getUsers', methods=['GET'])

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
    sha_1 = hashlib.sha1(request.headers.get('password'))
    password = sha_1.hexdigest()
    cursor.execute("SELECT * FROM users WHERE login = (%s) AND password = (%s)", (login, password))
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    for row in rows:
    	row = dict(zip(columns,row))
    	user.append(row)
    return jsonify({'users': user}),200

#Get all events
@app.route('/getEvents', methods=['GET'])

def getEvents():
    dbcon = influx_db.connection
    dbcon.switch_database(database='pli')
    tabledata = dbcon.query('SELECT * FROM events')
    events = list(tabledata.get_points(measurement='events'))
    # return jsonify({'data': events})
    return render_template('allEvents.html', events=events),200

#Post one event
@app.route('/postEvent', methods=['POST'])

def postEvent():
    dbcon = influx_db.connection
    dbcon.switch_database(database='statsdemo')
    json_body = [
        {
            "measurement": "cpu",
            "tags": {
                "host": "serverBB"
            },
            "fields": {
                "value": 0.44
            }
        }
    ]
    dbcon.write_points(json_body)
    return jsonify({'code':201,'message': 'Created'}),201

#ERROR ROUTE
@app.errorhandler(404)

def not_found(error):
	return jsonify({'code':404,'message': 'Not Found'}),404

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000)
