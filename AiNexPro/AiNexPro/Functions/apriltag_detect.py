#!/usr/bin/python3
# coding=utf8
import sys
import cv2
import time
import math
import threading
import numpy as np
from hiwonder import Misc
from hiwonder import Board
from hiwonder import Camera
from hiwonder import apriltag
from hiwonder import yaml_handle
import hiwonder.ActionGroupControl as AGC

# 标签检测

# 用到的动作组名称
id_1_action = 'greet'
id_2_action = 'twist'
id_3_action = 'wave'

# 初始位置
def initMove():
    Board.setBusServoPulse(19, 500, 500)
    Board.setBusServoPulse(20, 500, 500)

tag_id = None
haved_detect = False
# 变量重置
def reset():
    global tag_id
    global haved_detect   

    tag_id = None
    haved_detect = False

# app初始化调用
def init():
    print("ApriltagDetect Init")
    initMove()

__isRunning = False
# app开始玩法调用
def start():
    global __isRunning
    reset()
    __isRunning = True
    print("ApriltagDetect Start")

# app停止玩法调用
def stop():
    global __isRunning
    __isRunning = False
    print("ApriltagDetect Stop")

# app退出玩法调用
def exit():
    global __isRunning
    __isRunning = False
    AGC.runActionGroup('stand')
    print("ApriltagDetect Exit")

# 检测apriltag
detector = apriltag.Detector(searchpath=apriltag._get_demo_searchpath())
def apriltagDetect(img):   
    gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
    detections = detector.detect(gray, return_image=False)
    if len(detections) != 0:
        for detection in detections:                       
            corners = np.rint(detection.corners)  # 获取四个角点
            cv2.drawContours(img, [np.array(corners, np.int)], -1, (0, 255, 255), 5, cv2.LINE_AA)
            tag_family = str(detection.tag_family, encoding='utf-8')  # 获取tag_family

            if tag_family == 'tag36h11':
                tag_id = str(detection.tag_id)  # 获取tag_id
                return tag_id
            else:
                return None
    else:
        return None

#执行动作组
def move(): 
    global haved_detect

    while True:
        if __isRunning:
            if haved_detect:
                if tag_id == '1':
                    AGC.runAction(id_1_action)
                elif tag_id == '2':
                    AGC.runAction(id_2_action)
                elif tag_id == '3':
                    AGC.runAction(id_3_action)
                time.sleep(0.5)
                haved_detect = False
            else:
                time.sleep(0.01)
        else:
            time.sleep(0.01)

#启动动作的线程
th = threading.Thread(target=move)
th.setDaemon(True)
th.start()

def run(img):
    global tag_id
    global haved_detect

    if not __isRunning:
        return img
    
    tag_id = apriltagDetect(img) # apriltag检测
    if tag_id is not None and not haved_detect:
        haved_detect = True
    cv2.putText(img, tag_id, (10, img.shape[0] - 20), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 255, 255), 3)
    return img

if __name__ == '__main__':
    init()
    start()
    my_camera = Camera.Camera()
    my_camera.camera_open()

    AGC.runActionGroup('stand')
    while True:
        img = my_camera.frame
        if img is not None:
            frame = img.copy()
            Frame = run(frame)
            cv2.imshow('Frame', Frame)
            key = cv2.waitKey(1)
            if key == 27:
                break
        else:
            time.sleep(0.01)
    my_camera.camera_close()
    cv2.destroyAllWindows()
