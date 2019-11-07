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
import PySpin
import cv2
class FlirBFS(object):
    # takes in a mode, a path to a model, and a callback function that gets called each new frame
    def __init__(self, on_new_frame=None, frame_rate=120, display=False):
        self.system = PySpin.System.GetInstance()
        self.cam_list = self.system.GetCameras()
        self.frame_rate = frame_rate
        self.display = display
        self.on_new_frame = on_new_frame
        if len(self.cam_list) == 0:
            raise Exception('No FLIR camera connected!')

        self.cam = self.cam_list[0]

    # This function pre configures camera settings on the flir.
    def run_cam(self):
        try:
            self.cam.Init()

            # self.nodemap_tldevice = cam.GetTLdeviceNodeMap()
            nodemap = self.cam.GetNodeMap()
            stream_nodemap = self.cam.GetTLStreamNodeMap()

            # Configure Camera Settings
            self.cam.TriggerMode.SetValue(PySpin.TriggerMode_Off)
            self.cam.AcquisitionFrameRateEnable.SetValue(True)
            self.cam.AcquisitionFrameRate.SetValue(self.frame_rate)

            handling_mode = PySpin.CEnumerationPtr(
                stream_nodemap.GetNode('StreamBufferHandlingMode'))
            handling_mode_entry = handling_mode.GetEntryByName(
                'NewestOnly')
            handling_mode.SetIntValue(handling_mode_entry.GetValue())

            self.acquire_images(nodemap, stream_nodemap)
        except PySpin.SpinnakerException as ex:
            print('Error {}'.format(ex))

    def acquire_images(self, nodemap, stream_nodemap):

        self.cam.BeginAcquisition()

        while True:
            try:
                image_result = self.cam.GetNextImage()
                if image_result.IsIncomplete():
                    print('Image incomplete with image status {} ...'.format(image_result.GetImageStatus()))
                else:
                    color_image = image_result.Convert(PySpin.PixelFormat_BGR8, PySpin.HQ_LINEAR)
                    open_cv_mat = color_image.GetNDArray()
                    open_cv_mat = cv2.cvtColor(open_cv_mat, cv2.COLOR_BGR2RGB)
                    if (self.on_new_frame != None):
                        self.on_new_frame(cv_mat=open_cv_mat)

                    if (self.display == True):
                        cv2.imshow('sorter_camera', open_cv_mat)
                        cv2.waitKey(1)
            except PySpin.SpinnakerException as ex:
                print('Error {}'.format(ex))
                del self.cam

                # Clear camera list before releasing system
                self.cam_list.Clear()

                # Release system instance
                self.system.ReleaseInstance()
