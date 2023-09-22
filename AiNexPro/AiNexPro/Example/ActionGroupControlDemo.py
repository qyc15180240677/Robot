import time
import threading
import hiwonder.ActionGroupControl as AGC

print('''
**********************************************************
***************功能:幻尔科技动作组控制例程****************
**********************************************************
以下指令均需在LX终端使用，LX终端可通过ctrl+alt+t打开，或点
击上栏的黑色LX终端图标。
----------------------------------------------------------
Usage:
    python3 ActionGroupControlDemo.py
----------------------------------------------------------
Version: --V1.2  2021/08/03
----------------------------------------------------------
Tips:
 * 按下Ctrl+C可关闭此次程序运行，若失败请多次尝试！
----------------------------------------------------------
''')

# 动作组需要保存在路径/home/pi/AiNexPro/AiNexPro/ActionGroups下
AGC.runActionGroup('turn_left', 2)  
# 参数1为动作组的名称，不包含后缀，以字符形式传入
# 参数2为运行次数，当为0时表示无线循环

threading.Thread(target=AGC.runActionGroup, args=('turn_right', 0)).start()  # 运行动作函数是阻塞式的，如果要循环运行一段时间后停止，请用线程来开启
time.sleep(3)
AGC.stopAction()  # 右转3秒后停止
