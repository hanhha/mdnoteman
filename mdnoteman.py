#!/usr/bin/env python

import FreeSimpleGUI as sg
from tkhtmlview import html_parser

def make_main_window (theme = "SystemDefaultForReal"):
    menu_def = [['&Notebook', ['&Open', '---', 'E&xit']],
                ['&Edit', ['Copy (&C)', 'Cut (&X)', 'Paste (&V)', '&Undo', '&Redo']],
                ['T&ool', ['Settings']],
                ['&Help', ['&About...']]]

    layout_mid = []
    layout_nested_labels = []
    layout_tags = [[sg.Listbox (["all"], expand_x = True, expand_y = True)]]

    middle_frame = sg.Frame ("Notes", key = '-MIDDLE_FRAME-', layout = layout_mid, expand_x = True, expand_y = True)

    main_pane = sg.Pane([sg.Column([[sg.Frame ("Labels", layout_nested_labels, expand_x = True, expand_y = True)]]), sg.Column([[middle_frame]]), sg.Column([[sg.Frame ("Tags", layout_tags, expand_x = True, expand_y = True)]])],
                        orientation = 'horizontal', expand_x = True, expand_y = True)

    main_layout = [[sg.Menu (menu_def)],
                   [sg.Button ('New Note'), sg.Input (key = '-SEARCH-', expand_x = True), sg.Button ('Graph View'), sg.Button ('Refresh')],
                   [main_pane]]

    font = ("default", 15, 'normal')
    sg.theme(theme)
    sg.set_options(font=font)

    return sg.Window('MD Note Manager', main_layout, finalize=True, use_default_focus=True, grab_anywhere_using_control = True, resizable = True)

window = make_main_window ()

#def set_html(widget, html, strip=True):
#    prev_state = widget.cget('state')
#    widget.config(state=sg.tk.NORMAL)
#    widget.delete('1.0', sg.tk.END)
#    widget.tag_delete(widget.tag_names)
#    html_parser.w_set_html(widget, html, strip=strip)
#    widget.config(state=prev_state)
#
#html = """
#<td colspan="2" class="infobox-image"><a href="https://en.wikipedia.org/wiki/RoboCop" class="image">
#<img alt="RoboCop (1987) theatrical poster.jpg" src="https://upload.wikimedia.org/wikipedia/en/thumb/1/16/RoboCop_%281987%29_theatrical_poster.jpg/220px-RoboCop_%281987%29_theatrical_poster.jpg" decoding="async" width="250" height="386" class="thumbborder" srcset="//upload.wikimedia.org/wikipedia/en/1/16/RoboCop_%281987%29_theatrical_poster.jpg 1.5x" data-file-width="248" data-file-height="374"></a>
#<div class="infobox-caption" style="text-align:center">Directed by Paul Verhoeven<br>Release date July 17, 1987</div></td>
#"""
#
#
#layout_advertise = [
#    [sg.Multiline(
#        size=(25, 10),
#        border_width=2,
#        text_color='white',
#        background_color='green',
#        disabled=True,
#        no_scrollbar=True,
#        expand_x=True,
#        expand_y=True,
#        key='Advertise')],
#]
#
#keypad = [
#    ["Rad/Deg",          "x!",   "(",  ")", "%", "AC"],
#    ["Inv",       "sin", "ln",   "7", "8", "9", "÷" ],
#    ["Pi",        "cos", "log",  "4",  "5", "6", "x" ],
#    ["e",         "tan", "√",    "1",  "2", "3", "-" ],
#    ["Ans",       "EXP", "POW",  "0",  ".", "=", "+" ],
#]
#
#layout_calculator = [
#    [sg.Button(
#        key,
#        size=(7, 4),
#        expand_x=key=="Rad/Deg",
#        button_color=('white', '#405373') if key in "1234567890" else sg.theme_button_color(),
#     ) for key in line]
#            for line in keypad]
#
#layout = [
#    [sg.Frame("Calculator", layout_calculator, expand_x=True, expand_y=True),
#     sg.Frame("Advertise",  layout_advertise, expand_x=True, expand_y=True)],
#]
#for element in window.key_dict.values():
#    element.block_focus()
#
#advertise = window['Advertise'].Widget
#
#html_parser = html_parser.HTMLTextParser()
#set_html(advertise, html)
#width, height = advertise.winfo_width(), advertise.winfo_height()

def call_settings ():
    global window

    def make_theme_window (theme):
        sg.theme (theme)

        layout = [[sg.Text('Theme Browser')],
                  [sg.Listbox(values=sg.theme_list(), size=(20, 12), key='-LIST-', enable_events = True, default_values = theme)],
                  [sg.Button('OK'), sg.Button('Exit')]]

        return sg.Window('Theme Browser', layout, modal = True)

    old_theme = sg.theme ()
    new_theme = old_theme
    selected  = old_theme

    setting_window = make_theme_window (selected)

    while True:  # Event Loop
        event, values = setting_window.read()
        selected_theme = values['-LIST-'][0]
        if selected_theme != selected:
            setting_window.close ()
            selected = selected_theme
            setting_window = make_theme_window (selected)

        if event in (sg.WIN_CLOSED, 'Exit'):
            sg.theme (old_theme)
            break
        if event == 'OK':
            new_theme = selected_theme
            break

    setting_window.close ()
    if new_theme != old_theme:
        window.close ()
        window = make_main_window (new_theme)

def clean_up ():
    print ('TODO\n')

while True:

    event, values = window.read()
    if event == 'Settings':
        call_settings ()
    if event in (sg.WINDOW_CLOSED, 'Exit'):
        break
    print(event, values)

clean_up ()
window.close()
