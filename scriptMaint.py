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

# -- Functions --

# Retrieving all devices as list
def getDevices():

    tabledata = client.query('SELECT * FROM devices', epoch='ns')
    all_devices = list(tabledata.get_points(measurement='devices')) #we'll keep the list as is, so we can access attributes as needed

    return(all_devices)

#Get admin's email
def getAdminsMailAddress():

    cursor.execute("SELECT email FROM users WHERE role = 'admin'")
    result = cursor.fetchall()
    email = result[0][0]

    return email

#Get admin's name
def getAdminsName():

    cursor.execute("SELECT first_name FROM users WHERE role = 'admin'")
    result = cursor.fetchall()
    name = result[0][0]

    return name

def sendMailToAdmin(warningList, alertList):

    adminsName = getAdminsName()
    url = 'http://51.77.229.185:8000/signIn'

    message = "Bonjour " + adminsName + ","

    if (warningList != ''): #only if some devices have been flagged as suspicious
        message += "\n\nLes lampadaires suivants ont franchi votre seuil de monitoring : " + warningList + "."

    if (alertList != ''): #only if some devices have been flagged as faulty
        message += "\n\nLes lampadaires suivants ont franchi votre seuil d'alerte et sont probablement en panne : " + alertList + "."

    message += "\n\nVous pouvez situer ces installations en vous connectant au portail Et La Lumiere Fut : " + url
    message += "\n\nCordialement,\n\nL'Equipe La Lumiere Fut"

    mailInput = 'xyz97600@gmail.com'
    mailOutput = getAdminsMailAddress()
    msg = MIMEMultipart()
    msg['From'] = mailInput
    msg['To'] = mailOutput
    msg['Subject'] = 'Et La Lumière Fût - Des anomalies nécessitent votre attention'

    mailserver = smtplib.SMTP('smtp.gmail.com', 587)
    mailserver.ehlo()
    mailserver.starttls()
    mailserver.ehlo()
    mailserver.login(mailInput, 'PLI_2018')
    msg.attach(MIMEText(message))
    mailserver.sendmail(mailInput, mailOutput, msg.as_string())
    mailserver.quit()

    return

#Get device's last event
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

#Update device status based on last event
def changeDeviceStatus(device, newStatus):

    deviceEui = device['device']
    deviceStatus = device['status']
    deviceLat = device['latitude']
    deviceLong = device['longitude']
    deviceStreet = device['street']
    time = device['time']

    deviceStatus = float(newStatus) #device is suspicious or faulty, we'll adjust status accordingly

    json_body = [
        {
            "measurement": "devices",
            "tags": {
                "latitude": deviceLat,
                "longitude": deviceLong
            },
            "fields": {
                "status": deviceStatus,
                "device": deviceEui,
                "street": deviceStreet
            },
            "time": time
        }
    ]
    client.write_points(json_body) #and we update

    return

# Get user warning and alert settings
def getSettings():

    settings = []
    cursor.execute("SELECT * FROM alerts")
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]

    for row in rows:

        row = dict(zip(columns,row))
        settings.append(row)
        warning_delay = settings[0]['warning_threshold']
        alert_delay = settings[0]['alert_threshold']
        settings = {
                'warning_delay' : warning_delay,
                'alert_delay' : alert_delay
        }

    return settings

#Main function
def main():

    settings = getSettings() #retrieving user settings
    warning = settings['warning_delay']
    alert = settings['alert_delay']
    warningArray = []
    alertArray = []
    warningList = ''
    alertList = ''

    import time
    now = str(time.time())
    now = ".".join(now.split('.')[:1])
    now = int(now + '000000000') #hacky way to get nanoseconds :p

    warningDelayNanosecs = warning * 3600000000000 #warning delay is in hours, we want nanoseconds
    warningPeriodStartTime = now - warningDelayNanosecs #now we have a timespan

    alertDelayNanosecs =  alert * 3600000000000 #alert delay is in hours, we want nanoseconds
    alertPeriodStartTime = now - alertDelayNanosecs #now we have a timespan

    devices = getDevices()
    devicesLastData = getDevicesLastData(devices) #for each device, we get the latest data

    for device in devices:

        deviceEui = device['device']
        deviceStatus = device['status']

        deviceLastData = devicesLastData[deviceEui] #retrieving device's last data

        if (deviceLastData < alertPeriodStartTime): #device has not sent data since beginning of alert delay

            changeDeviceStatus(device, 0) #we'll set it to 0 (faulty)
            alertArray.append(deviceEui) #appending to array for email

        if (deviceLastData > alertPeriodStartTime and deviceLastData < warningPeriodStartTime): #device's last data is between the two thresholds, must be flagged as suspicious

            changeDeviceStatus(device, 0.5) #we'll set it to 0.5 (suspicious/warning)
            warningArray.append(deviceEui) #appending to array for email

        # else: we don't do anything, API will take care of setting device back to functionning as soon as data received (if device was previously flagged as suspicious or faulty)

    if (warningArray != []): #if some devices have been flagged suspicious
        warningList = ', '.join(warningArray) #we put them in a comma-separated string

    if (alertArray != []): #if some devices have been flagged as faulty
        alertList = ', '.join(alertArray) #we put them in a comma-separated string

    if (warningArray != [] or alertArray != []): #we'll only send email if there is an incident to report
        sendMailToAdmin(warningList, alertList)

    return

#Executing script
main()
