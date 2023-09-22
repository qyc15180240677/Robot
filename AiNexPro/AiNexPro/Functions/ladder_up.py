#!/usr/bin/python3
# coding=utf8
import sys
sys.path.append('/home/pi/AiNexPro/CameraCalibration/')
import cv2
import time
import math
import threading
import numpy as np
from hiwonder import Misc
from hiwonder import Board
from hiwonder import Camera
from hiwonder.PID import PID
from hiwonder import yaml_handle
import hiwonder.ActionGroupControl as AGC
from CalibrationConfig import *

# 上台阶
debug = False

#使用到的动作组，存储在/home/pi/AiNexPro/AiNexPro/ActionGroups/
go_forward = 'go_forward_normal'
go_forward_one_step = 'go_forward_one_step'
turn_right = 'turn_right_30'
turn_left  = 'turn_left_30'        
left_move = 'left_move'
right_move = 'right_move'
up = 'up'

y_up = 390

if sys.version_info.major == 2:
    print('Please run this program with python3!')
    sys.exit(0)

range_rgb = {
    'red': (0, 0, 255),
    'blue': (255, 0, 0),
    'green': (0, 255, 0),
    'black': (0, 0, 0),
    'white': (255, 255, 255),
}

#加载参数
param_data = np.load(calibration_param_path + '.npz')

#获取参数
dim = tuple(param_data['dim_array'])
k = np.array(param_data['k_array'].tolist())
d = np.array(param_data['d_array'].tolist())

print('加载参数完成')
print('dim:\n', dim)
print('k:\n', k)
print('d:\n', d)

#截取区域，1表示完全截取
scale = 1
#优化内参和畸变参数
p = cv2.fisheye.estimateNewCameraMatrixForUndistortRectify(k, d, dim ,None)
Knew = p.copy()
if scale:#change fov
    Knew[(0,1), (0,1)] = scale * Knew[(0,1), (0,1)]
map1, map2 = cv2.fisheye.initUndistortRectifyMap(k, d, np.eye(3), Knew, dim, cv2.CV_16SC2)

__target_color = ('black',)
# 设置检测颜色
def setBallTargetColor(target_color):
    global __target_color

    __target_color = target_color
    return (True, ())

lab_data = None
servo_data = None
def load_config():
    global lab_data, servo_data
    
    lab_data = yaml_handle.get_yaml_data(yaml_handle.lab_file_path)
    servo_data = yaml_handle.get_yaml_data(yaml_handle.servo_file_path)

load_config()

# 初始位置
def initMove():
    Board.setBusServoPulse(19, servo_data['servo1'], 500)
    Board.setBusServoPulse(20, 210, 500)    

object_center_x, object_center_y, object_angle = -2, -2, 0
# 变量重置
def reset():
    global object_center_x, object_center_y, object_angle
    
    object_center_x, object_center_y, object_angle = -2, -2, 0
    
# 初始化调用
def init():
    print("Up Init")
    load_config()
    initMove()
    reset()

__isRunning = False
# 开始玩法调用
def start():
    global __isRunning
    
    __isRunning = True
    print("Up Start")

# 停止玩法调用
def stop():
    global __isRunning
    
    __isRunning = False
    reset()        
    print("Up Stop")

# 退出玩法调用
def exit():
    global __isRunning
    __isRunning = False
    AGC.runActionGroup('stand')
    print("Up Exit")

#函数功能：识别特定颜色并且计算出云台舵机跟踪需要转动的值
#参数1：要识别的图像
#参数2：要识别的颜色，默认黄色
def color_identify(img, img_draw, target_color = 'yellow'):
    img_w = img.shape[:2][1]
    img_h = img.shape[:2][0]
    
    GaussianBlur_img = cv2.GaussianBlur(img, (3, 3), 0)#高斯模糊
    frame_lab = cv2.cvtColor(GaussianBlur_img, cv2.COLOR_BGR2LAB) #将图像转换到LAB空间
    frame_mask = cv2.inRange(frame_lab,
                                 (lab_data[target_color]['min'][0],
                                  lab_data[target_color]['min'][1],
                                  lab_data[target_color]['min'][2]),
                                 (lab_data[target_color]['max'][0],
                                  lab_data[target_color]['max'][1],
                                  lab_data[target_color]['max'][2]))  #对原图像和掩模进行位运算    
    opened = cv2.morphologyEx(frame_mask, cv2.MORPH_OPEN, np.ones((3,3),np.uint8))#开运算
    closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, np.ones((9,9),np.uint8))#闭运算
    detected_edges = cv2.Canny(closed, 50, 450, apertureSize = 3)#边缘检测
    
    lines = cv2.HoughLinesP(detected_edges, 1, np.pi/180, 60, minLineLength=50, maxLineGap=100)
    kk = []
    angle = 0
    center_y = 0
    x_min = 640
    x_max = 0
    center_x = 0
    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            if y1 > center_y:
                center_y = y1
            if y2 > center_y:
                center_y = y2
            if x1 < x_min:
                x_min = x1
            if x2 < x_min:
                x_min = x2
            if x1 > x_max:
                x_max = x1
            if x2 > x_max:
                x_max = x2
            k = int(math.degrees(math.atan2(y2 - y1, x2 - x1)))
            kk.append(k)
            cv2.line(img_draw, (x1, y1), (x2, y2), (255, 0, 0), 2)
        angle = int(np.mean(kk))
    center_x = (x_min + x_max) / 2
    if debug:
        cv2.imshow('Canny', detected_edges)
        cv2.imshow('closed', closed)
        print('angle:', angle)
    return center_x, center_y, angle      

x_center = 320
#机器人跟踪线程
def move():      
    while True:
        if __isRunning and not debug:          
            if object_center_y >= 0:
                #print(object_center_y)
                if object_center_y < 250:
                    AGC.runActionGroup(go_forward)
                elif 5 <= object_angle < 90:
                    AGC.runActionGroup(turn_right)
                    time.sleep(0.5)
                elif -5 > object_angle > -90:
                    AGC.runActionGroup(turn_left)
                    time.sleep(0.5)
                elif object_center_x - x_center > 30:               
                    AGC.runActionGroup(right_move)
                elif object_center_x - x_center < -30:#
                    AGC.runActionGroup(left_move)
                elif y_up > object_center_y >= 250:
                    AGC.runActionGroup(go_forward_one_step)
                    time.sleep(0.5)
                elif object_center_y >= y_up:
                    AGC.runActionGroup(up)
                else:
                    time.sleep(0.01)
            elif object_center_y == -1:
                AGC.runActionGroup(go_forward)
        else:
            time.sleep(0.01)
            
#作为子线程开启
th = threading.Thread(target=move)
th.setDaemon(True)
th.start()

def run(img):
    global object_center_x, object_center_y, object_angle
    
    img_copy = img.copy()
    img_h, img_w = img.shape[:2]

    #cv2.line(img, (int(img_w/2), int(img_h/2 - 10)), (int(img_w/2), int(img_h/2 + 10)), (0, 255, 255), 2)
    
    if not __isRunning or __target_color == ():
        return img
    
    object_center_x, object_center_y, object_angle = color_identify(img, img_copy, target_color = __target_color[0])
    
    cv2.line(img_copy, (0, y_up), (img_w, y_up), (0, 255, 255), 2)
    return img_copy

if __name__ == '__main__': 
    debug = False
    if debug:
        print('Debug mode')
    init()
    start()
    __target_color = ('yellow',)
    my_camera = Camera.Camera()
    my_camera.camera_open()
    AGC.runAction('stand')
    while True:
        img = my_camera.frame
        if img is not None:
            frame = img.copy()
            dst = cv2.remap(frame, map1, map2, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
            Frame = run(dst)           
            cv2.imshow('Frame', Frame)
            key = cv2.waitKey(1)
            if key == 27:
                break
        else:
            time.sleep(0.01)
    my_camera.camera_close()
    cv2.destroyAllWindows()
