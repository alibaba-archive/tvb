# encoding: utf-8
'''
@author:     Juncheng Chen

@copyright:  1999-2015 Alibaba.com. All rights reserved.

@license:    Apache Software License 2.0

@contact:    juncheng.cjc@outlook.com
'''
import os
import subprocess

import logging
from time import sleep
logger = logging.getLogger(__name__)

class Device(object):
    def __init__(self, device, log_dir):
        self.log_dir = os.path.join(log_dir, device)
        if not os.path.isdir(self.log_dir):
            logger.info('create device dir %s' % self.log_dir)
            os.makedirs(self.log_dir)
        self.device = device
        self.address = None
        self.connect()
        with open(os.path.join(self.log_dir, 'corenum.txt'), 'w') as f:
            core_num = self.get_core_number()
            f.write(core_num)
            
    def get_core_number(self):
        core_num = 0
        lines = self.get_process_stdout(self.shell('ls /sys/devices/system/cpu/')).splitlines()
        for line in lines:
            if line.startswith('cpu') and line[-1].isdigit():
                core_num += 1
        if core_num == 0:
            logger.error('get CPU core number failed, set core number to 1')
            core_num = 1
        else:
            logger.info('CPU core number is %s' % core_num)
        return str(core_num)
        
    def execmd(self, cmd):
        return subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE).stdout.read().replace('\r\r', '').strip()
    
    def adb(self, cmd):
        cmd = 'adb -s %s %s' % (self.address, cmd)
        logger.debug(cmd)
        return subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE).stdout.read().replace('\r\r', '').strip()
    
    def shell(self, cmd, redirect=None):
        cmd = 'adb -s %s shell "%s"' % (self.address, cmd)
        logger.debug(cmd)
        if redirect:
            with open(redirect, 'a') as f:
                return subprocess.Popen(cmd, shell=True, stdout=f)
        return subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    
    def get_process_stdout(self, process):
        result = process.communicate()[0].replace('\r\r', '').strip()
        ret = process.wait()
        logger.debug('ret %s' % ret)
        if ret != 0:
            self.reconnect()
        process = None
        return result
        
    def is_connected(self, retry=True):
        results = filter(lambda line: self.device in line, self.execmd('adb devices').splitlines())
        if len(results) == 1:
            result = results[0]
            if 'device' in result:
                logger.info(result)
                return True
            elif retry and 'unauthorized' in result:
                sleep(1)
                return self.is_connected(False)
            logger.error(result)
        return False
        
    def connect(self):
        if '.' not in self.device:
            self.address = self.device
            return
        result = self.execmd('adb connect %s' % self.device)
        logger.info(result)
        if 'connected to' in result:
            self.address = result.split()[-1]
        else:
            raise Exception(result)
        if not self.is_connected():
            raise Exception('disconnect')
        
    def disconnect(self):
        if '.' not in self.device:
            return
        self.execmd('adb disconnect %s' % self.device)
        
    def reconnect(self):
        if '.' not in self.device:
            return
        logger.error('try reconnect')
        self.disconnect()
        logger.info(self.execmd('adb connect %s' % self.device))
