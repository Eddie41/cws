#-*- coding:utf-8 -*-

import time
import sys
import traceback
import json
from Crypto.Cipher import AES
import base64

KEY = "starwarsstarwars"
IV  = "aaaaaaaaaaaaaaaa"

class Result:
    def __init__(self):
        self.code = 200
        self.msg = ""
        self.buf = {}

    def set(self, key, value=None):

        if None == value:
            value = key
            if type(value) == int:
                if value >= 200 and value < 600:
                    self.code = value
                else:
                    if value <= 0:
                        self.code = 500

            elif type(value) == str:
                self.msg = value
            else:
                return False
            return True

        else:
            self.buf[key] = str(value)

    def dumps(self, encrypt=False):
        if self.code >= 300:
            return str(self.code) + ": " + self.msg
    
        self.buf["msg"]  = self.msg
        ret = json.dumps(self.buf)
        
        if not encrypt:
            return str(self.code) + ": " + ret
        
        # 1. 原始数据加工，补足16*n的字节个数
        i   = len(ret)%16
        if i > 0:
            ret = ret + ' '*(16 - i)

        # 2. AES加密，采用CBC模式
        cipher = AES.new(KEY, AES.MODE_CBC, IV)
        ret = cipher.encrypt(ret)

        # 3. base64加密
        ret = base64.encodestring(ret)
        ret = ret.replace( '\n', '' )

        return str(self.code) + ": " + ret

    def error(self, msg="system error"):
        self.code = 500
        self.msg  = msg
        return self.dumps()


        
