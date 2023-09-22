#!/usr/bin/python3
# coding=utf8
import os
import sys
import cv2
import time
import math
import pandas as pd
import threading
import numpy as np
from icm20948 import ICM20948
import hiwonder.ActionGroupControl as AGC

# 走方形

go_forward = 'go_forward_normal'
turn_left = 'turn_left_30'
turn_right = 'turn_right_30'

# 初始位置
def initMove():
    Board.setBusServoPulse(19, 1500, 500)
    Board.setBusServoPulse(20, 1500, 500) 
    AGC.runAction('stand')

load_path = '/home/pi/AiNexPro/AiNexPro/Example/icm20948_calibration_param.npz'

if not os.path.exists(load_path):
    print('没有检测到imu校正保存的数据，请确保已经进行过imu校正')
    sys.exit()
else:
    print('检测到imu校正保存的数据，请确保是自己亲自进行过校正')

def rotate(ps, m):
    pts = np.float32(ps).reshape([-1, 2])  # 要映射的点
    pts = np.hstack([pts, np.ones([len(pts), 1])]).T
    target_point = np.dot(m, pts).astype(np.int)
    target_point = [[target_point[0][x], target_point[1][x]] for x in range(len(target_point[0]))]
    
    return target_point

def rotate_point(center_point, corners, angle):
    '''
    获取一组点绕一点旋转后的位置
    :param center_point:
    :param corners:
    :param angle:
    :return:
    '''
    # points [[x1, y1], [x2, y2]...]
    # 角度
    M = cv2.getRotationMatrix2D((center_point[0], center_point[1]), angle, 1)
    out_points = rotate(corners, M)

    return out_points

# 加载参数
param_data = np.load(load_path)

# 获取参数
amin = param_data['amin']
amax = param_data['amax']

imu = ICM20948()

X = 0
Y = 1
Z = 2

AXES = X, Z
r = 30
point1 = [120, 60]
point2 = [120 + r, 60]
point3 = [480 - 120, 60]
point4 = [480 - 120 + r, 60]
point = point2 
point_ = point4

target_angle = 0
current_angle = 0
Running = False
action_finish = True
def Move():
    global point_
    global Running
    global target_angle
    global current_angle
    global action_finish

    # 直走步数
    go_count = 8
    count_go = 0
    turn_angle = [120, 188, 260]
    while True:
        if Running and not action_finish:
            print("当前方向: {} 目标方向: {} 当前步数: {} 前进步数: {}".format(current_angle, target_angle, count_go, go_count))
            d_angle = current_angle - target_angle
            if d_angle > 180:
                d_angle = d_angle - 360
            if d_angle < -180:
                d_angle = d_angle + 360
            if 20 < d_angle < 180:
                AGC.runActionGroup(turn_right)
                action_finish = True
            elif -20 > d_angle > -180:
                AGC.runActionGroup(turn_left)
                action_finish = True
            else:
                count_go += 1
                AGC.runActionGroup(go_forward)
                if count_go >= go_count:
                    count_go = 0
                    if turn_angle == []:
                        break
                    target_angle = turn_angle[0]
                    if target_angle > 360:
                        target_angle -= 360
                    turn_angle.remove(turn_angle[0])
                    point_ = rotate_point(point3, [point4], target_angle)[0]
                action_finish = True
        else:
            time.sleep(0.01)
                  
#作为子线程开启
th = threading.Thread(target=Move)
th.setDaemon(True)
th.start()

angle_list = []
img_map = np.zeros((120, 480), np.uint8)

while True:
    # 获取原始数据并转化为角度
    mag = list(imu.read_magnetometer_data())
    for i in range(3):
        mag[i] -= amin[i]
        try:
            mag[i] /= amax[i] - amin[i]
        except ZeroDivisionError:
            pass
        mag[i] -= 0.5

    heading = math.atan2(
            mag[AXES[0]],
            mag[AXES[1]])

    if heading < 0:
        heading += 2 * math.pi
    heading = math.degrees(heading)
    heading = round(heading)

    # 对数据进行均值滤波，提高抗干扰
    if action_finish:
        angle_list.append(heading)    
        if len(angle_list) == 10:
            image_map = img_map.copy()
            Running = True
            if max(angle_list) - min(angle_list) > 250:
                for i in range(len(angle_list)):
                    if angle_list[i] < 250:
                        angle_list[i] = angle_list[i] + 360   
            data = pd.DataFrame(angle_list)
            data_ = data.copy()
            u = data_.mean()  # 计算均值
            std = data_.std()  # 计算标准差

            data_c = data[np.abs(data - u) <= std]
            current_angle = int(round(data_c.mean()[0]))

            #current_angle = int(round(np.mean(angle_list)))       
            if current_angle > 360:
                current_angle -= 360
            # 通过图像显示方向
            point = rotate_point(point1, [point2], current_angle)[0]
            #cv2.putText(image, "Heading: {}".format(current_angle), (10, image.shape[0] - 20), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            cv2.line(image_map, tuple(point1), tuple(point), (255, 255, 255), 1, cv2.LINE_AA)
            cv2.circle(image_map, tuple(point1), 40, (255, 255, 255), 1, cv2.LINE_AA)
            cv2.line(image_map, tuple(point3), tuple(point_), (255, 255, 255), 1, cv2.LINE_AA)
            cv2.circle(image_map, tuple(point3), 40, (255, 255, 255), 1, cv2.LINE_AA)
            #cv2.imshow('image', image)
 
            angle_list = []
            action_finish = False
            cv2.imshow('image_map', image_map)
            key = cv2.waitKey(10)
            if key != -1:
                break  
        '''
        angle_list = data_c.values[:, 0].tolist()
        angle_list = [a_ for a_ in angle_list if a_ == a_]
        print(angle_list)
        if len(angle_list) >= 10:
            angle_list.remove(angle_list[0])
        '''
