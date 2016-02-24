# encoding: utf-8
'''
@author:     Juncheng Chen

@copyright:  1999-2015 Alibaba.com. All rights reserved.

@license:    Apache Software License 2.0

@contact:    juncheng.cjc@outlook.com
'''
import os
import re

import logging
logger = logging.getLogger(__name__)

class Data(object):
    def __init__(self, timestamp):
        self.timestamp = timestamp
        self.lines = []
        self.data = None
        
    def add_line(self, line):
        self.lines.append(line)
        
    def get_data(self):
        if not self.data:
            self.data = ''.join(self.lines)
        return self.data
        
class Info(object):
    def __init__(self, device_dir, file_name, process_names=[], core_num=1):
        self.core_num = str(core_num)
        self.plugins = self._get_plugins(process_names)
        with open(os.path.join(device_dir, file_name), 'r') as f:
            data = None
            for line in f:
                if line.startswith('>>'):
                    if data:
                        for plugin in self.plugins:
                            plugin.parse(data)
                    data = Data(line.split('>>')[1])
                elif data:
                    data.add_line(line)
                    
    def _get_plugins(self, process_names):
        plugins = self.get_plugins()
        for process_name in process_names:
            plugins += self.get_plugins_with_process_name(process_name)
        return plugins
                    
    def get_plugins(self):
        return []
    
    def get_plugins_with_process_name(self, process_name):
        return []
    
    def get_sheet_list(self):
        return (plugin.get_sheet() for plugin in self.plugins)
    
class CpuInfo(Info):
    def get_plugins(self):
        return [RegexPlugin('cpuinfo.load', 'load (%s)' % self.core_num, ['lavg_1', 'lavg_5', 'lavg_15'],
                            r'Load: (?P<lavg_1>.*) / (?P<lavg_5>.*) / (?P<lavg_15>.*)'),
                CpuTotalPlugin()]
    
    def get_plugins_with_process_name(self, process_name):
        short_name = process_name.split('.')[-1]
        return [RegexPlugin('cpuinfo.usage.%s' % short_name, 'usage (100%)', ['usage', 'user', 'kernel'],
                            r'(?P<usage>\d.*)%% \d*/%s: (?P<user>.*)%% user \+ (?P<kernel>.*)%% kernel.*' % process_name, operation='float("%s") / ' + self.core_num),
#                 RegexPlugin('cpuinfo.pid.%s' % short_name, 'pid', ['pid'],
#                             r'\d.*%% (?P<pid>\d.*)/%s: .*' % process_name)
                ]
        
class MemInfo(Info):
    def get_plugins(self):
        return [RegexPlugin('meminfo.uptime', 'uptime (second)', ['uptime'],
                            r'Uptime: (?P<uptime>.*) Realtime: .*', operation='%s / 6000.0'),
                RegexPlugin('meminfo.total', 'meminfo (MB)', ['Total', 'Free', 'Used', 'Lost'],
                            r'Total (RAM|PSS): (?P<Total>\d.*?) kB.* Free (RAM|PSS): (?P<Free>\d.*?) kB.* Used (RAM|PSS): (?P<Used>\d.*?) kB.* Lost (RAM|PSS): (?P<Lost>\d.*?) kB.*',
                            re.DOTALL, operation='%s / 1024.0'),]
    
    def get_plugins_with_process_name(self, process_name):
        short_name = process_name.split('.')[-1]
        return [RegexPlugin('meminfo.pss.%s' % short_name, 'pss (MB)', ['pss'],
                            r'(?P<pss>\d.*?) kB: %s.*' % process_name, operation='%s / 1024.0'),
#                 RegexPlugin('meminfo.pid.%s' % short_name, 'pid', ['pid'],
#                             r'kB: %s \(pid (?P<pid>\d.*?) .*' % process_name)
                            ]
        
class TopInfo(Info):
    def get_plugins(self):
        return [RegexPlugin('top.cpu', 'cpu (100%)', ['User', 'System', 'IOW', 'IRQ'],
                            r'User (?P<User>\d.*?)%, System (?P<System>\d.*?)%, IOW (?P<IOW>\d.*?)%, IRQ (?P<IRQ>\d.*?)%'),
                ]
    
    def get_plugins_with_process_name(self, process_name):
        short_name = process_name.split('.')[-1]
        return [RegexPlugin('top.cpu.%s' % short_name, 'cpu (100%)', ['cpu'], r'.* (?P<cpu>\d.*?)%% .* %s' % process_name),
                RegexPlugin('top.pid.%s' % short_name, 'pid', ['pid'], r'(?P<pid>\d.*?) .* %s' % process_name),
                RegexPlugin('top.thr.%s' % short_name, 'thr', ['thr'], r'.* \d*%%\s\D\s*(?P<thr>\d*) .* %s' % process_name)]
        
class Temp0Info(Info):
    def get_plugins(self):
        return [RegexPlugin('temperature0', u'temperature (℃)', ['temperature'], r'(?P<temperature>\d*)')]
    
class Temp1Info(Info):
    def get_plugins(self):
        return [RegexPlugin('temperature1', u'temperature (℃)', ['temperature'], r'(?P<temperature>\d*)')]
    
class Plugin(object):
    def __init__(self, name, y_axis, headings, operation='float("%s")'):
        self.name = name
        self.y_axis = y_axis
        self.headings = headings
        self.operation = operation
        self.rows = []
        
    def parse_row(self, data, rowd):
        row = [data.timestamp]
        if rowd:
            for key in self.headings:
                try:
                    row.append(eval(self.operation % rowd.get(key)))
                except:
                    row.append('')
        else:
            for unused in self.headings:
                row.append('')
        self.rows.append(row)
        
    def parse_rowd(self, data):
        pass
    
    def parse(self, data):
        self.parse_row(data, self.parse_rowd(data))
    
    def get_sheet(self):
        return self.name, 'time (m/d H:M:S)', self.y_axis, ['timestamp'] + self.headings, self.rows

class RegexPlugin(Plugin):
    def __init__(self, name, y_axis_unit, headings, pattern, flags=None, operation='float("%s")'):
        Plugin.__init__(self, name, y_axis_unit, headings, operation)
        self.flags = flags
        self.pattern = pattern
        
    def parse_rowd(self, data):
        if self.flags:
            p = re.compile(self.pattern, self.flags)
        else:
            p = re.compile(self.pattern)
        m = p.search(data.get_data())
        if m:
            return m.groupdict()
    
class CpuTotalPlugin(Plugin):
    def __init__(self):
        Plugin.__init__(self, 'cpuinfo.total', 'total (100%)', ['TOTAL', 'user', 'kernel', 'iowait', 'softirq'])
        
    def parse_rowd(self, data):
        lines = data.get_data().splitlines()
        if lines:
            rowd = {}
            last_line = lines.pop(-1)
            while 'TOTAL' not in last_line and lines:
                last_line = lines.pop(-1)
            items = last_line.replace(':', '').replace('+', '').replace('%', '').split()
            ilen = len(items)
            for i in range(ilen / 2):
                rowd[items[i * 2 + 1]] = items[i * 2]
            return rowd
    
INFO_CONFIG = {
    'cpuinfo': CpuInfo,
    'meminfo': MemInfo,
    'top': TopInfo,
    'temperature_zone0': Temp0Info,
    'temperature_zone1': Temp1Info
}
        