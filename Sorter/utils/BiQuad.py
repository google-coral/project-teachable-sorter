#!/usr/bin/env python
#
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

import math

class BiQuadFilter(object):

    def __init__(self, filter_type, Fc, Q, peakGainDB):
        self.z1 = self.z2 = 0.0
        self.a0 = self.a1 = self.a2 = self.b1 = self.b2 = 0.0

        self.setBiquad(filter_type, Fc, Q, peakGainDB)
        self.calcBiquad()

    def setType(filter_type):
        self.type = filter_type
        calcBiquad()
    def setQ(Q):
        self.Q = Q
        calcBiquad()
    def setFc(Fc):
        self.Fc = Fc
        calcBiquad()

    def setPeakGain(peakGainDB):
        this.peakGain = peakGainDB
        calcBiquad()

    def setBiquad(self, filter_type, Fc, Q, peakGainDB):
        self.type = filter_type
        self.Q = Q
        self.Fc = Fc
        self.peakGain = peakGainDB
        self.calcBiquad()

    def calcBiquad(self):
        norm = None
        V = pow(10, abs(self.peakGain) / 20.0)
        K = math.tan(math.pi * self.Fc)
        if self.type == 'low':
            norm = 1 / (1 + K / self.Q + K * K)
            self.a0 = K * K * norm
            self.a1 = 2 * self.a0
            self.a2 = self.a0
            self.b1 = 2 * (K * K - 1) * norm
            self.b2 = (1 - K / self.Q + K * K) * norm

        if self.type == 'high':
            norm = 1 / (1 + K / self.Q + K * K)
            self.a0 = 1 * norm
            self.a1 = -2 * self.a0
            self.a2 = self.a0
            self.b1 = 2 * (K * K -1) * norm
            self.b2 = (1 - K / self.Q + K * K) * norm
        if self.type == 'band':
            norm = 1 / (1 + K / self.Q + K * K)
            self.a0 = K / self.Q * norm
            self.a1 = 0
            self.a2 = -self.a0
            self.b1 = 2 * (K * K - 1) * norm
            self.b2 = (1 - K / self.Q + K * K) * norm

    def process(self, input_float):
        out = input_float * self.a0 + self.z1
        self.z1 = input_float * self.a1 + self.z2 - self.b1 * out
        self.z2 = input_float * self.a2 - self.b2 * out
        return out



