#!/usr/bin/env python

import sys
if sys.hexversion < 0x03070000:
    print("!!! This component requires Python version 3.7 at least !!!")
    sys.exit(1)

import FreeSimpleGUI as sg
import datetime
import calendar
import itertools
from dataclasses import dataclass, field
from typing import List

@dataclass
class Calendar:
    """
    :param start_mon: The starting month
    :type start_mon: int
    :param start_day: The starting day - optional. Set to None or 0 if no date to be chosen at start
    :type start_day: int or None
    :param start_year: The starting year
    :type start_year: int
    :param begin_at_sunday_plus: Determines the left-most day in the display. 0=sunday, 1=monday, etc
    :type begin_at_sunday_plus: int
    :param locale: locale used to get the day names
    :type locale: str
    :param month_names: optional list of month names to use (must have 12 items)
    :type month_names: List[str]
    :param day_abbreviations: optional list of abbreviations to display as the day of week (must have 7 items)
    :type day_abbreviations: List[str]
    """
    start_mon  : int = None
    start_day  : int = None
    start_year : int = None
    begin_at_sunday_plus : int = 0
    locale : str = None
    key_prefix : str = "cal"
    month_names : List[str] = field (default_factory=lambda: [calendar.month_name[i] for i in range(1,13)])
    day_abbreviations : List[str] = None
    day_font      : str = 'TkFixedFont 11'
    mon_year_font : str = 'TkFixedFont 12'
    arrow_font    : str = 'TkFixedFont 9'

    @property
    def current_date (self):
        now = datetime.datetime.now()
        return now.month, now.day, now.year

    prev_choice        = None
    chosen_date        = None
    looking_month_year = None

    def make_days_layout(self):
        days_layout = []
        for week in range(6):
            row = []
            for day in range(7):
                row.append(sg.T('', size=(4, 1), justification='c', font=self.day_font, key=(self.key_prefix, week, day), enable_events=True, pad=(0, 0)))
            days_layout.append(row)
        return days_layout

    def make_cal_layout (self):
        cur_month, cur_day, cur_year = self.current_date

        # Create table of month names and week day abbreviations
        if self.day_abbreviations is None or len(self.day_abbreviations) != 7:
            fwday = calendar.SUNDAY
            try:
                if self.locale is not None:
                    _cal = calendar.LocaleTextCalendar(fwday, self.locale)
                else:
                    _cal = calendar.TextCalendar(fwday)
                    day_names = _cal.formatweekheader(3).split()
            except Exception as e:
                print('Exception building day names from locale', self.locale,  e)
                day_names = ('Sun', 'Mon', 'Tue', 'Wed', 'Th', 'Fri', 'Sat')
        else:
            day_names = self.day_abbreviations

        days_layout = self.make_days_layout()

        layout = [[sg.B('◀◀', font=self.arrow_font, border_width=0, key=f"{self.key_prefix}-YEAR-DOWN-", pad=(2,2)),
                   sg.B('◀', font=self.arrow_font, border_width=0, key=f"{self.key_prefix}-MON-DOWN-", pad=(0,2)),
                   sg.Text('{} {}'.format(self.month_names[cur_month - 1], cur_year), size=(16, 1), justification='c', font=self.mon_year_font, key=f'{self.key_prefix}-MON-YEAR-', pad=(0,2)),
                   sg.B('▶', font=self.arrow_font,border_width=0, key=f"{self.key_prefix}-MON-UP-", pad=(0,2)),
                   sg.B('▶▶', font=self.arrow_font,border_width=0, key=f"{self.key_prefix}-YEAR-UP-", pad=(2,2))]]
        layout += [[sg.Col([[sg.T(day_names[i - (7 - self.begin_at_sunday_plus) % 7], size=(4,1), font=self.day_font, background_color=sg.theme_text_color(), text_color=sg.theme_background_color(), pad=(0,0)) for i in range(7)]], background_color=sg.theme_text_color(), pad=(0,0))]]
        layout += days_layout
        layout += [[sg.Push(), sg.B(f'Today: {cur_month}/{cur_day}/{cur_year}', font=self.mon_year_font, key=f'{self.key_prefix}-TODAY-', pad=(0,2)), sg.Push()]]

        return layout

    def update_days(self, month, year):
        [self.window[(self.key_prefix, week, day)].update('') for day in range(7) for week in range(6)]
        weeks = calendar.monthcalendar(year, month)
        month_days = list(itertools.chain.from_iterable([[0 for _ in range(8 - self.begin_at_sunday_plus)]] + weeks))
        if month_days[6] == 0:
            month_days = month_days[7:]
            if month_days[6] == 0:
                month_days = month_days[7:]
        for i, day in enumerate(month_days):
            offset = i
            if offset >= 6 * 7:
                break
            self.window[(self.key_prefix, offset // 7, offset % 7)].update(str(day) if day else '')

    def set_date (self, set_mon = None, set_day = None, set_year = None, within_month_week_day =  None):
        if within_month_week_day:
            if self.prev_choice:
                self.window[(self.key_prefix,) + self.prev_choice].update(background_color=sg.theme_background_color(), text_color=sg.theme_text_color())
            self.window[(self.key_prefix,) + within_month_week_day].update(background_color=sg.theme_text_color(), text_color=sg.theme_background_color())
            self.prev_choice = within_month_week_day

            if set_day:
                self.chosen_date = self.looking_month_year [0], set_day, self.looking_month_year [1]
        else:
            if set_mon and set_day and set_year:
                self.chosen_date = set_mon, set_day, set_year

            if self.chosen_date:
                sel_month, sel_day, sel_year = self.chosen_date
            else:
                sel_month, sel_day, sel_year = self.current_date

            if self.looking_month_year:
                draw_month = set_mon or self.looking_month_year [0]
                draw_year  = set_year or self.looking_month_year [1]
            else:
                draw_month = set_mon or sel_month
                draw_year  = set_year or sel_year
            self.looking_month_year = draw_month, draw_year

            self.window[f'{self.key_prefix}-MON-YEAR-'].update('{} {}'.format(self.month_names[draw_month - 1], draw_year))
            self.update_days(draw_month, draw_year)
            if self.prev_choice:
                self.window[(self.key_prefix,) + self.prev_choice].update(background_color=sg.theme_background_color(), text_color=sg.theme_text_color())
            for week in range(6):
                for day in range(7):
                    if (sel_month == draw_month) and (sel_year == draw_year) and self.window[(self.key_prefix, week,day)].DisplayText == str(sel_day):
                        self.window[(self.key_prefix, week,day)].update(background_color=sg.theme_text_color(), text_color=sg.theme_background_color())
                        self.prev_choice = (week,day)


    def init_cal (self, window):
        self.window = window
        self.set_date ()

    def handle (self, event, values):
        ''' Call in Event Loop '''
        if event in (f'{self.key_prefix}-MON-UP-', f'{self.key_prefix}-MON-DOWN-', f'{self.key_prefix}-YEAR-UP-', f'{self.key_prefix}-YEAR-DOWN-', f'{self.key_prefix}-TODAY-'):
            if event == f'{self.key_prefix}-TODAY-':
                cur_month, cur_day, cur_year = self.current_date
            else:
                cur_month, cur_year = self.looking_month_year
                cur_day = None

            cur_month += (event == f'{self.key_prefix}-MON-UP-')
            cur_month -= (event == f'{self.key_prefix}-MON-DOWN-')
            cur_year  += (event == f'{self.key_prefix}-YEAR-UP-')
            cur_year  -= (event == f'{self.key_prefix}-YEAR-DOWN-')
            if cur_month > 12:
                cur_month = 1
                cur_year += 1
            elif cur_month < 1:
                cur_month = 12
                cur_year -= 1

            self.set_date (set_mon = cur_month, set_year = cur_year, set_day = cur_day)
        elif type(event) is tuple:
            if event [0] == self.key_prefix:
                if self.window[event].DisplayText != "":
                    self.set_date (set_day = int(self.window[event].DisplayText), within_month_week_day = (event[1], event[2]))

if __name__ == '__main__':
    # Create the Calendar object and its layout
    cal = Calendar ()
    cal_layout = cal.make_cal_layout()

    left_layout = [
        [sg.Text("Full name", size=(14, 1))],
        [sg.Input(size=(25, 1), key="name")],
        [sg.Text()],
        [sg.Text("Selected date", size=(14, 1))],
        [sg.Text("", size=(25, 1), key="date")],
    ]

    layout = [
        [sg.Text("This is an example app using a Calendar class!")],
        [sg.Frame("", left_layout), sg.Frame("", cal_layout)],
    ]

    window = sg.Window("Example app with calendar", layout, finalize=True)

    # Initialize Calendar now that the window is made
    cal.init_cal(window)

    while True:  # Event Loop
        event, values = window.read()
        if event in (None,):  break
        else: # Handel other events - including calendar ones!
            cal.handle(event, values)
            window["date"](cal.chosen_date)

    window.close()
