# Copyright 2019 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import tornado
import tornado.websocket
import tornado.ioloop
from tornado.iostream import IOStream
import threading
import time
import base64
import sys, os
import asyncio

cam_sockets = None

class CameraWebsocketHandler(tornado.websocket.WebSocketHandler):
    def open(self):
        global cam_sockets
        cam_sockets.append(self)
        print('new camera connection')

    def on_message(self, message):
        print (message)

    def on_close(self):
        global cam_sockets
        cam_sockets.remove(self)
        print('camera connection closed')

    def check_origin(self, origin):
        return True

def start_server(loop, cs):
    global cam_sockets
    cam_sockets = cs
    asyncio.set_event_loop(loop)

    cam_app = tornado.web.Application([
        (r'/', CameraWebsocketHandler)
    ])

    cam_server = (cam_app)
    cam_server.listen(8889)
    tornado.ioloop.IOLoop.instance().start()

def signal_handler(signum, frame):
    print("Interrupt caught")
    tornado.ioloop.IOLoop.instance().stop()
    server_thread.stop()
