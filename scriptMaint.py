# coding: utf-8

# -- IMPORTS --
from flask import Flask, request, jsonify
from flaskext.mysql import MySQL
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

#MySQL config
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = 'Makaveli'
app.config['MYSQL_DATABASE_DB'] = 'pli_users'
app.config['MYSQL_DATABASE_HOST'] = '127.0.0.1'
mysql.init_app(app)

#InfluxDB config
host = 'localhost'
port = 8086
user = 'root'
password = 'root'
dbname = 'pli'
client = InfluxDBClient(host, port, user, password, dbname)

# -- MYSQL OBJECTS --

conn = mysql.connect()
cursor = conn.cursor()

# Retrieving all devices as list
def getDevices():

    tabledata = client.query('SELECT * FROM devices')
    all_devices = list(tabledata.get_points(measurement='devices')) #we'll keep the list as is, so we can access attributes as needed

    return(all_devices)

#Get admin email
def getAdminsMailAddress():

    cursor.execute("SELECT email FROM users WHERE role = 'admin'")
    result = cursor.fetchall()
    email = result[0][0]

    return email

def getDevicesLastData(devices):

    last_data = {}

    for device in devices:

        deviceEui = device['device']
        query = client.query("SELECT last(lumens), time FROM events WHERE device = '{0}'".format(deviceEui), epoch='ns')
        event_point = list(query.get_points())

        if (event_point != []): #if device has already emitted

            time = event_point[0]['time'] #we want the time
            last_data[deviceEui] = time #storing in dict so we may easily retrieve values from device id

        else: #no data for this device
            last_data[deviceEui] = 0 #storing in dict so we may easily retrieve values from device id

    return (last_data)

def setDeviceStatusToOff(device):

    return

def setDeviceStatusToWarning(device):

    return


# Get user settings
def getSettings():

    settings = []
    cursor.execute("SELECT * FROM alerts")
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]

    for row in rows:

        row = dict(zip(columns,row))
        settings.append(row)
        warning_delay = settings[0]['warning_threshold'] #current value, to display on page load
        alert_delay = settings[0]['alert_threshold'] #current value, to display on page load
        settings = {
                'warning_delay' : warning_delay,
                'alert_delay' : alert_delay
        }

    return settings

settings = getSettings()
warning = settings['warning_delay']
alert = settings['alert_delay']

import time
now = str(time.time())
now = ".".join(now.split('.')[:1])
now = int(now + '000000000') #hacky way to get nanoseconds

warningDelayNanosecs = warning * 3600000000000
warningPeriodStartTime = now - warningDelayNanosecs

alertDelayNanosecs =  alert * 3600000000000
alertPeriodStartTime = now - alertDelayNanosecs

# query = 'select "device","status" from devices where time < now()'
# queryEvent = 'select * from events;'
# arrayResult = []

##############################################EMAIL########################################

mailInput = 'xyz97600@gmail.com'
mailOutput = getAdminsMailAddress()
msg = MIMEMultipart()
msg['From'] = mailInput
msg['To'] = mailOutput

msg['Subject'] = 'Alert Lampadaire'
mailserver = smtplib.SMTP('smtp.gmail.com', 587)
mailserver.ehlo()
mailserver.starttls()
mailserver.ehlo()
mailserver.login(mailInput, 'PLI_2018')

##########################################################################################

devices = getDevices()

devicesLastData = getDevicesLastData(devices)

for device in devices:

    deviceEui = device['device']
    deviceStatus = device['status']

    deviceLastData = devicesLastData[deviceEui]
    print(deviceLastData)

    if (deviceLastData < alertPeriodStartTime or deviceLastData == 0):

        # setDeviceStatusToOff(device)
        print("set to zero")

    if (deviceLastData > alertPeriodStartTime and deviceLastData < warningPeriodStartTime):

        # setDeviceStatusToWarning(device)
        print("set to warning")



# #result = client.query(query)
# resultsEvent = client.query(queryEvent)
# ## getAll result
# points = resultsEvent.get_points()
# for item in points:
# 	arrayResult.append(item)
#
# ## str to result
# getResultInArray = ''.join(str(e) for e in arrayResult)
# getResultInArray = getResultInArray.replace('}',']').replace('{','').replace('u\'','').replace('\'','')
# getResultInArray = getResultInArray.split(']')[:-1]
#
# ##Iteration on Array to get only time
# arrayTime = []
# for item in getResultInArray:
# 	arrayTime.append(item.split(None,8)[7])
# ##Change format dateTime
#
# ArrayFormat = []
# for i in arrayTime:
# 	ArrayFormat.append(i.replace('T',' ').replace('.',' ').replace('-','/').rsplit(' ', 1)[0])
#
# def create_json_body_for_value(time,device,lat,long,street):
#     return json.dumps([
#         {
#             "measurement": "devices",
#             "time": time,
# 	    "tags": {
# 		"street": street,
# 		"latitude": lat,
# 		"longitude": long,
# 		},
#             "fields": {
#                 "device": device,
#  		"status": '0.1'
#             }
#         }])
#
# ## Array for index of values
# arratGetTime = []
# arrayGetDevice = []
# deviceDanger = []
# deviceEteint = []
#
# for i in ArrayFormat:
#
#     a = datetime.strptime(i, "%Y/%m/%d %H:%M:%S").strftime("%A, %d. %B %Y %I:%M:%S%p")
#     b = pd.to_datetime(a) + pd.DateOffset(hours=_valueWarnig)
#     c = pd.to_datetime(a) + pd.DateOffset(hours=_valueAlert)
#
#     if (datetime.now() >= b and datetime.now() < c):
#
#         arratGetTime.append(ArrayFormat.index(i))
#         device = str(arrayResult[ArrayFormat.index(i)]).split(None,2)[1].replace('u','').replace(',','')
#         device = device.replace("'","")
#         device1 = client.query(("select * from devices where device='%s'")%(str(device)),epoch='ns')
#         timeStamp = device1.raw['series'][0]['values'][0][0]
#         lat = device1.raw['series'][0]['values'][0][2]
#         long = device1.raw['series'][0]['values'][0][3]
#         street = device1.raw['series'][0]['values'][0][5]
#         json_body = [ {
#                 "measurement": "devices",
#                 "tags": {
#                     "latitude": lat,
#                     "longitude": long,
#             },
#             "fields": {
#                     "status": float("0.5"),
#                     "street": street,
#                     "device": device,
#                 },
#             "time": timeStamp,
#             }]
#
#         try:
#         	client.write_points(json_body)
#
#         except Exception as e:
#         	print(str(e))
#
#         deviceDanger.append(device)
#
#     elif (datetime.now() >= c):
#
#         arratGetTime.append(ArrayFormat.index(i))
#         device = str(arrayResult[ArrayFormat.index(i)]).split(None,2)[1].replace('u','').replace(',','')
#         device = device.replace("'","")
#         device1 = client.query(("select * from devices where device='%s'")%(str(device)),epoch='ns')
#         timeStamp = device1.raw['series'][0]['values'][0][0]
#         lat = device1.raw['series'][0]['values'][0][2]
#         long = device1.raw['series'][0]['values'][0][3]
#         street = device1.raw['series'][0]['values'][0][5]
#         json_body = [ {
#             "measurement": "devices",
#             "tags": {
#                 "latitude": lat,
#                 "longitude": long,
#             },
#             "fields": {
#                 "street": street,
#                 "device": device,
#                 "status": float(0)
#             },
#             "time": timeStamp,
#         }]
#
#         try:
#                 client.write_points(json_body)
#         except Exception as e:
#                 print(str(e))
#         deviceEteint.append(device)
        # else:
    	# arratGetTime.append(ArrayFormat.index(i))
        #         device = str(arrayResult[ArrayFormat.index(i)]).split(None,2)[1].replace('u','').replace(',','')
        #         device = device.replace("'","")
        #         device1 = client.query(("select * from devices where device='%s'")%(str(device)),epoch='ns')
        #         timeStamp = device1.raw['series'][0]['values'][0][0]
        #         lat = device1.raw['series'][0]['values'][0][2]
        #         long = device1.raw['series'][0]['values'][0][3]
        #         street = device1.raw['series'][0]['values'][0][5]
        #         json_body = [ {
        #             "measurement": "devices",
        #             "tags": {
        #                 "latitude": lat,
        #                 "longitude": long,
        #             },
        #             "fields": {
        #                 "status": float(1),
        #                 "street": street,
        #                 "device": device,
        #             },
        #             "time": timeStamp,
        #         }]
        #         try:
        #                 client.write_points(json_body)
        #         except Exception as e:
        #                 print(str(e))

# print(deviceDanger)
# print(deviceEteint)
# str1 = ','.join(deviceDanger)
# str2 = ','.join(deviceEteint)
# message = 'holaaaalaaaa ! Alert '+str1+' est en danger et '+str2+' sont etteint'
# msg.attach(MIMEText(message))
# mailserver.sendmail(mailInput, mailOutput, msg.as_string())
# mailserver.quit()
