# encoding: utf-8
'''
@author:     Juncheng Chen

@copyright:  1999-2015 Alibaba.com. All rights reserved.

@license:    Apache Software License 2.0

@contact:    juncheng.cjc@outlook.com
'''
import os
from datetime import datetime

from excel import Excel
from info import INFO_CONFIG

import logging
logger = logging.getLogger(__name__)

class Report(object):
    def __init__(self, log_dir, process_names=[]):
        os.chdir(log_dir)
        if process_names is None:
            process_names = []
        self.process_names = process_names
        for device_dir in self.list_device_dirs():
            logger.info('create report for %s' % device_dir)
            core_num = 1
            try:
                with open(os.path.join(device_dir, 'corenum.txt'), 'r') as f:
                    core_num = int(f.read())
            except:
                pass
            file_names = self.filter_file_names(device_dir)
            logger.debug('%s' % file_names)
            if file_names:
                book_name = '%s-%s.xlsx' % (device_dir, datetime.now().strftime('%Y.%m.%d-%H.%M.%S'))
                excel = Excel(book_name)
                for file_name in file_names:
                    name = file_name.split('.')[0]
                    info = INFO_CONFIG.get(name)(device_dir, file_name, process_names, core_num)
                    for sheet in info.get_sheet_list():
                        logger.info('add sheet %s' % sheet[0])
                        excel.add_sheet(*sheet)
                logger.info('wait to save %s' % book_name)
                excel.save()
        
    def list_device_dirs(self):
        return [d for d in os.listdir('.') if os.path.isdir(d)]
    
    def filter_file_names(self, device):
        return [f for f in os.listdir(device) if os.path.isfile(os.path.join(device, f)) and f.split('.')[0] in INFO_CONFIG.keys()]
    
