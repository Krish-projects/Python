import logging
import time
from functools import partial
from logging.handlers import RotatingFileHandler

def init():
    print("Init done!")
def mainloop():
    i=0
    while (1):
        print("Test service lc%s"+time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()))
        time.sleep(5)
        log.error("GW|1234","lc log.info %d"% i)
        i=i+1    

class LoggerWrapper(object):
    """ 
    A wrapper class for logger objects with
    calculation of time spent in each step 
    """
    def __init__(self, app_name, filename=None,level=logging.INFO, console=False):
        self.log = logging.getLogger(app_name)
        self.log.setLevel(level)
        # Add handlers
        if console:
            self.log.addHandler(logging.StreamHandler())
        if filename != None:
            # add a rotating handler
            r_handler = RotatingFileHandler(filename, maxBytes=1000000, backupCount=30)            
            self.log.addHandler(r_handler)       #logging.FileHandler(filename)
        # Set formatting
        for handle in self.log.handlers:
            #formatter = logging.Formatter('%(asctime)s [%(timespent)s]:%(levelname)-8s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
            formatter = logging.Formatter('%(asctime)s  [%(mac_str)s]:%(levelname)-8s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
            handle.setFormatter(formatter)
        for name in ('debug','info','warning','error','critical'):
            # Creating convenient wrappers by using functools
            func = partial(self._dolog, name)
            # Set on this class as methods
            setattr(self, name, func)
        # Mark timestamp
        self._markt = time.time()
    def set_level (self, level):        
        self.log.setLevel(level)
        return
    def _calc_time(self):
        """ 
        Calculate time spent so far 
        """
        tnow = time.time()
        tdiff = int(round(tnow - self._markt))
        hr, rem = divmod(tdiff, 3600)
        mins, sec = divmod(rem, 60)
        # Reset mark
        self._markt = tnow
        return '%.2d:%.2d:%.2d' % (hr, mins, sec)
    def formatID(self, string):
        """
        ID format: [MD|XXXX] where MD means Module, XXXX mac address last four hex
        GW---Gateway    RD--Radio       BT--bootloader      IT--IoTHub
        """
        ID='AN'       #Default ID
        if(len(string)==len(ID)):
            ID=string
        elif (len(string)==len('AN')):  #only contains module
            ID=string #+ '|xxxx'
        return ID
    
    def _dolog(self, levelname, msg, *args, **kwargs):
        """ Generic method for logging at different levels 
            ("ID_STR", MSG), if there is no 'ID_STR', print MSG only
        """
        logfunc = getattr(self.log, levelname)
        _msg=''
        ID='GW|xxxx'
        if(args==()):       #no ID part
            _msg=msg
        else:
            try:
                ID= self.formatID(msg)
                _msg=args[0]
            except:
                pass
        args=()
        #return logfunc(msg, *args, extra={'timespent': self._calc_time()})
        return logfunc(_msg, *args, extra={'mac_str': ID})
        
if __name__ == '__main__':
    # Application code
    a="str"
    
    log=LoggerWrapper('myapp', filename='myapp.log',console=True)
    log.info("ID",a)
    b={a:'b'}
    log.info("123455","Starting application...")
    log.info("Initializing objects. %d",100)
    init()
    log.info("IT","Initialization complete.")
    log.info("ID","Loading configuration and data")
    log.info("ID",'Loading complete. Listening for connections')
    mainloop()
