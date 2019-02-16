#-*- coding:utf-8 -*-
import time
import logging
import Common
import hashlib
    
_KEY_ = Common.KEY

# 参数合法性检查
def _checkPoint(func):

    
    # 检查CK:check key
    #   规则：query字串 + 口令( starwars )，再md5取后16位
    def _checkKey(args):
        
        if not args.has_key( "QUERY_STR" ):
            logging.error( "缺少入参QUERY_STR" )
            return False
            
        QUERY_STR = args["QUERY_STR"]
        flag = QUERY_STR.rfind( "&ck=" ) # 从后往前查找 &ck= 这个关键字位置
        if flag <= 0:
            logging.error( "缺少入参ck" )
            return False
            
        yourCK = QUERY_STR[flag:]
        yourCK = yourCK.split('=')[1].upper()   # check key
        QUERY_STR_WITHOUT_CK = QUERY_STR[:flag] # 剔除ck之后的query字串
        
        # 开始校验
        myCK = hashlib.md5( QUERY_STR_WITHOUT_CK + _KEY_ ).hexdigest().upper()
        myCK = myCK[-16:]
        
        if yourCK != myCK:
            logging.error( "ck 不匹配 [yourCK:%s][myCK:%s]", yourCK, myCK )
            return False
            
        return True
        
        
    def new_func(*args, **kwargs):

        ret = Common.Result()

        if len(args) <= 0:
            logging.error( "入参为空" )
            return ret.error("empty input")

        if type(args[0]) != dict:
            logging.error( "入参类型不是字典" )
            return ret.error("parameter type error")
        
        # 1. 检查时间戳，过时不候（1分钟过时）
        if not args[0].has_key( "ts" ):
            logging.error( "入参缺少timestamp" )
            return ret.error( "parameter lacks" )
        ts = args[0]["ts"]
        if not ts.isdigit():
            logging.error( "timestamp类型错误[%s]", ts )
            return ret.error( "parameter type error" )
        ts = int( ts )
        tNow = time.time()
        if tNow - ts > 20:
            logging.error( "请求过时" )
            return ret.error( "request out of date" )


        # 2. 检查CK，入参的合法性
        if not _checkKey(args[0]):
            logging.error( "检查CK不通过" )
            return ret.error( "CK ERROR" )


        return func(*args, **kwargs)

    return new_func


def new():
    return _checkPoint
    

