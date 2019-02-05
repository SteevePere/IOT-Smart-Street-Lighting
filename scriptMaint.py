# coding: utf-8

# -- IMPORTS --
from flask import Flask, request, jsonify, redirect, url_for, render_template
#from __future__ import unicode_literals
from flaskext.mysql import MySQL
import datetime
import json
import re
import encodings
import argparse
from influxdb import InfluxDBClient
import datetime
from dateutil.parser import parse
from datetime import datetime, date, time, timedelta
import pandas as pd
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText



# -- INIT APP --

app = Flask(__name__)

# -- INIT MySQL & InfluxDB --

mysql = MySQL()

# -- APP CONFIG --

app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = 'Makaveli'
app.config['MYSQL_DATABASE_DB'] = 'pli_users'
app.config['MYSQL_DATABASE_HOST'] = '127.0.0.1'
mysql.init_app(app)
host = 'localhost'
port = 8086
user = 'root'
password = 'root'
dbname = 'pli'
client = InfluxDBClient(host, port, user, password, dbname)


# -- MYSQL OBJECTS --

conn = mysql.connect()
cursor = conn.cursor()

# Get paramettre
def getAlert():
#+-------------------+---------+------+-----+---------+-------+
#| Field             | Type    | Null | Key | Default | Extra |
#+-------------------+---------+------+-----+---------+-------+
#| warning_threshold | int(11) | NO   |     | 48      |       |
#| alert_threshold   | int(11) | NO   |     | 72      |       |
#+-------------------+---------+------+-----+---------+-------+
#2 rows in set (0.00 sec)

        settings = []
        cursor.execute("SELECT * FROM alerts") #getting current values
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        for row in rows:
                row = dict(zip(columns,row))
                settings.append(row)
        warning_delay = settings[0]['warning_threshold'] #current value, to display on page load
        alert_delay = settings[0]['alert_threshold'] #current value, to display on page load
        dataSeting = {
                'warning_delay' : warning_delay,
                'alert_delay' : alert_delay
        }
        return dataSeting

getSeting = getAlert()

print(getSeting['warning_delay'])




# -- Valuel Alert
_valueWarnig = getSeting['warning_delay']
_valueAlert = getSeting['alert_delay']


query = 'select "device","status" from devices where time < now()'
queryEvent = 'select * from events;'
arrayResult = []


##############################################EMAIL########################################

#mailInput = 'xyz97600@gmail.com'
#mailOutput = 'keavinwilson@gmail.com'
#msg = MIMEMultipart()
#msg['From'] = mailInput
#msg['To'] = mailOutput

#msg['Subject'] = 'Alert Lampadaire' 
#mailserver = smtplib.SMTP('smtp.gmail.com', 587)
#mailserver.ehlo()
#mailserver.starttls()
#mailserver.ehlo()
#mailserver.login(mailInput, '@@@@@@@@@')

##########################################################################################


#result = client.query(query)
resultsEvent = client.query(queryEvent)
#print(result)
#print(resultsEvent)
## getAll result
points = resultsEvent.get_points()
for item in points:
	arrayResult.append(item)

print(arrayResult)

## str to result
getResultInArray = ''.join(str(e) for e in arrayResult)
getResultInArray = getResultInArray.replace('}',']').replace('{','').replace('u\'','').replace('\'','')
getResultInArray = getResultInArray.split(']')[:-1]
#print(getResultInArray)

##Iteration on Array to get only time
arrayTime = []
for item in getResultInArray:
	arrayTime.append(item.split(None,8)[7])
#	print(item.split(None,8)[7])
##Change format dateTime

#print(arrayTime)
ArrayFormat = []
for i in arrayTime:
	ArrayFormat.append(i.replace('T',' ').replace('.',' ').replace('-','/').rsplit(' ', 1)[0])
print(ArrayFormat)

def create_json_body_for_value(time,device,lat,long,street):
    return json.dumps([
        {
            "measurement": "devices",
            "time": time,
	    "tags": {
		"street": street,
		"latitude": lat,
		"longitude": long,
		},
            "fields": {
                "device": device,
 		"status": '0.1'
            }
        }])

## Array for index of values
arratGetTime = []
arrayGetDevice = []
deviceDanger = []
deviceEteint = []
for i in ArrayFormat:
	a = datetime.strptime(i, "%Y/%m/%d %H:%M:%S").strftime("%A, %d. %B %Y %I:%M:%S%p")
	b = pd.to_datetime(a) + pd.DateOffset(days=_valueWarnig)
	c = pd.to_datetime(a) + pd.DateOffset(days=_valueAlert)
	if (datetime.now() >= b and datetime.now() < c):
		arratGetTime.append(ArrayFormat.index(i))
		device = str(arrayResult[ArrayFormat.index(i)]).split(None,2)[1].replace('u','').replace(',','')
		device = device.replace("'","")
		device1 = client.query(("select * from devices where device='%s'")%(str(device)),epoch='ns')
		timeStamp = device1.raw['series'][0]['values'][0][0]
		lat = device1.raw['series'][0]['values'][0][2]
		long = device1.raw['series'][0]['values'][0][3]
		street = device1.raw['series'][0]['values'][0][5]
		json_body = [ {
	            "measurement": "devices",
	            "tags": {
	                "street": street,
	                "latitude": lat,
	                "longitude": long,
	                "device": device,
		    },
		    "fields": {
	                "status": 0.5
	            },
		    "time": timeStamp,
	        }]
		try:
			client.write_points(json_body)
#			mailserver.sendmail(mailInput, mailOutput, msg.as_string())
#			mailserver.quit()
		except Exception as e:
			print(str(e))
		deviceDanger.append(device)
                print("device danger"+device)
        elif (datetime.now() >= c):
		arratGetTime.append(ArrayFormat.index(i))
                device = str(arrayResult[ArrayFormat.index(i)]).split(None,2)[1].replace('u','').replace(',','')
                device = device.replace("'","")
                device1 = client.query(("select * from devices where device='%s'")%(str(device)),epoch='ns')
                timeStamp = device1.raw['series'][0]['values'][0][0]
                lat = device1.raw['series'][0]['values'][0][2]
                long = device1.raw['series'][0]['values'][0][3]
                street = device1.raw['series'][0]['values'][0][5]
                json_body = [ {
                    "measurement": "devices",
                    "tags": {
                        "street": street,
                        "latitude": lat,
                        "longitude": long,
                        "device": device,
                    },
                    "fields": {
                        "status": float(0)
                    },
                    "time": timeStamp,
                }]
                try:
                        client.write_points(json_body)
                except Exception as e:
                        print(str(e))
                print("device down"+device)
		deviceEteint.append(device)
        else:
		arratGetTime.append(ArrayFormat.index(i))
                device = str(arrayResult[ArrayFormat.index(i)]).split(None,2)[1].replace('u','').replace(',','')
                device = device.replace("'","")
		print(device)
                device1 = client.query(("select * from devices where device='%s'")%(str(device)),epoch='ns')
                timeStamp = device1.raw['series'][0]['values'][0][0]
		print(device1)
                lat = device1.raw['series'][0]['values'][0][2]
                long = device1.raw['series'][0]['values'][0][3]
                street = device1.raw['series'][0]['values'][0][5]
                json_body = [ {
                    "measurement": "devices",
                    "tags": {
                        "street": street,
                        "latitude": lat,
                        "longitude": long,
                        "device": device,
                    },
                    "fields": {
                        "status": float(1)
                    },
                    "time": timeStamp,
                }]
                try:
                        client.write_points(json_body)
                except Exception as e:
                        print(str(e))
                print("device up")
print(deviceDanger)
print(deviceEteint)
str1 = ','.join(deviceDanger)
str2 = ','.join(deviceEteint)
message = 'holaaaalaaaa ! Alert '+str1+' est en danger et '+str2+' sont etteint'
#msg.attach(MIMEText(message))
#mailserver.sendmail(mailInput, mailOutput, msg.as_string())
#mailserver.quit()