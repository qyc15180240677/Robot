#!/usr/bin/python3
# coding=utf8
import sys
import cv2
import math
import time
import threading
import numpy as np
from hiwonder import Misc
from hiwonder import Board
from hiwonder import Camera
from hiwonder import yaml_handle
import hiwonder.ActionGroupControl as AGC

# 颜色检测
debug = False

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

# 找出面积最大的轮廓
# 参数为要比较的轮廓的列表
def getAreaMaxContour(contours):
    contour_area_temp = 0
    contour_area_max = 0
    area_max_contour = None

    for c in contours:  # 历遍所有轮廓
        contour_area_temp = math.fabs(cv2.contourArea(c))  # 计算轮廓面积
        if contour_area_temp > contour_area_max:
            contour_area_max = contour_area_temp
            if contour_area_temp > 50:  # 只有在面积大于50时，最大面积的轮廓才是有效的，以过滤干扰
                area_max_contour = c

    return area_max_contour, contour_area_max  # 返回最大的轮廓

lab_data = None
def load_config():
    global lab_data
    
    lab_data = yaml_handle.get_yaml_data(yaml_handle.lab_file_path)

load_config()

# 初始位置
def initMove():
    Board.setPWMServoPulse(19, 500, 500)
    Board.setPWMServoPulse(20, 500, 500)

color_list = []
detect_color = 'None'
action_finish = True
draw_color = range_rgb["black"]
# 变量重置
def reset():
    global draw_color
    global color_list
    global detect_color
    global action_finish
    
    color_list = []
    detect_color = 'None'
    action_finish = True
    draw_color = range_rgb["black"]
    
# 初始化调用
def init():
    print("ColorDetect Init")
    initMove()

__isRunning = False
# 开始玩法调用
def start():
    global __isRunning
    reset()
    __isRunning = True
    print("ColorDetect Start")

# 停止玩法调用
def stop():
    global __isRunning
    __isRunning = False
    print("ColorDetect Stop")

# 退出玩法调用
def exit():
    global __isRunning
    __isRunning = False
    AGC.runActionGroup('stand')
    print("ColorDetect Exit")

def buzzer_di(di_time):
    Board.setBuzzer(0)
    Board.setBuzzer(1)
    time.sleep(di_time)
    Board.setBuzzer(0)

def move():
    global draw_color
    global detect_color
    global action_finish

    while True:
        if __isRunning and not debug:
            if detect_color != 'None':
                action_finish = False
                if detect_color == 'red':
                    buzzer_di(0.3)
                    Board.setBusServoPulse(20, 600, 200)
                    time.sleep(0.2)
                    Board.setBusServoPulse(20, 400, 200)
                    time.sleep(0.2)
                    Board.setBusServoPulse(20, 600, 200)
                    time.sleep(0.2)
                    Board.setBusServoPulse(20, 400, 200)
                    time.sleep(0.2)
                    Board.setBusServoPulse(20, 500, 200)
                    time.sleep(0.2)
                    detect_color = 'None'
                    draw_color = range_rgb["black"]                    
                    time.sleep(1)
                elif detect_color == 'green' or detect_color == 'blue':
                    Board.setBusServoPulse(19, 600, 200)
                    time.sleep(0.2)
                    Board.setBusServoPulse(19, 400, 200)
                    time.sleep(0.2)
                    Board.setBusServoPulse(19, 600, 200)
                    time.sleep(0.2)
                    Board.setBusServoPulse(19, 400, 200)
                    time.sleep(0.2)
                    Board.setBusServoPulse(19, 500, 200)
                    time.sleep(0.2)
                    detect_color = 'None'
                    draw_color = range_rgb["black"]                    
                    time.sleep(1)
                else:
                    time.sleep(0.01)                
                action_finish = True                
                detect_color = 'None'
            else:
               time.sleep(0.01)
        else:
            time.sleep(0.01)

# 运行子线程
th = threading.Thread(target=move)
th.setDaemon(True)
th.start()

size = (320, 240)
def run(img):
    global draw_color
    global color_list
    global detect_color
    global action_finish
    
    img_copy = img.copy()
    img_h, img_w = img.shape[:2]

    if not __isRunning:
        return img

    frame_resize = cv2.resize(img_copy, size, interpolation=cv2.INTER_NEAREST)
    frame_gb = cv2.GaussianBlur(frame_resize, (3, 3), 3)      
    frame_lab = cv2.cvtColor(frame_gb, cv2.COLOR_BGR2LAB)  # 将图像转换到LAB空间

    max_area = 0
    color_area_max = None    
    areaMaxContour_max = 0
    
    if action_finish:
        for i in lab_data:
            if i in ['red', 'green', 'blue']:
                frame_mask = cv2.inRange(frame_lab,
                                             (lab_data[i]['min'][0],
                                              lab_data[i]['min'][1],
                                              lab_data[i]['min'][2]),
                                             (lab_data[i]['max'][0],
                                              lab_data[i]['max'][1],
                                              lab_data[i]['max'][2]))  #对原图像和掩模进行位运算
                eroded = cv2.erode(frame_mask, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)))  #腐蚀
                dilated = cv2.dilate(eroded, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))) #膨胀
                if debug:
                    cv2.imshow(i, dilated)
                contours = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)[-2]  #找出轮廓
                areaMaxContour, area_max = getAreaMaxContour(contours)  #找出最大轮廓
                if areaMaxContour is not None:
                    if area_max > max_area:#找最大面积
                        max_area = area_max
                        color_area_max = i
                        areaMaxContour_max = areaMaxContour
        if max_area > 200:  # 有找到最大面积
            ((centerX, centerY), radius) = cv2.minEnclosingCircle(areaMaxContour_max)  # 获取最小外接圆
            centerX = int(Misc.map(centerX, 0, size[0], 0, img_w))
            centerY = int(Misc.map(centerY, 0, size[1], 0, img_h))
            radius = int(Misc.map(radius, 0, size[0], 0, img_w))            
            cv2.circle(img, (centerX, centerY), radius, range_rgb[color_area_max], 2)#画圆

            if color_area_max == 'red':  #红色最大
                color = 1
            elif color_area_max == 'green':  #绿色最大
                color = 2
            elif color_area_max == 'blue':  #蓝色最大
                color = 3
            else:
                color = 0
            color_list.append(color)

            if len(color_list) == 3:  #多次判断
                # 取平均值
                color = int(round(np.mean(np.array(color_list))))
                color_list = []
                if color == 1:
                    detect_color = 'red'
                    draw_color = range_rgb["red"]
                elif color == 2:
                    detect_color = 'green'
                    draw_color = range_rgb["green"]
                elif color == 3:
                    detect_color = 'blue'
                    draw_color = range_rgb["blue"]
                else:
                    detect_color = 'None'
                    draw_color = range_rgb["black"]               
        else:
            detect_color = 'None'
            draw_color = range_rgb["black"]
            
    cv2.putText(img, "Color: " + detect_color, (10, img.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.65, draw_color, 2)
    
    return img

if __name__ == '__main__':
    debug = False
    if debug:
        print('Debug Mode')
        
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
