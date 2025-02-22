#!/usr/bin/env python

import FreeSimpleGUI as sg
from fsg_calendar import Calendar
from tkhtmlview import html_parser

default_theme = 'SystemDefault1'
window = None
cal    = Calendar (key_prefix = "Cal")

def make_main_window (cal):
    menu_def = [['&Notebook', ['&Open', '---', 'E&xit']],
                ['&Edit', ['Copy (&C)', 'Cut (&X)', 'Paste (&V)', '&Undo', '&Redo']],
                ['T&ool', ['Settings']],
                ['&Help', ['&About...']]]

    mene_elem  = sg.Menu (menu_def)
    layout_mid = []
    layout_nested_labels = []

    cal_layout = cal.make_cal_layout ()

    layout_tags = [[sg.Listbox (["all"], expand_x = True, expand_y = True)]]

    middle_frame = sg.Frame ("Notes", key = '-MIDDLE_FRAME-', layout = layout_mid, expand_x = True, expand_y = True)

    main_pane = sg.Pane([sg.Column([[sg.Frame ("Labels", layout_nested_labels, expand_x = True, expand_y = True)],[sg.Frame ("", cal_layout)]]), sg.Column([[middle_frame]]), sg.Column([[sg.Frame ("Tags", layout_tags, expand_x = True, expand_y = True)]])],
                        orientation = 'horizontal', expand_x = True, expand_y = True)

    main_layout =  [[sg.Menu (menu_def)]]
    main_layout += [[sg.Button ('New Note'), sg.Input (key = '-SEARCH-', expand_x = True), sg.Button ('Graph View'), sg.Button ('Refresh')]]
    main_layout += [[main_pane]]

    return sg.Window('MD Note Manager', main_layout, finalize = True, use_default_focus = True, grab_anywhere_using_control = True, resizable = True)

def create_gui (theme = default_theme):
    global cal

    sg.theme(theme)
    font = ("default", 15, 'normal')
    sg.set_options(font=font)
    window = make_main_window (cal)
    cal.init_cal (window)

    return window

def make_theme_window (theme):
    sg.theme (theme)

    layout = [[sg.Text('Theme Browser')],
              [sg.Listbox(values=sg.theme_list(), size=(20, 12), key='-LIST-', enable_events = True, select_mode = "LISTBOX_SELECT_MODE_SINGLE")],
              [sg.Button('OK'), sg.Button('Exit')]]

    return sg.Window('Theme Browser', layout, modal = True, finalize = True)

def handle (setting_cb, open_cb):
    event, values = window.read(10)

    if event == 'Settings':
        setting_cb ()
        return False
    if event == 'Open':
        open_cb ()
        return False
    if event in (sg.WINDOW_CLOSED, 'Exit'):
        return True

    # Call sub-components's handles
    cal.handle (event, values)
    return False
