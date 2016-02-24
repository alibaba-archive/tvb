# encoding: utf-8
'''
@author:     Juncheng Chen

@copyright:  1999-2015 Alibaba.com. All rights reserved.

@license:    Apache Software License 2.0

@contact:    juncheng.cjc@outlook.com
'''

import sys
import os
from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
from time import sleep, time
from threading import Timer

from tvb.command import support_commands, default_commands
from tvb.config import Config
from tvb.report import Report

import logging
logger = logging.getLogger(__name__)

__version__ = '1.0.1'
__date__ = '2015-09-10'
__updated__ = '2015-12-10'

DEBUG = False

def get_version():
    return __version__

class CLIError(Exception):
    '''Generic exception to raise and log different fatal errors.'''
    def __init__(self, msg):
        super(CLIError).__init__(type(self))
        self.msg = "E: %s" % msg
        
    def __str__(self):
        return self.msg
    
    def __unicode__(self):
        return self.msg

def main(argv=None): # IGNORE:C0111
    '''Command line options.'''

    if argv is None:
        argv = sys.argv
    else:
        sys.argv.extend(argv)

    program_version_message = __version__
    program_license = '''tvb -- TV Bridge

  Created by Juncheng Chen on %s.
  Copyright 2015 organization_name. All rights reserved.

  Licensed under the Apache License 2.0
  http://www.apache.org/licenses/LICENSE-2.0

  Distributed on an "AS IS" basis without warranties
  or conditions of any kind, either express or implied.

USAGE
''' % (__date__)

    try:
        parser = ArgumentParser(description=program_license, formatter_class=RawDescriptionHelpFormatter)
        parser.add_argument('-d', dest="devices", help=u"device ip address or name", metavar="ip_address", nargs='*')
        parser.add_argument('-c', dest="commands", choices=support_commands, help=u"collection commands, default %(default)s", default=default_commands, nargs='*')
        parser.add_argument('-l', '--log', dest="log_dir", help=u"specify the file path where to store logs", default=os.path.abspath('.'), metavar="log path", nargs='?')
        parser.add_argument('-t', '--time', dest="time", type=float, help=u"execution time, unit(minutes)", default=-1, metavar="minutes", nargs='?')
        parser.add_argument('-i', '--interval', dest="interval", type=int, help=u"time interval of command, unit(seconds), default %(default)s seconds", default=10, metavar="seconds", nargs='?')
        parser.add_argument('-p', '--process', dest="process_names", help=u"specify process names to generate line chart", metavar="process names", nargs='*')
        
        parser.add_argument('-m', '--monkey', dest="monkey", help=u"monkey will only allow the system to visit activities within those packages", metavar="packages", nargs='*')
        parser.add_argument('-b', '--blacklist', dest="blacklist", help=u"monkey will not allow the system to visit activities within those packages", metavar="packages", nargs='+')
        parser.add_argument('-s', '--script', dest="script", help=u"monkey will repeat run according the script", metavar="script_path", nargs='?')
        parser.add_argument('-o', '--throttle', dest="throttle", type=int, help=u"inserts a fixed delay between monkey events, unit(millisecond), default %(default)s millisecond", default=500, metavar="millisecond", nargs='?')
        
        parser.add_argument('--pct-touch', dest="pct-touch", type=int, help=u"adjust percentage of touch events.", metavar="percentage", nargs='?')
        parser.add_argument('--pct-motion', dest="pct-motion", type=int, help=u"adjust percentage of motion events.", metavar="percentage", nargs='?')
        parser.add_argument('--pct-trackball', dest="pct-trackball", type=int, help=u"adjust percentage of trackball events, default 5", metavar="percent", nargs='?')
        parser.add_argument('--pct-nav', dest="pct-nav", type=int, help=u'adjust percentage of "basic" navigation events, default 55', metavar="percent", nargs='?')
        parser.add_argument('--pct-majornav', dest="pct-majornav", type=int, help=u'adjust percentage of "major" navigation events, default 15', metavar="percent", nargs='?')
        parser.add_argument('--pct-syskeys', dest="pct-syskeys", type=int, help=u'adjust percentage of "system" key events, default 15', metavar="percent", nargs='?')
        parser.add_argument('--pct-appswitch', dest="pct-appswitch", type=int, help=u'adjust percentage of activity launches, default 9', metavar="percent", nargs='?')
        parser.add_argument('--pct-anyevent', dest="pct-anyevent", type=int, help=u'adjust percentage of other types of events, default 1', metavar="percent", nargs='?')
        
        parser.add_argument("-r", "--report", dest="report", help=u"regenerate excel report", metavar="report path", nargs='?')
        parser.add_argument("-v", "--verbose", dest="verbose", action="count", default=0, help=u"verbose level")
        parser.add_argument('-V', '--version', action='version', help=u"show version and exit", version=program_version_message)

        # Process arguments
        args = parser.parse_args()
        logging.basicConfig(level=logging.INFO if args.verbose == 0 else logging.DEBUG,
                    format='%(asctime)s %(levelname)-5s %(message)s',
                    datefmt='%y-%m-%d %H:%M:%S')
        logger.debug(args)
        if not args.devices and not args.report:
            raise CLIError("no operation")
        
        if args.report:
            logger.info('report dir %s' % args.report)
            Report(args.report, args.process_names)
            return 0
        
        if args.monkey is not None:
            args.commands.insert(0, 'monkey')
            if not args.process_names:
                args.process_names = args.monkey
                
        if args.blacklist:
            args.commands.insert(0, 'blacklist')
            
        if args.script:
            args.commands.insert(0, 'script')
                
        config = Config(args)
        total_time = args.time * 60 if args.time > 0 else None
        timeout = len(config.commands) * 10
        def watchdog():
            logger.error('watchdog %s seconds timeout' % timeout)
            for command in config.commands:
                command.kill()
        logger.info('start collection')
        try:
            while total_time is None or total_time > 0:
                timer = Timer(timeout, watchdog)
                timer.setDaemon(True)
                timer.start()
                logger.debug('watchdog start')
                before = time()
                for command in config.commands:
                    command.execute()
                if timer.isAlive():
                    timer.cancel()
                    logger.debug('watchdog cancel')
                timer.join()
                if total_time is not None:
                    total_time -= args.interval
                    logger.debug("remain time: %s sec." % total_time)
                delta = time() - before
                if delta < args.interval:
                    sleep(args.interval - delta)
        except KeyboardInterrupt:
            logger.info('KeyboardInterrupt')
        for command in config.commands:
            command.clean()
        if config.last_commads:
            logger.info('please wait a moment')
        for command in config.last_commads:
            command.execute()
        logger.info('collection finish')
        Report(config.log_dir, args.process_names)
        logger.info('finish')
    except KeyboardInterrupt:
        return 0
    except Exception, e:
        if DEBUG:
            raise(e)
        sys.stderr.write(str(e) + "\n")
        sys.stderr.write("  for help use --help")
        return 2
