#!/usr/bin/env python3
# encoding: utf-8
import os
import time
from . import Board
import sqlite3 as sql

#上位机编辑的动作调用库
running = True
runningAction = False
stop_action = False
stop_action_group = False

def stopAction():
    global running 
    global stop_action
    global stop_action_group
    
    stop_action = True
    running = False
    stop_action_group = True

__end = False
__start = True
def runActionGroup(actName, times=1, with_stand=False): 
    global __end
    global __start
    global stop_action_group
    
    temp = times
    while True:
        if temp != 0:
            times -= 1
        try:
            if actName != 'go_forward' or stop_action_group:
                if __end:       
                    runAction('go_forward_end')
                __end = False
                __start = True                     
                if stop_action_group or times < 0:
                    stop_action_group = False                        
                    break                
                runAction(actName)
            else:
                if times < 0:
                    if with_stand:
                        runAction('go_forward_end')
                    break
                if __start:
                    __start = False
                    __end = True
                    if actName == 'go_forward':                       
                        runAction('go_forward_start')
                        runAction('go_forward')
                        if with_stand:
                            runAction('go_forward_end')
                else:
                    runAction(actName)
        except BaseException as e:
            print(e)

def runAction(actNum, times=1, path="/home/pi/AiNexPro/AiNexPro/ActionGroups/"):
    '''
    运行动作组
    :param actNum: 动作组名字 ， 字符串类型
    :param times: 运行次数，当为0时表示循环
    :return:
    '''
    global running
    global stop_action
    global runningAction    
    
    if actNum is None:
        return
    
    last_act = None
    running = True
    actNum = path + actNum + ".d6a"
    if os.path.exists(actNum) is True:
        running_times = times
        while running:
            if times > 0:
                running_times -= 1
                if running_times <= 0:
                    running = False
            if runningAction is False:
                runningAction = True
                ag = sql.connect(actNum)
                cu = ag.cursor()
                cu.execute("select * from ActionGroup")
                while True:
                    act = cu.fetchone()
                    if stop_action is True:
                        stop_action = False
                        break
                    if act is not None:
                        data = [act[1]]
                        for i in range(0, len(act) - 2, 1):
                            data.extend([i + 1, act[2 + i]])
                        Board.setBusServosPulse(data)
                        time.sleep(float(act[1])/1000.0)
                    else:   # 运行完才退出
                        break
                runningAction = False
                
                cu.close()
                ag.close()
    else:
        runningAction = False
        print("未能找到动作组文件:" + actNum)
    
if __name__ == '__main__':
    runAction('go_forward')
