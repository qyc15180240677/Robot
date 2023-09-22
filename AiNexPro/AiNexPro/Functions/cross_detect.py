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
from hiwonder import yaml_handle
import hiwonder.ActionGroupControl as AGC
from skimage import morphology

# 十字路口识别
servo1 = 320
servo2 = 500

__isRunning = False
__target_color = ()

go_forward = 'go_forward_normal'
go_turn_right = 'go_turn_right_20'
go_turn_left = 'go_turn_left_20'

if sys.version_info.major == 2:
    print('Please run this program with python3!')
    sys.exit(0)

def buzzer_di(di_time):
    Board.setBuzzer(0)
    Board.setBuzzer(1)
    time.sleep(di_time)
    Board.setBuzzer(0)

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
            if contour_area_temp >= 5:  # 只有在面积大于300时，最大面积的轮廓才是有效的，以过滤干扰
                area_max_contour = c

    return area_max_contour, contour_area_max  # 返回最大的轮廓

lab_data = None
servo_data = None
def load_config():
    global lab_data, servo_data
    
    lab_data = yaml_handle.get_yaml_data(yaml_handle.lab_file_path)
    servo_data = yaml_handle.get_yaml_data(yaml_handle.servo_file_path)

load_config()

def getROI(box):
    x_min = min(box[0, 0], box[1, 0], box[2, 0], box[3, 0])
    x_max = max(box[0, 0], box[1, 0], box[2, 0], box[3, 0])
    y_min = min(box[0, 1], box[1, 1], box[2, 1], box[3, 1])
    y_max = max(box[0, 1], box[1, 1], box[2, 1], box[3, 1])

    return [x_min, x_max, y_min, y_max]

# 十字口检测
def crossDetect(img):
    img_copy = img.copy()
    img_h, img_w = img.shape[:2]
    frame_resize = cv2.resize(img_copy, size, interpolation=cv2.INTER_NEAREST)
    frame_gb = cv2.GaussianBlur(frame_resize, (3, 3), 3)

    frame_lab = cv2.cvtColor(frame_gb, cv2.COLOR_BGR2LAB)  # 将图像转换到LAB空间
    frame_mask = cv2.inRange(frame_lab,
                             (lab_data[__target_color[0]]['min'][0],
                              lab_data[__target_color[0]]['min'][1],
                              lab_data[__target_color[0]]['min'][2]),
                             (lab_data[__target_color[0]]['max'][0],
                              lab_data[__target_color[0]]['max'][1],
                              lab_data[__target_color[0]]['max'][2]))  #对原图像和掩模进行位运算
    opened = cv2.morphologyEx(frame_mask, cv2.MORPH_OPEN, np.ones((6, 6), np.uint8))  # 开运算
    closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, np.ones((6, 6), np.uint8))  # 闭运算
    cnts = cv2.findContours(closed[0:130,:], cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_TC89_L1)[-2]#找出所有轮廓
    cnt_large, area = getAreaMaxContour(cnts)#找到最大面积的轮廓
    if cnt_large is not None:#如果轮廓不为空
        rect = cv2.minAreaRect(cnt_large)#最小外接矩形
        box = np.int0(cv2.boxPoints(rect))#最小外接矩形的四个顶点
       
        closed[closed==255] = 1
        skeleton0 = morphology.skeletonize(closed[0:130, :])
        skeleton = skeleton0.astype(np.uint8)*255
        roi = getROI(box)
        if roi[0] < 0:
            roi[0] = 0
        if roi[2] < 0:
            roi[2] = 0
        if roi[1] > size[0]:
            roi[1] = size[0]
        if roi[3] > 130:
            roi[3] = 130
        find_up = True
        up_point = None
        up_row = None
        left_min = img_w
        right_max = 0
        left_point = None
        right_point = None
        down_max = 0
        down_point = None
        for col in range(roi[2], roi[3]):
            for row in range(roi[0], roi[1]):
                if skeleton[col][row] == 255:
                    if up_point is None:
                        up_point = [row, col]
                    else:
                        if col == up_point[1] and abs(row - up_point[0]) > 10:
                            find_up = False
                            break
                        else:
                            if col >= down_max:
                                down_max = col
                                down_point = [row, col]
                            if row <= left_min:
                                left_min = row
                                left_point = [row, col]
                            if row >= right_max:
                                right_max = row
                                right_point = [row, col]
            if up_point is not None and not find_up:
                break
        if up_point is not None and down_point is not None and left_point is not None and right_point is not None:
            angle1 = int(math.degrees(math.atan2(up_point[1] - down_point[1], up_point[0] - down_point[0])))
            angle2 = int(math.degrees(math.atan2(left_point[1] - right_point[1], left_point[0] - right_point[0])))
            if angle1 < 0:
                angle1 = 360 + angle1
            if angle2 < 0:
                angle2 = 360 + angle2
            print(abs(angle1 - angle2))
           
            if 50 < abs(angle1 - angle2) < 130:
                cv2.line(frame_resize, tuple(up_point), tuple(down_point), (0, 255, 255), 2)
                cv2.line(frame_resize, tuple(left_point), tuple(right_point), (0, 255, 255), 2)
                Board.setBuzzer(1)
            else:
                Board.setBuzzer(0)
        else:
            Board.setBuzzer(0)
    else:
        Board.setBuzzer(0)

    return frame_resize

line_centerx = -1
img_centerx = 160
def move():
    global line_centerx
    
    while True:
        if __isRunning:
            if line_centerx != -1:
                if abs(line_centerx - img_centerx) <= 50:
                    AGC.runAction(go_forward)
                elif line_centerx - img_centerx > 50:
                    AGC.runAction(go_turn_right)
                elif line_centerx - img_centerx < -50:
                    AGC.runAction(go_turn_left)
            else:
                time.sleep(0.01)
        else:
            time.sleep(0.01)

# 运行子线程
th = threading.Thread(target=move)
th.setDaemon(True)
th.start()

roi = [ # [ROI, weight]
        (20, 40,  0, 320, 0.1), 
        (60, 80,  0, 320, 0.2), 
        (100, 120,  0, 320, 0.7)
       ]

roi_h1 = roi[0][0]
roi_h2 = roi[1][0] - roi[0][0]
roi_h3 = roi[2][0] - roi[1][0]

roi_h_list = [roi_h1, roi_h2, roi_h3]

size = (320, 240)
def run(img):
    global line_centerx
    global __target_color
    
    img_copy = img.copy()
    img_h, img_w = img.shape[:2]
    
    img_draw = crossDetect(img)
    
    if not __isRunning or __target_color == ():
        return img
    
    frame_resize = cv2.resize(img_copy, size, interpolation=cv2.INTER_NEAREST)
    frame_gb = cv2.GaussianBlur(frame_resize, (3, 3), 3)   
            
    centroid_x_sum = 0
    weight_sum = 0
    center_ = []
    n = 0

    #将图像分割成上中下三个部分，这样处理速度会更快，更精确
    for r in roi:
        roi_h = roi_h_list[n]
        n += 1       
        blobs = frame_gb[r[0]:r[1], r[2]:r[3]]
        frame_lab = cv2.cvtColor(blobs, cv2.COLOR_BGR2LAB)  # 将图像转换到LAB空间
        
        area_max = 0
        areaMaxContour = 0
        for i in lab_data:
            if i in __target_color:
                detect_color = i
                frame_mask = cv2.inRange(frame_lab,
                                             (lab_data[detect_color]['min'][0],
                                              lab_data[detect_color]['min'][1],
                                              lab_data[detect_color]['min'][2]),
                                             (lab_data[detect_color]['max'][0],
                                              lab_data[detect_color]['max'][1],
                                              lab_data[detect_color]['max'][2]))  #对原图像和掩模进行位运算                
                opened = cv2.morphologyEx(frame_mask, cv2.MORPH_OPEN, np.ones((6, 6), np.uint8))  # 开运算
                closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, np.ones((6, 6), np.uint8))  # 闭运算
        cnts = cv2.findContours(closed , cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_TC89_L1)[-2]#找出所有轮廓
        cnt_large, area = getAreaMaxContour(cnts)#找到最大面积的轮廓
        if cnt_large is not None:#如果轮廓不为空
            rect = cv2.minAreaRect(cnt_large)#最小外接矩形
            box = np.int0(cv2.boxPoints(rect))#最小外接矩形的四个顶点
            for i in range(4):
                box[i, 1] = box[i, 1] + (n - 1)*roi_h + roi[0][0]
                
            cv2.drawContours(img_draw, [box], -1, (0,0,255), 2)#画出四个点组成的矩形
            
            #获取矩形的对角点
            pt1_x, pt1_y = box[0, 0], box[0, 1]
            pt3_x, pt3_y = box[2, 0], box[2, 1]            
            center_x, center_y = (pt1_x + pt3_x) / 2, (pt1_y + pt3_y) / 2#中心点       
            cv2.circle(img_draw, (int(center_x), int(center_y)), 2, (0,0,255), -1)#画出中心点
            
            center_.append([center_x, center_y])                        
            #按权重不同对上中下三个中心点进行求和
            centroid_x_sum += center_x * r[4]
            weight_sum += r[4]

    if weight_sum is not 0:
        #求最终得到的中心点
        cv2.circle(img_draw, (line_centerx, int(center_y)), 2, (0,255,255), -1)#画出中心点
        line_centerx = int(centroid_x_sum / weight_sum)  
    else:
        line_centerx = -1
    
    return img_draw

if __name__ == '__main__':
    __isRunning = True
    
    Board.setBusServoPulse(19, servo_data['servo1'], 500)
    Board.setBusServoPulse(20, 200, 500)
    AGC.runAction('stand')
    
    __target_color = ('black', )

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
    ccrossed_bridgev2.destroyAllWindows()
