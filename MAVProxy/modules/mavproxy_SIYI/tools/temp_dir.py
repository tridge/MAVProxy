#!/usr/bin/env python3

# save images in therm cap

import sys
import numpy as np
import cv2
import time
import glob
import os
from MAVProxy.modules.lib.mp_image import MPImage
from pymavlink import mavutil

from argparse import ArgumentParser
parser = ArgumentParser(description=__doc__)

parser.add_argument("--min-temp", default=None, type=float, help="min temperature")
parser.add_argument("--siyi-log", default=None, type=float, help="SIYI binlog")
parser.add_argument("--gamma", default=3, type=float, help="image display gamma")
parser.add_argument("dirname", default=None, type=str, help="directory")
args = parser.parse_args()

DNAME=args.dirname
mouse_temp=-1
tmin = -1
tmax = -1
last_data = None
C_TO_KELVIN = 273.15

next_file = 0
found_index = []

def update_title():
    global tmin, tmax, mouse_temp
    cv2.setWindowTitle('Thermal', "Thermal: (%.1fC to %.1fC) %.1fC" % (tmin, tmax, mouse_temp))

def click_callback(event, x, y, flags, param):
    global last_data, mouse_temp
    if last_data is None:
        return
    p = last_data[y*640+x]
    mouse_temp = p - C_TO_KELVIN
    update_title()

def display_file(fname):
    global mouse_temp, tmin, tmax, last_data
    global next_file, found_index
    #print('Importing: ', fname)
    a = np.fromfile(fname, dtype='>u2')
    if len(a) != 640 * 512:
        print("Bad size %u" % len(a))
        return
    # get in Kelvin
    a = (a / 64.0)

    C_TO_KELVIN = 273.15

    maxv = a.max()
    minv = a.min()

    tmin = minv - C_TO_KELVIN
    tmax = maxv - C_TO_KELVIN

    if args.min_temp is not None and tmax < args.min_temp:
        return

    print("[%u] Max=%.3fC Min=%.3fC" % (next_file, tmax, tmin))
    if maxv <= minv:
        print("Bad range")
        return

    found_index.append(next_file)
    last_data = a

    # convert to 0 to 65535
    a = (a - minv) * 65535.0 / (maxv - minv)

    if args.gamma:
        a = np.power(a / 65535.0, 1.0 / args.gamma) * 65535.0

    # convert to uint8 greyscale as 640x512 image
    a = a.astype(np.uint16)
    a = a.reshape(512, 640)

    cv2.namedWindow('Thermal', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('Thermal', 640, 512)
    cv2.imshow('Thermal', a)
    cv2.setMouseCallback('Thermal', click_callback)
    cv2.setWindowTitle('Thermal', "Thermal[%u]: (%.1fC to %.1fC) %.1fC" % (found_index[-1], tmin, tmax, mouse_temp))

    # wait for enter key
    while True:
        key = cv2.waitKey(0)
        if key == 13:
            break
        if key == ord('p') and len(found_index)>1:
            next_file = max(0, found_index[-2] - 1)
            print("Going to %u" % (next_file+1))
            found_index = found_index[:-2]
            break

flist = sorted(glob.glob(DNAME + "/*bin"))

while next_file < len(flist):
    display_file(flist[next_file])
    next_file = next_file + 1
