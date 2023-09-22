#!/usr/bin/env python3
import cv2
import time
import math
import threading
import numpy as np
from hiwonder import Board
from icm20948 import ICM20948
import hiwonder.ActionGroupControl as AGC

# 跌倒起立

lie_to_stand = 'lie_to_stand'
recline_to_stand = 'recline_to_stand'

AGC.runAction('stand')
imu = ICM20948()

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

def buzzer_di():
    Board.setBuzzer(0)
    Board.setBuzzer(1)
    time.sleep(0.2)
    Board.setBuzzer(0)

action_finish = True
def run_action():
    global action_finish

    while True:
        if not action_finish:
            buzzer_di()
            if count1 > 10:
                AGC.runAction(recline_to_stand)
            elif count2 > 10:
                AGC.runAction(lie_to_stand)
            time.sleep(0.5)
            action_finish = True
        else:
            time.sleep(0.01)

threading.Thread(target=run_action, daemon=True).start()

img = np.zeros((300, 480), np.uint8)
point1 = [240, 230]
point2 = [240, 30]

count1 = 0
count2 = 0
while True:
    ax, ay, az, gx, gy, gz = imu.read_accelerometer_gyro_data()
    angle_y = abs(int(math.degrees(math.atan2(ay, az)))) #转化为角度值
    image = img.copy()
    # 通过图像显示方向
    point = rotate_point(point1, [point2], 90 - angle_y)[0]
    cv2.line(image, tuple(point1), tuple(point), (255, 255, 255), 1, cv2.LINE_AA)
    cv2.putText(image, str(angle_y), (225, image.shape[0] - 20), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    cv2.imshow('image', image)
    key = cv2.waitKey(1)
    if key != -1:
        break     
    if action_finish:
        if angle_y > 160:
            count1 += 1
        else:
            count1 = 0
        if angle_y < 20:
            count2 += 1
        else:
            count2 = 0

        if count1 > 10 or count2 > 10:
            action_finish = False
        time.sleep(0.1)
