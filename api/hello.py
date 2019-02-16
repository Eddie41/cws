#-*- coding:utf-8 -*-
import time

def hello(args):

    return "Hello world! The time is %s"%time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))
    
    ret = "Hello world! The time is %s\n"%time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))
    
    return ret*1000

