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
from hiwonder.PID import PID
from hiwonder import yaml_handle
import hiwonder.ActionGroupControl as AGC

# 颜色跟踪
debug = False
x_center = 455
y_min = 240
y_dis = y_min

x_1 = 680
x_2 = 320
y_2 = y_dis + 300
x_pid = PID(P=0.06, I=0.01, D=0.002)#pid初始化
y_pid = PID(P=0.06, I=0.01, D=0.002)

X = 0
Y = 0
dis_ok = False
action_finish = True

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

__target_color = ('red',)

lab_data = None
servo_data = None
def load_config():
    global lab_data, servo_data
    
    lab_data = yaml_handle.get_yaml_data(yaml_handle.lab_file_path)
    servo_data = yaml_handle.get_yaml_data(yaml_handle.servo_file_path)

load_config()

x_dis = x_center
# 初始位置
def initMove():
    Board.setBusServoPulse(19, x_center, 500)
    Board.setBusServoPulse(20, y_min, 500)    

# 变量重置
def reset():
    global X, Y
    global x_dis
    global y_dis
    global dis_ok   
    global action_finish
    global __target_color
    
    X = 0
    Y = 0
    x_pid.clear()
    y_pid.clear()
    dis_ok = False
    action_finish = True
    x_dis = x_center
    y_dis = y_min
    __target_color = ()
    
def init():
    print("ColorTrack Init")
    load_config()
    initMove()
    reset()

__isRunning = False
def start():
    global __isRunning
    
    __isRunning = True
    print("ColorTrack Start")

def stop():
    global __isRunning
    
    __isRunning = False
    reset()        
    print("ColorTrack Stop")

def exit():
    global __isRunning
    __isRunning = False
    AGC.runActionGroup('stand')
    print("ColorTrack Exit")

# 找出面积最大的轮廓
# 参数为要比较的轮廓的列表
def getAreaMaxContour(contours, area_min=10):
    contour_area_temp = 0
    contour_area_max = 0
    area_max_contour = None

    for c in contours:  # 历遍所有轮廓
        contour_area_temp = math.fabs(cv2.contourArea(c))  # 计算轮廓面积
        if contour_area_temp > contour_area_max:
            contour_area_max = contour_area_temp
            if contour_area_temp >= area_min:  # 只有在面积大于设定值时，最大面积的轮廓才是有效的，以过滤干扰
                area_max_contour = c

    return area_max_contour, contour_area_max  # 返回最大的轮廓

size = (320, 240)
#函数功能：识别特定颜色并且计算出云台舵机跟踪需要转动的值
#参数1：要识别的图像
#参数2：要识别的颜色，默认蓝色
def color_identify(img, img_draw, target_color = 'blue'):
    global X, Y    
    global x_dis, y_dis
    global ball_status, dis_ok
    
    img_w = img.shape[:2][1]
    img_h = img.shape[:2][0]
    
    img_resize = cv2.resize(img, (size[0], size[1]), interpolation = cv2.INTER_CUBIC)
    
    GaussianBlur_img = cv2.GaussianBlur(img_resize, (3, 3), 0)#高斯模糊
    frame_lab = cv2.cvtColor(GaussianBlur_img, cv2.COLOR_BGR2LAB) #将图像转换到LAB空间
    frame_mask = cv2.inRange(frame_lab,
                                 (lab_data[target_color]['min'][0],
                                  lab_data[target_color]['min'][1],
                                  lab_data[target_color]['min'][2]),
                                 (lab_data[target_color]['max'][0],
                                  lab_data[target_color]['max'][1],
                                  lab_data[target_color]['max'][2]))  #对原图像和掩模进行位运算    
    opened = cv2.morphologyEx(frame_mask, cv2.MORPH_OPEN, np.ones((3,3),np.uint8))#开运算
    closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, np.ones((3,3),np.uint8))#闭运算
    contours = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)[-2] #找出所有外轮廓
    areaMax_contour = getAreaMaxContour(contours, area_min=3)[0] #找到最大的轮廓
    
    X = 999
    Y = 999
    radius = 0
    if areaMax_contour is not None:
        if target_color != 'black':
            (X, Y), radius = cv2.minEnclosingCircle(areaMax_contour) #获取最小外接圆的圆心以及半径
            X = int(Misc.map(X, 0, size[0], 0, img_w))
            Y = int(Misc.map(Y, 0, size[1], 0, img_h))
            radius = int(Misc.map(radius, 0, size[0], 0, img_w))            
            cv2.circle(img_draw, (X, Y), radius, range_rgb[target_color], 2)#用圆圈框出识别的颜色
            if radius > 5:#半径太小的不做处理
                ########pid控制#########
                #x_pid处理的是控制水平的舵机，y_pid处理控制竖直的舵机
                #以图像的中心点的x，y坐标作为设定的值，以当前识别的颜色中心x，y坐标作为输入
            
                x_pid.SetPoint = img_w/2.0#设定
                x_pid.update(X)#当前
                x_pwm = x_pid.output#输出
                x_dis += x_pwm
                x_dis = int(x_dis)
                #限制处理，限制水平舵机的旋转范围为0-180,默认的是0-240
                if x_dis < 125:
                    x_dis = 125
                elif x_dis > 875:
                    x_dis = 875                 
                
                y_pid.SetPoint = img_h/2.0
                y_pid.update(img_h - Y)#图像的纵像素点从上往下是增大的，而舵机从上往下转动时值减小，故做此处理
                y_pwm = y_pid.output
                y_dis -= y_pwm
                y_dis = int(y_dis)
                #限制处理，防止舵机舵转
                if y_dis < y_min:
                    y_dis = y_min
                elif y_dis > 500:
                    y_dis = 500
                ball_status = 1
                if action_finish:
                    dis_ok = True
                #print(x_dis)
            else:
                X, Y = -999, -999
                ball_status = 0
    else:
        ball_status = 0
        X, Y = -999, -999
        
#云台跟踪
def track():
    global dis_ok
    global action_finish
        
    while True:
        if __isRunning:
            if dis_ok is True:
                dis_ok = False
                action_finish = False
                Board.setBusServoPulse(19, x_dis, 20)
                Board.setBusServoPulse(20, y_dis, 20)
                if debug:
                    print('x_dis:', x_dis)
                time.sleep(0.02)
                action_finish = True
            else:
                time.sleep(0.01)
        else:
            time.sleep(0.01)
                
#作为子线程开启
th = threading.Thread(target=track)
th.setDaemon(True)
th.start()

def run(img):
    img_copy = img.copy()
    img_h, img_w = img.shape[:2]

    cv2.line(img_copy, (int(img_w/2 - 10), int(img_h/2)), (int(img_w/2 + 10), int(img_h/2)), (0, 255, 255), 2)
    cv2.line(img_copy, (int(img_w/2), int(img_h/2 - 10)), (int(img_w/2), int(img_h/2 + 10)), (0, 255, 255), 2)
    
    if not __isRunning or __target_color == ():
        return img
    
    color_identify(img, img_copy, target_color=__target_color[0])

    return img_copy

if __name__ == '__main__': 
    debug = False
    if debug:
        print('Debug mode')
    init()
    start()
    __target_color = ('blue',)
    AGC.runAction('stand')
    my_camera = Camera.Camera()
    my_camera.camera_open()
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
