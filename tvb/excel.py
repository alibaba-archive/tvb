# encoding: utf-8
'''
@author:     Juncheng Chen

@copyright:  1999-2015 Alibaba.com. All rights reserved.

@license:    Apache Software License 2.0

@contact:    juncheng.cjc@outlook.com
'''
import xlsxwriter

import logging
logger = logging.getLogger(__name__)

class Excel(object):
    def __init__(self, book_name):
        self.workbook = xlsxwriter.Workbook(book_name)
        
    def add_sheet(self, sheet_name, x_axis, y_axis, headings, lines):
        worksheet = self.workbook.add_worksheet(sheet_name)
        worksheet.write_row('A1', headings)
        for i, line in enumerate(lines, 2):
            worksheet.write_row('A%d' % i, line)
        columns = len(headings)
        rows = len(lines)
        if columns > 1 and rows > 1:
            chart = self.workbook.add_chart({'type': 'line'})
            for j in range(1, columns):
                chart.add_series({'name':       [sheet_name, 0, j],
                                  'categories': [sheet_name, 1, 0, rows, 0],
                                  'values':     [sheet_name, 1, j, rows, j]})
            chart.set_title ({'name': sheet_name.replace('.', ' ').title()})
            chart.set_x_axis({'name': x_axis})
            chart.set_y_axis({'name': y_axis})
            worksheet.insert_chart('B3', chart, {'x_scale': 2, 'y_scale': 2})
    
    def save(self):
        self.workbook.close()
