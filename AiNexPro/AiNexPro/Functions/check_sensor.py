import time
from hiwonder import Board
from icm20948 import ICM20948
# 测试板载传感器是否可以使用
# 该程序已被设置为开机自启
# 自启文件/etc/systemd/system/check_sensor.service

def check_buzzer():
    try:
        Board.setBuzzer(0)
        Board.setBuzzer(1)
        time.sleep(0.1)
        Board.setBuzzer(0)
    except BaseException as e:
        print('buzzer error', e)

def check_imu():
    try:
        imu = ICM20948()
        return True
    except BaseException as e:
        print('imu error', e)
        return False

if __name__ == '__main__':
    if check_imu():
        check_buzzer()
