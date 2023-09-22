#!/usr/bin/python3
# -*- coding: UTF-8 -*-
############9轴传感器测试#############
import os
import sys
import cv2
import math
import time
import numpy as np
from icm20948 import ICM20948
import hiwonder.ActionGroupControl as AGC

if not os.path.exists('icm20948_calibration_param.npz'):
    print('没有检测到imu校正保存的数据，请确保已经进行过imu校正')
    sys.exit()
else:
    print('检测到imu校正保存的数据，请确保是自己亲自进行过校正')

AGC.runAction('1')

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
param_data = np.load('icm20948_calibration_param.npz')

# 获取参数
amin = param_data['amin']
amax = param_data['amax']

imu = ICM20948()

X = 0
Y = 1
Z = 2

AXES = X, Z

img = np.zeros((320, 320), np.uint8)
point1 = [160, 160]
point2 = [250, 160]
while True:
    image = img.copy()
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
    
    point = rotate_point(point1, [point2], heading)[0]
    cv2.putText(image, "Heading: {}".format(heading), (10, image.shape[0] - 20), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    cv2.line(image, tuple(point1), tuple(point), (255, 255, 255), 1, cv2.LINE_AA)
    cv2.imshow('image', image)
    key = cv2.waitKey(1)
    time.sleep(0.04)
    if key != -1:
        break