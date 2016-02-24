# encoding: utf-8
'''
@author:     Juncheng Chen

@copyright:  1999-2015 Alibaba.com. All rights reserved.

@license:    Apache Software License 2.0

@contact:    juncheng.cjc@outlook.com
'''
import os
from datetime import datetime
import copy

import logging
logger = logging.getLogger(__name__)

class Command(object):
    def __init__(self, name, command=None, clean_command=None):
        self.name = name
        self.command = command
        self.clean_command = clean_command
        self.process = None
        
    def new(self, device, args):
        self.device = device
        self.args = args
        return copy.deepcopy(self)
    
    def kill(self):
        if self.process:
            self.process.kill()
            self.process.wait()
            self.process = None
            logger.debug('kill %s %s' % (self.name, self.command))
    
    def is_done(self):
        if self.process:
            return self.process.poll() is not None
        return True
    
    def execute(self):
        raise Exception('%s not implement execute' % self.__class__)
    
    def clean(self):
        pass
    
class LastCommand(Command):
    def execute(self):
        if self.command:
            logger.debug('execute single command %s' % self.command)
            with open(os.path.join(self.device.log_dir, '%s.txt' % self.name), 'a') as f:
                self.process = self.device.shell(self.command)
                f.write(self.device.get_process_stdout(self.process))
                
class LoopCommand(Command):
    def execute(self):
        if self.command:
            logger.debug('execute loop command %s' % self.command)
            with open(os.path.join(self.device.log_dir, '%s.txt' % self.name), 'a') as f:
                self.process = self.device.shell(self.command)
                f.write(">>%s>>\n%s\n" % (datetime.now().strftime('%m/%d %H:%M:%S'), self.device.get_process_stdout(self.process)))
            
class AnrLoopCommand(LoopCommand):
    def execute(self):
        logger.debug('execute loop command %s' % self.command)
        if not hasattr(self, 'timestamp'):
            self.process = self.device.shell(self.command)
            self.timestamp = self.device.get_process_stdout(self.process)
        self.process = self.device.shell(self.command)
        timestamp = self.device.get_process_stdout(self.process)
        if timestamp != self.timestamp:
            self.timestamp = timestamp
            with open(os.path.join(self.device.log_dir, '%s_%s.txt' % (self.name, datetime.now().strftime('%Y%m%d%H%M%S'))), 'w') as f:
                self.process = self.device.shell('cat /data/anr/traces.txt')
                f.write(self.device.get_process_stdout(self.process))
    
class MemdetailLoopCommand(LoopCommand):
    def new(self, device, args):
        if args.process_names:
            self.command = 'dumpsys meminfo -a %s' % args.process_names[0]
        else:
            self.command = None
        return LoopCommand.new(self, device, args)
    
class ShowMapLoopCommand(LoopCommand):
    def new(self, device, args):
        if args.process_names:
            self.command = "ps | grep %s | awk '{print $2}' | xargs showmap" % args.process_names[0]
        else:
            self.command = None
        return LoopCommand.new(self, device, args)
    
class DumpheapLoopCommand(LoopCommand):
    def new(self, device, args):
        self.delay = 3600 / args.interval
        self.hprof = '/sdcard/dumpheap.hprof'
        self.clean_command = 'rm -f %s' % self.hprof
        if args.process_names:
            self.command = "am dumpheap %s %s" % (args.process_names[0], self.hprof)
        else:
            self.command = None
        self.i = 0
        return LoopCommand.new(self, device, args)
    
    def execute(self):
        if self.command:
            if self.i == (self.delay - 2):
                logger.debug('execute loop command %s' % self.command)
                self.clean()
                self.device.get_process_stdout(self.device.shell(self.command))
            elif self.i == self.delay:
                self.i = 0
                self.device.adb('pull %s %s' % (self.hprof, os.path.join(self.device.log_dir, '%s_%s.hprof' % (self.name, datetime.now().strftime('%Y%m%d_%H%M%S')))))
            self.i += 1
            
    def clean(self):
        if self.clean_command:
            logger.debug('execute loop clean command %s' % self.clean_command)
            self.device.get_process_stdout(self.device.shell(self.clean_command))
            
            
class DurableCommand(Command):
    
    def execute(self):
        if self.command and self.is_done():
            logger.debug('execute durable command %s' % self.command)
            self.clean()
            self.process = self.device.shell(self.command, os.path.join(self.device.log_dir, '%s_%s.txt' % (self.name, datetime.now().strftime('%Y%m%d_%H%M%S'))))
            
    def clean(self):
        if self.clean_command:
            logger.debug('execute durable clean command %s' % self.command)
            self.device.get_process_stdout(self.device.shell(self.clean_command))
            if self.process:
                self.process.wait()

MONKEYBLACKLIST = '/mnt/sdcard/tvb_monkey_blacklist.txt'
MONKEYSCRIPT = '/mnt/sdcard/tvb_monkey_script.txt'
MONKEYSCRIPTTITLE = ['type = tvb_user', 'count = 1', 'speed = 1.0', 'start data >>']
MONKEYCMD = 'monkey -v -v -v --ignore-crashes --ignore-timeouts --ignore-security-exceptions --kill-process-after-error --monitor-native-crashes'
MONKEYCOUNT = 1200000000

MONKEYPCT = {'pct-touch': 0, 'pct-motion': 0, 'pct-trackball': 5, 'pct-nav': 55, 'pct-majornav': 15, 'pct-syskeys': 15, 'pct-appswitch': 9, 'pct-anyevent': 1}

class MonkeyDurableCommand(DurableCommand):
    def new(self, device, args):
        self.clean_command = 'busybox killall com.android.commands.monkey'
        return DurableCommand.new(self, device, args)
    
    def get_monkey_percent(self, args):
        percent = []
        for pct in MONKEYPCT:
            if hasattr(args, pct):
                value = getattr(args, pct)
                if value:
                    percent.append('--%s %s' % (pct, value))
        if percent:
            return ' '.join(percent)
        return ' '.join(['--%s %s' % (k, v) for k, v in MONKEYPCT.iteritems() if v])

class AppMonkeyDurableCommand(MonkeyDurableCommand):
    def new(self, device, args):
        extra = ''
        if args.monkey:
            extra = '-p ' + ' -p '.join(args.monkey)
        self.command = '%s %s %s --throttle %s %s' % (MONKEYCMD, self.get_monkey_percent(args), extra, args.throttle, MONKEYCOUNT)
        return MonkeyDurableCommand.new(self, device, args)
    
class BlacklistMonkeyDurableCommand(MonkeyDurableCommand):
    def new(self, device, args):
        if args.blacklist:
            cmd = "echo '%s' > %s" % ('\\n'.join(args.blacklist), MONKEYBLACKLIST)
            device.shell(cmd)
            extra = '--pkg-blacklist-file %s' % MONKEYBLACKLIST
            self.command = '%s %s %s --throttle %s %s' % (MONKEYCMD, self.get_monkey_percent(args), extra, args.throttle, MONKEYCOUNT)
        else:
            self.command = None
        return MonkeyDurableCommand.new(self, device, args)
    
class ScriptMonkeyDurableCommand(MonkeyDurableCommand):
    def new(self, device, args):
        if args.script:
            with open(args.script, 'r') as f:
                cmd = "echo '%s' > %s" % ('\\n'.join(MONKEYSCRIPTTITLE + f.read().splitlines()), MONKEYSCRIPT)
                device.shell(cmd)
                extra = '-f %s ' % MONKEYSCRIPT
                self.command = '%s %s --throttle %s %s' % (MONKEYCMD, extra, args.throttle, MONKEYCOUNT)
        else:
            self.command = None
        return MonkeyDurableCommand.new(self, device, args)
            
COMMAND_CONFIG = {
    'top': LoopCommand('top', 'top -n 1'),
    'meminfo': LoopCommand('meminfo', 'dumpsys meminfo'),
    'cpuinfo': LoopCommand('cpuinfo', 'dumpsys cpuinfo'),
    'mali': LoopCommand('mali', 'librank -P /dev/mali'),
    'activity': LoopCommand('activity', 'dumpsys activity'),
    'oom': LoopCommand('activity_oom', 'dumpsys activity oom'),
    'processes': LoopCommand('activity_processes', 'dumpsys activity processes'),
    'procstats': LoopCommand('activity_procstats', 'dumpsys activity procstats'),
    'temp0': LoopCommand('temperature_zone0', 'cat /sys/class/thermal/thermal_zone0/temp'),
    'temp1': LoopCommand('temperature_zone1', 'cat /sys/class/thermal/thermal_zone1/temp'),
    'anr': AnrLoopCommand('anr', 'ls -l /data/anr/traces.txt'),
    'memdetail': MemdetailLoopCommand('memdetail'),
    'showmap': ShowMapLoopCommand('showmap'),
    'dumpheap': DumpheapLoopCommand('dumpheap'),
    
    'logcat': DurableCommand('logcat', 'logcat -v threadtime', 'busybox killall logcat'),
    'event': DurableCommand('logcat_event', 'logcat -v threadtime -b events'),
    
    'monkey': AppMonkeyDurableCommand('monkey'),
    'blacklist': BlacklistMonkeyDurableCommand('monkey'),
    'script': ScriptMonkeyDurableCommand('monkey'),
}

LAST_COMMAND_CONFIG = {
    'bugreport': LastCommand('bugreport', 'bugreport'),
    'usagestats': LastCommand('usagestats', 'dumpsys usagestats')
}

excluded = ['monkey', 'blacklist', 'script']
support_commands = sorted([key for key in COMMAND_CONFIG.keys() if key not in excluded] + LAST_COMMAND_CONFIG.keys())
default_commands = sorted(['top', 'cpuinfo', 'meminfo', 'logcat', 'anr', 'bugreport'])
