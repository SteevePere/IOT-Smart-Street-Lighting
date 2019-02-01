# coding=utf-8
# -- IMPORTS --
from __future__ import unicode_literals
import hashlib
import time
import datetime
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

def getStreets():

    dbcon = influx_db.connection
    dbcon.switch_database(database='pli')

    streets = []

    street_tags = dbcon.query("SELECT DISTINCT(street) from devices")
    tag_points = list(street_tags.get_points())

    for point in tag_points:
        streets.append(point['distinct'])

    return(streets)

def getStreetFromDeviceId(device_id):

    dbcon = influx_db.connection
    dbcon.switch_database(database='pli')

    street = dbcon.query("SELECT street from devices WHERE device = {0}".format(device_id))
    street = list(street.get_points(measurement='devices'))
    street = street[0]['street']

    return(street)

def cleanStreetNames(streets):

    cleanStreets = []

    for street in streets:
        street = street.replace('_', ' ')
        cleanStreets.append(street)

    return cleanStreets

def idIncrement():

    dbcon = influx_db.connection
    dbcon.switch_database(database='pli')

    tabledata = dbcon.query('SELECT MAX(device) FROM devices')
    max_device = list(tabledata.get_points(measurement='devices'))

    if (max_device != []):
        id = max_device[0]['max']
    else:
        id = 0

    id = id + 1

    return(id)

def getDevices():

    dbcon = influx_db.connection
    dbcon.switch_database(database='pli')

    tabledata = dbcon.query('SELECT * FROM devices')
    all_devices = list(tabledata.get_points(measurement='devices'))

    return(all_devices)

def IsOneOff():

    all_devices = getDevices()
    NoOnesOff = []

    for device in all_devices:

        if (device['status'] == 0):
            return(device)

    return(NoOnesOff)

def highChartTimeSeries():

    dbcon = influx_db.connection
    dbcon.switch_database(database='pli')

    start_time = 1547856000000000000 #01/01/2019

    streets = getStreets()

    set = []
    data = []

    for street in streets:

        events_array = []
        set = []

        events = dbcon.query("select count(lumens) from events where street = '{0}' and time > {1} group by time(15m)".format(street, start_time))
        event_points = list(events.get_points())

        for event in event_points:
            event_array = []
            timestamp = int(time.mktime(datetime.datetime.strptime(event['time'], "%Y-%m-%dT%H:%M:%SZ").timetuple()) * 1000)
            event_array.append(timestamp)
            event_array.append(event['count'])
            events_array.append(event_array)

        set.append(street)
        set.append(events_array)
        data.append(set)

    return(data)

def chartJsWeekCount(week):

    dbcon = influx_db.connection
    dbcon.switch_database(database='pli')

    streets = getStreets()
    perStreetWeeklyCount = []
    i = 0
    colors = ['#BBE2E9', '#B5F299']

    from_week_day = datetime.datetime.strptime(week + '-1', "%Y-W%W-%w") - datetime.timedelta(days=7)
    monday_date = str(from_week_day.date())
    week_start_timestamp = int(time.mktime(datetime.datetime.strptime(monday_date, "%Y-%m-%d").timetuple())) * 1000000000
    week_end_timestamp = week_start_timestamp + 604800000000000

    for street in streets:

        weekly_events = dbcon.query("select count(lumens) from events where street = '{0}' and time >= {1} AND time <= {2} group by time(1d)".format(street, week_start_timestamp, week_end_timestamp))
        weekly_event_points = list(weekly_events.get_points())
        weekly_event_points = weekly_event_points[1:] #truncating list to account for influxdb's group by day (starts with previous day...)

        counts = []

        for event in weekly_event_points:
            counts.append(event["count"])

        color = colors[i]
        i = i + 1

        if (i == 2):
            i = 0

        perStreetWeeklyCount.append([street, counts, color])

    monday_date = datetime.datetime.strptime(monday_date, '%Y-%m-%d').strftime('%d/%m/%Y')

    return(perStreetWeeklyCount, monday_date)

# -- ROUTES -- #

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

@app.route('/admin', methods=['GET', 'POST'])

def create_settings():

    settings = []
    cursor.execute("SELECT * FROM alerts")
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    for row in rows:
        row = dict(zip(columns,row))
        settings.append(row)

    warning_delay = settings[0]['warning_threshold']
    alert_delay = settings[0]['alert_threshold']

    if (request.method == 'POST'):
        warning_delay = request.form.get('warning')
        alert_delay = request.form.get('alert')
        error = ''

        if (alert_delay > warning_delay):
            cursor.execute("UPDATE alerts SET warning_threshold = (%s), alert_threshold = (%s);", (warning_delay, alert_delay))
        else:
            error = "Le seuil de déclenchement d'alerte doit être supérieur au seuil de déclenchement du monitoring !"
            return render_template('admin.html', error=error),400

    return render_template('admin.html', warning=warning_delay, alert=alert_delay),200

@app.route('/newDevice', methods=['GET', 'POST'])

def create_device():

    dbcon = influx_db.connection
    dbcon.switch_database(database='pli')

    allDevices = getDevices()
    streets = getStreets()
    cleanStreets = cleanStreetNames(streets)

    if (request.method == 'POST'):

        status = int(request.form.get('status'))
        lat = request.form.get('lat')
        long = request.form.get('long')
        street = request.form.get('street')
        street = street.replace(' ', '_')
        id = idIncrement()

        json_body = [
            {
                "measurement": "devices",
                "tags": {
                    "latitude": lat,
                    "longitude": long
                },
                "fields": {
                    "status": status,
                    "device": id,
                    "street": street
                }
            }
        ]
        dbcon.write_points(json_body)

    return render_template('newDevice.html', devices=allDevices, streets=cleanStreets),200

@app.route('/map', methods=['GET', 'POST'])

def map():

    allDevices = getDevices()
    OffDevices = IsOneOff()

    return render_template('home.html', OffDevices=OffDevices, devices=allDevices),200

@app.route('/getEvents', methods=['GET', 'POST'])

def getEvents():

    dbcon = influx_db.connection
    dbcon.switch_database(database='pli')

    streets = getStreets()
    week = '2019-W03'
    post = False

    if (request.method == 'POST'):
        week = request.form['week']
        post = True

    timeSeriesData = highChartTimeSeries()
    weeklyData = chartJsWeekCount(week)[0]
    monday_date = chartJsWeekCount(week)[1]

    i = 0;

    return render_template('allEvents.html', i=i, post=post, week=week, streets=streets, week_monday_date=monday_date, perStreetWeeklyCount=weeklyData, timeSeriesData=timeSeriesData),200

#Post one event
@app.route('/postEvent', methods=['POST'])

def postEvent():

    dbcon = influx_db.connection
    dbcon.switch_database(database='pli')

    content = request.json

    device_id = content['hardware_serial']
    street = getStreetFromDeviceId(device_id)
    payload = content['payload_raw']
    time = content['metadata']['time']

    print(device_id)
    print(street)
    print(payload)
    print(time)

    #
    #
    #     json_body = [
    #         {
    #             "measurement": "events",
    #             "tags": {
    #                 "device": "001",
    #                 "street": "Maurice_Grandcoing"
    #             },
    #             "fields": {
    #                 "lumens": 0.45
    #             },
    #             "time": time
    #         }
    #     ]
    #     dbcon.write_points(json_body, time_precision='s')
    # return jsonify({'code':201,'message': 'Created'}),201
    return ''

#ERROR ROUTE
@app.errorhandler(404)

def not_found(error):
	return jsonify({'code':404,'message': 'Not Found'}),404

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000)
