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

#ALL USERS
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
@app.route('/signIn', methods=['GET', 'POST'])

def signIn():
    if (request.method == 'POST'):
        user = []
        login = request.form['login']
        sha_1 = hashlib.sha1(request.form['password'])
        password = sha_1.hexdigest()
        isSignedIn = cursor.execute("SELECT * FROM users WHERE login = (%s) AND password = (%s)", (login, password))
        if (isSignedIn):
            return redirect('/getEvents')
        else:
            error = "Identifiant ou mot de passe incorrect !"
            return render_template('login.html', error=error),401
    return render_template('login.html'),200

#Get all events
@app.route('/getEvents', methods=['GET', 'POST'])

def getEvents():

    dbcon = influx_db.connection
    dbcon.switch_database(database='pli')

    streets = ['Lenine', 'Toto', 'Maurice_Grandcoing']
    date = "2019-01-19"
    interval = '30m'

    if (request.method == 'POST'):

        date = request.form['period']
        interval = request.form['interval']

    Lenine_times = []
    Lenine_counts = []
    Toto_times = []
    Toto_counts = []
    Maurice_Grandcoing_times = []
    Maurice_Grandcoing_counts = []

    import time
    import datetime
    timestamp = int(time.mktime(datetime.datetime.strptime(date, "%Y-%m-%d").timetuple()))
    time_from = (timestamp + 68400) * 1000000000 #from 6
    time_to = time_from + 43200000000000 #to 6

    for street in streets:

        events = dbcon.query("select count(lumens) from events where street = '{0}' and time <= {1} AND time >= {2} group by time({3})".format(street, time_to, time_from, interval))
        event_points = list(events.get_points())

        for event in event_points:
            event_time = "Z".join(event["time"].split('Z')[0:1])
            event_time = "T".join(event_time.split('T')[1:])
            event_time = ":".join(event_time.split(':')[:2])
            if (street == 'Lenine'):
                Lenine_times.append(event_time)
                Lenine_counts.append(event["count"])
            if (street == 'Toto'):
                Toto_times.append(event_time)
                Toto_counts.append(event["count"])
            if (street == 'Maurice_Grandcoing'):
                Maurice_Grandcoing_times.append(event_time)
                Maurice_Grandcoing_counts.append(event["count"])

        MG_legend = 'Rue Maurice Grandcoing, la nuit du ' + date
        Toto_legend = 'Rue Toto, la nuit du ' + date
        Lenine_legend = 'Rue Lenine, la nuit du ' + date

    tabledata = dbcon.query('SELECT * FROM events')
    all_events = list(tabledata.get_points(measurement='events'))
    tabledata2 = dbcon.query('SELECT * FROM devices')
    all_devices = list(tabledata2.get_points(measurement='devices'))

    return render_template('allEvents.html', events=all_events, devices=all_devices, Lenine_values=Lenine_counts, MG_values=Maurice_Grandcoing_counts, Toto_values=Toto_counts, labels=Lenine_times, Lenine_legend=Lenine_legend, MG_legend=MG_legend, Toto_legend=Toto_legend),200

#Post one event
@app.route('/postEvent', methods=['POST'])

def postEvent():
    # import time;
    # time = int(time.time())
    time = 1547917200
    dbcon = influx_db.connection
    dbcon.switch_database(database='pli')

    for i in range(24):
        json_body = [
            {
                "measurement": "events",
                "tags": {
                    "device": "001",
                    "street": "Maurice_Grandcoing"
                },
                "fields": {
                    "lumens": 0.45
                },
                "time": time
            }
        ]
        dbcon.write_points(json_body, time_precision='s')
        time += 4325
    return jsonify({'code':201,'message': 'Created'}),201


# def cronJob():
#     time_now = os_time
#     time_48_h_ago = time_now - 48 h
#     time_72_h_ago = time_now - 72 h
#
#     devices = select * distinct(id) from events
#
#     for device in devices:
#
#     event = select from events where device_id = device.id and timestamp between time_now and time_48_h_ago
#
#     if (!event):
#         if (device.status == 1):
#             set device_status = 0.5
#         else if (device.status == 0.5):
#             event = select from events where device_id = device.id and timestamp between time_now and time_72_h_ago
#             if (!event):
#                 set device_status = 0
# 		else if (event and device.status == 0.5 or device.status = 0):
#             set device_status = 1


#ERROR ROUTE
@app.errorhandler(404)

def not_found(error):
	return jsonify({'code':404,'message': 'Not Found'}),404

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000)
