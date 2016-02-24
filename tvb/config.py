# encoding: utf-8
'''
@author:     Juncheng Chen

@copyright:  1999-2015 Alibaba.com. All rights reserved.

@license:    Apache Software License 2.0

@contact:    juncheng.cjc@outlook.com
'''
import os
from datetime import datetime

import logging
logger = logging.getLogger(__name__)

from tvb.device import Device
from tvb.command import COMMAND_CONFIG, LAST_COMMAND_CONFIG

class Config(object):
    def __init__(self, args):
        self.log_dir = os.path.join(args.log_dir, datetime.now().strftime('%Y.%m.%d-%H.%M.%S'))
        if not os.path.isdir(self.log_dir):
            logger.info('create log dir %s' % self.log_dir)
            os.makedirs(self.log_dir)
        self.devices, self.commands, self.last_commads = [], [], []
        for device in args.devices:
            self.devices.append(Device(device, self.log_dir))
        for device in self.devices:
            for name in args.commands:
                if name in COMMAND_CONFIG:
                    command = COMMAND_CONFIG.get(name).new(device, args)
                    self.commands.append(command)
                    logger.debug('%s add %s %s' % (device.device, command.__class__.__name__, command.command))
                elif name in LAST_COMMAND_CONFIG:
                    command = LAST_COMMAND_CONFIG.get(name).new(device, args)
                    self.last_commads.append(command)
                    logger.debug('%s add %s %s' % (device.device, command.__class__.__name__, command.command))
                    
    