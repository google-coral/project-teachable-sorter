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


# this file will contain the main sorter class
# this will handle grabbing the flir images, determining

from utils import CameraWebsocketHandler
from utils.BiQuad import BiQuadFilter
from functools import partial
from PIL import Image
from scipy import ndimage
import edgetpu.classification.engine
import threading
import asyncio
import base64
import utils
import cv2
import argparse
import sys
import RPi.GPIO as GPIO
# Path to edgetpu compatible model
model_path = '../model.tflite'

# NOTE: can either be 'train' to classify images using edgetpu or 'sort' to just send images to TM2
mode = "sort"
sendPin = 7
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)
GPIO.setup(sendPin, GPIO.OUT, initial=GPIO.LOW)
filter_type = 'zone'
# biquad params : type, Fc, Q, peakGainDB
bq = BiQuadFilter('band', 0.1, 0.707, 0.0)
def send_over_ws(msg, cam_sockets):
    for ws in cam_sockets:
        ws.write_message(msg)

def format_img_tm2(cv_mat):
    ret, buf = cv2.imencode('.jpg', cv_mat)
    encoded  =  base64.b64encode(buf)
    return encoded.decode('ascii')


# this is the logic that determines if there is a sorting target in the center of the frame
def is_good_photo(img, width, height, mean, sliding_window):
    detection_zone_height = 20
    detection_zone_interval = 5
    threshold = 4.5
    if (filter_type == 'zone'):
        detection_zone_avg = img[height // 2 : (height // 2) + detection_zone_height : detection_zone_interval, 0:-1:3].mean()
    if (filter_type == 'biquad2d'):
        detection_zone_avg = abs(bq.process(img.mean))
    if (filter_type == 'biquad'):
        detection_zone_avg = abs(bq.process(img[height // 2: (height // 2) + detection_zone_height: detection_zone_interval, 0:-1:3].mean()))
    if (filter_type == 'center_of_mass'):
        center = scipy.ndimage.measurements.center_of_mass(img)
        detection_zone_avg = (center[0] + center[1]) / 2


    if len(sliding_window) > 30:
        mean[0] = utils.mean_arr(sliding_window)
        sliding_window.clear()

    else:
        sliding_window.append(detection_zone_avg)
    # print(detection_zone_avg)
    if mean[0] != None and abs(detection_zone_avg - mean[0]) > threshold:
        print("Target Detected Taking Picture")
        return True

    return False

# call each time you  have a new frame
def on_new_frame(cv_mat, engine, mean, sliding_window, send_over_ws, cam_sockets):
    img_pil = Image.fromarray(cv_mat)

    width, height = img_pil.size

    is_good_frame = is_good_photo(cv_mat, width, height, mean, sliding_window)
    if (is_good_frame):
        # NOTE: Teachable Machine 2 works on images of size 224x224 and will resize all inputs
        # to that size. so we have to make sure our edgetpu converted model is fed similar images.
        if (width, height) != (224, 224):
            img_pil.resize((224, 224))

        if (mode == 'train'):
            message = dict()
            message['image'] = format_img_tm2(cv_mat)
            message['shouldTakePicture'] = True
            send_over_ws(message, cam_sockets)
            # time.sleep(0.25) NOTE: debounce this at a rate depending on your singulation rate


        elif (mode == 'sort'):
            classification_result = engine.ClassifyWithImage(img_pil)
            print(classification_result)
            if classification_result [0][0] == 0 and  classification_result[0][1] > 0.95:
                GPIO.output(sendPin, GPIO.HIGH)
            else:
                GPIO.output(sendPin, GPIO.LOW)
            # Here you can actuate the sorting end-effector through GPIO, etc.



if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    mode_parser = parser.add_mutually_exclusive_group(required=False)
    mode_parser.add_argument('--train', dest='will_sort', action='store_false')
    mode_parser.add_argument('--sort', dest='will_sort', action='store_true')

    filter_parse = parser.add_mutually_exclusive_group(required=False)
    filter_parse.add_argument('--zone-activation', dest='zone', action='store_true')
    filter_parse.add_argument('--biquad', dest='biquad', action='store_true')
    filter_parse.add_argument('--biquad2d', dest='biquad2d', action='store_true')
    filter_parse.add_argument('--center-of-mass', dest='center_of_mass', action='store_true')

    camera_parse = parser.add_mutually_exclusive_group(required=False)
    camera_parse.add_argument('--flir', dest='flir', action='store_true')
    camera_parse.add_argument('--opencv', dest='opencv', action='store_true')
    camera_parse.add_argument('--arducam', dest='arducam', action='store_true')

    parser.set_defaults(will_sort=True)
    args = parser.parse_args()

    # Start the tornado websocket server
    cam_sockets = []
    new_loop = asyncio.new_event_loop()
    server_thread = threading.Thread(target=CameraWebsocketHandler.start_server, args=(new_loop, cam_sockets, ))
    server_thread.start()

    if args.will_sort:
        engine = edgetpu.classification.engine.ClassificationEngine(model_path)
        mode = "sort"
    else:
        mode = "train"

    #  parse filter type
    if args.zone: filter_type = 'zone'
    elif args.biquad: filter_type = 'biquad'
    elif args.biquad2d: filter_type = 'biquad2d'
    elif args.center_of_mass: filter_type  = 'center_of_mass'

    mean = [None]
    sliding_window = []

    if (args.flir):
        import FLIR
        print("Initializing Flir Camera")
        cam = FLIR.FlirBFS(on_new_frame=partial(on_new_frame, engine=engine, mean=mean, sliding_window=sliding_window,
                                                send_over_ws=send_over_ws, cam_sockets=cam_sockets),
                        display=True, frame_rate=120)
        cam.run_cam();
    elif (args.arducam):
        raise Exception("Arducam Support Coming")
    else:
        cap = cv2.VideoCapture(0)
        while cap.isOpened():
            ret,frame = cap.read()
            if  not ret:
                break
            cv2_im  = frame
            pil_im = Image.fromarray(cv2_im)
            pil_im.resize((224, 224))
            pil_im.transpose(Image.FLIP_LEFT_RIGHT)
            cv2.imshow('frame', cv2_im)
            on_new_frame(engine, mean, sliding_window, send_over_ws, cam_sockets)
            if cv2.waitKey(1) & 0xff  == ord('q'):
                break
        cap.release()
        cv2.destroyAllWindows()
        print('Initializing opencv Video Stream')


