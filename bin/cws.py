#-*- coding:utf-8 -*-
import os
import sys
import time
import json
import traceback
import urllib
import getopt
import logging
import logging.handlers
import ConfigParser
import multiprocessing.pool
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import types
import imp
from tornado.options import define, options


def initLog(filename, **kwargs):
    """
    给logger添加一个大小切换文件的handler。
    默认大小是100M，30个备份。
    """
    dname = os.path.dirname(filename)
    if dname and not os.path.isdir(dname):
        os.makedirs(dname, 0755)
    conf = {
        'maxBytes': 1024 * 1024 * 100,
        'backupCount': 30,
        'format': '[%(asctime)s][tid:%(thread)d][%(filename)s:%(lineno)d] %(levelname)s: %(message)s',
        'logger': logging.getLogger(),
    }
    conf.update(kwargs)
    if conf.has_key('logLevel'):
        if isinstance(conf['logLevel'], str):
            conf['logLevel'] = getattr(logging, conf['logLevel'])
        conf['logger'].setLevel(conf['logLevel'])

    handler = logging.handlers.RotatingFileHandler(
        filename = filename,
        maxBytes = conf['maxBytes'],
        backupCount = conf['backupCount'],
    )
    handler.setFormatter(
        logging.Formatter(conf['format'])
    )
    conf['logger'].addHandler(handler)


class CommonHandler(tornado.web.RequestHandler):

    def worker_assault(self, cmd, args):
        tBegin = time.time()
        try:
            if cmd not in self.methods.keys():
                ret = "404: Not Found!"
            else:
                ret = self.methods[cmd](args)
        except:
            logging.error( traceback.format_exc() )
            ret = "500: System Error!"

        tEnd = time.time()
        logging.info( "[FINISH] COST:%sms RETURN:%s"%( int( 1000*(tEnd - tBegin) ), ret) )
        return ret


    def worker_callback(self, ret):
        # 为了线程安全，这个地方要返回到主线程来执行 write 和 finish
        tornado.ioloop.IOLoop.instance().add_callback(self.mainthread_callback, ret)

    def mainthread_callback(self, ret):
        try:
            self.write(ret)
        except:
            logging.error( traceback.format_exc() )
            self.write( "500: System Error!" )

        self.finish()

    def initialize(self, workers, methods):
        self.workers = workers
        self.methods = methods

    @tornado.web.asynchronous
    def get(self, cmd):

        try:

            logging.debug( "method : %s"%self.request.method )
            logging.debug( "uri : %s"%self.request.uri )
            logging.debug( "path : %s"%self.request.path )
            logging.debug( "query : %s"%self.request.query )
            logging.debug( "version : %s"%self.request.version )
            logging.debug( "headers : %s"%self.request.headers )
            logging.debug( "body : %s"%self.request.body )
            
            args = {}
            for k, v in self.request.arguments.items():
                args[k] = v[0]
            logging.info( "[INCOME] CMD:%s ARGS:%s"%(cmd, args) )
            args[ "QUERY_STR" ] = self.request.query
            args[ "CMD" ] = cmd

            self.workers.apply_async(self.worker_assault, (cmd, args), {}, self.worker_callback)

        except:
            logging.error( traceback.format_exc() )
            self.write( "500: System Error!" )
            self.finish()


    # 没有GET或者POST方法的时候，考虑这个函数
    def write_error(self, status_code, **kwargs):
        self.write( "401: Request Error!" )

def usage():
    print """\nusage:python %s -c configfile """%(sys.argv[0])
    print """
# config example
[cws]
listen=8787
worker_threads=5
access_log=./cws.log
log_level=DEBUG
root=/home/service/cws
include=demo

[demo]
location=api
include=hello
    """
    sys.exit()

#define("port", default=_DEFAULT_PORT_, help="run on the given port", type=int)
if __name__ == "__main__":

    # 1. 获取配置文件
    options,args = getopt.getopt(sys.argv[1:],"c:",["config="])
    config_file = None
    for k,v in options:
        if k in ("-c", "--config"):
            config_file = v
            # 判断文件是否存在
            if not os.path.isfile(config_file):
                print "file %s not exist"%config_file
                usage()
            break
    if not config_file:
        usage()

    # 2. 解析配置文件
    conf = ConfigParser.ConfigParser()
    conf.read(config_file)
    cws_section = "cws"
    if not conf.has_section(cws_section) or\
        not conf.has_option(cws_section, "include"):
        print "configuration format error"
        usage()

    include_list = conf.get(cws_section, "include")
    include_list = include_list.split() # include列表，业务接口的集合
    if not include_list:
        logging.error( "configuration format error. include empty" )
        print "configuration format error. include empty"
        usage()

    port = 80 # 监听端口
    worker_threads = 2 # 工作线程
    access_log="./cws.log" #日志路径
    log_level="INFO"    # 日志级别
    root_path="." # 根目录

    if conf.has_option(cws_section, "listen"):
        port = conf.getint(cws_section, "listen")
    if conf.has_option(cws_section, "worker_threads"):
        worker_threads = conf.getint(cws_section, "worker_threads")
    if conf.has_option(cws_section, "access_log"):
        access_log = conf.get(cws_section, "access_log")
    if conf.has_option(cws_section, "log_level"):
        log_level = conf.get(cws_section, "log_level")
    if conf.has_option(cws_section, "root"):
        root_path = conf.get(cws_section, "root")


    # 3. 初始化根目录
    os.environ['_BASIC_PATH_'] = root_path
    sys.path.append(os.environ['_BASIC_PATH_'])


    # 4. 初始化日志
    dirname = os.path.dirname(access_log)
    if dirname == "":
        dirname = "."
    if not os.path.isdir(dirname):
        os.makedirs(dirname, 0755)
    initLog(access_log, logLevel=log_level)
    logging.info( "========== GET CONFIG ===========" )
    logging.info( "[listen:%s]"%(port) )
    logging.info( "[worker_threads:%s]"%(worker_threads) )
    logging.info( "[access_log:%s]"%(access_log) )
    logging.info( "[log_level:%s]"%(log_level) )
    logging.info( "[root:%s]"%(root_path) )

    
    # 5. 加载API接口
    section2method = {}
    for section in include_list:
        section2method[ section ] = {}
    
        location = conf.get(section, "location")
        pyfile_list = conf.get(section, "include").split()
        
        # 5.1 location加入搜索路径
        sys.path.append( os.environ['_BASIC_PATH_'] + "/" + location )
        
        # 5.2 尝试执行start函数
        module = location.split("/")
        module = ".".join( module )
        if module not in sys.modules:
            module = __import__( module )
            if hasattr(module, 'start'):
                if type( getattr(module, 'start') ) == types.FunctionType:
                    getattr(module, 'start')()

        # 5.3 读取接口并登记
        for pyfile in pyfile_list:
            module = location.split("/")
            module.append( pyfile )
            module = ".".join(module)
            __import__( module ) # 先import一次 location.pyfile 否则会warning
            
            module = imp.load_source(module.replace('.', '_'),\
                os.environ['_BASIC_PATH_'] + "/" + location + "/" + pyfile + '.py')

            objectList = filter(lambda x:x[0] != '_', dir(module))  # 取模块里面第一个字母不为'_'的成员名列表
            
            for objectName in objectList:
                _object = eval( "module." + objectName )            # 取到具体的成员对象
                if types.FunctionType == type(_object) :            # 如果这个成员类型是函数，则登记
                    section2method[ section ][ objectName ] = _object

        logging.info( "from [%s] FETCH methods : %s"%( section, ", ".join( section2method[ section ].keys() ) ) )

    # 6. 初始化多线程模型
    workers = multiprocessing.pool.ThreadPool(worker_threads)

    
    # 7. 启动tornado服务
    #tornado.options.parse_command_line()
    handlers = []
    for section, methods in section2method.items():
        handlers.append( [r"/%s/(\w+)"%section, CommonHandler, dict(workers=workers, methods=methods)] )

    settings = {
        "compress_response" : True,
    }
        
    app = tornado.web.Application(handlers, **settings)
    http_server = tornado.httpserver.HTTPServer(app)
    http_server.listen(port)
    tornado.ioloop.IOLoop.instance().start()
