# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from awscrt import io, mqtt, auth, http
from awsiot import mqtt_connection_builder
import time as t
import json
import busio
import board
import heapq
import itertools
from gpiozero import Button
from datetime import datetime
import adafruit_amg88xx
import pytz

import settings
from lib import util

# Define ENDPOINT, CLIENT_ID, PATH_TO_CERT, PATH_TO_KEY, PATH_TO_ROOT, MESSAGE, TOPIC, and RANGE
ENDPOINT = settings.AWS_IOT_ENDPOINT
CLIENT_ID = settings.AWS_IOT_THING_NAME
PATH_TO_CERT = settings.AWS_CERTS_PATH_CERTIFICATE
PATH_TO_KEY = settings.AWS_CERTS_PATH_PRIVATEKEY
PATH_TO_ROOT = settings.AWS_CERTS_PATH_ROOTCA
TOPIC = settings.MQTT_TOPIC

def get_data():
    return max(list(itertools.chain.from_iterable(sensor.pixels)))

def print_data():
    print(get_data())
    
# センサからデータを取得し、AWS に送信する 
def get_sensordata_and_send_to_aws():

    data = get_data()
    payload = {
        'device_id': settings.MQTT_DEVICE_ID,
        'timestamp': None,
        'temperature': None,
        'verbose_timestamp': None

    }

    now = datetime.now(pytz.timezone('Asia/Tokyo'))

    payload['timestamp'] = str(util.datetime_to_unixtime_ms(now))
    payload['verbose_timestamp'] = now.strftime("%Y-%m-%d %H:%M:%S.") + \
                                   "%03d" % (now.microsecond // 1000) + "+0900"

    # 温度・湿度・照度を取得
    payload['temperature'] = data

    payload_json = json.dumps(payload, indent=4)
    print(json.dumps(payload))

    # AWS IoT に Publish
    mqtt_connection.publish(topic=TOPIC, payload=json.dumps(payload), qos=mqtt.QoS.AT_LEAST_ONCE)


# Spin up resources
event_loop_group = io.EventLoopGroup(1)
host_resolver = io.DefaultHostResolver(event_loop_group)
client_bootstrap = io.ClientBootstrap(event_loop_group, host_resolver)
mqtt_connection = mqtt_connection_builder.mtls_from_path(
            endpoint=ENDPOINT,
            cert_filepath=PATH_TO_CERT,
            pri_key_filepath=PATH_TO_KEY,
            client_bootstrap=client_bootstrap,
            ca_filepath=PATH_TO_ROOT,
            client_id=CLIENT_ID,
            clean_session=False,
            keep_alive_secs=6
            )
print("Connecting to {} with client ID '{}'...".format(
        ENDPOINT, CLIENT_ID))
# Make the connect() call
connect_future = mqtt_connection.connect()
# Future.result() waits until a result is available
connect_future.result()
print("Connected!")
# Publish message to server desired number of times.
print('Begin Publish')

# I2Cバスの初期化
i2c_bus = busio.I2C(board.SCL, board.SDA)

# センサーの初期化
# アドレスを68に指定
sensor = adafruit_amg88xx.AMG88XX(i2c_bus, addr=0x68)

# センサーの初期化待ち
t.sleep(.1)

# initialize button
button = Button(13)
try:
    while(True):
        button.when_pressed = get_sensordata_and_send_to_aws
except KeyboardInterrupt:
    print('Publish End')
    disconnect_future = mqtt_connection.disconnect()
    disconnect_future.result()