#!/usr/bin/env python

import sys
if sys.hexversion < 0x03050000:
    print("!!! This component requires Python version 3.5 at least !!!")
    sys.exit(1)

import configparser
from pathlib import Path

import FreeSimpleGUI as sg
import mdnoteman_gui as gui
from mdnoteman_pkm import Notebook as nb
from tkhtmlview import html_parser

cfgpath_str = str(Path.home ()) + "/.mdnote"
cfgfile_str = cfgpath_str + '/config'
cfg = configparser.ConfigParser ()
cfg_file = Path(cfgfile_str)
if cfg_file.exists() and cfg_file.is_file():
    cfg.read (cfgfile_str)
else:
    cfg['Appearance'] = {'Theme': 'SystemDefault1'}
    cfg['Notebook'] = {'Path': ''}

default_theme = cfg ['Appearance']['Theme']

def save_config ():
    global cfgpath_str
    global cfg

    Path(cfgpath_str).mkdir (parents = True, exist_ok = True)
    with open (cfgpath_str + '/config', 'w') as cfgfile:
        cfg.write (cfgfile)

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

def new_notebook (path):
    global Nb

    Nb = nb (path = path)
    Nb.Refresh ()

def call_open ():
    global cfg

    sel_notebook = sg.popup_get_folder (message = 'Select path to notebook',
                                        default_path = cfg['Notebook']['Path'],
                                        initial_folder = str(Path.home()), grab_anywhere = True, keep_on_top = True) \
                   or cfg['Notebook']['Path']
    if sel_notebook != cfg['Notebook']['Path']:
        cfg['Notebook']['Path'] = sel_notebook
    save_config ()
    new_notebook (sel_notebook)

def call_settings (window, cfg):
    old_theme = sg.theme ()
    new_theme = old_theme
    selected  = old_theme

    setting_window = gui.make_theme_window (selected)
    list_of_themes = setting_window['-LIST-'].get_list_values ()
    selected_idx   = list_of_themes.index (selected)
    setting_window['-LIST-'].update (scroll_to_index = selected_idx, set_to_index = selected_idx)

    while True:  # Event Loop
        event, values  = setting_window.read()
        if event == '-LIST-':
            selected_theme = values['-LIST-'][0]
            selected_idx   = setting_window['-LIST-'].get_indexes ()[0]
            if selected_theme != selected:
                setting_window.close ()
                selected = selected_theme
                setting_window = make_theme_window (selected_theme)
                setting_window['-LIST-'].update (scroll_to_index = selected_idx, set_to_index = selected_idx)
            continue

        if event in (sg.WIN_CLOSED, 'Exit'):
            sg.theme (old_theme)
            break
        if event == 'OK':
            new_theme = selected_theme
            break

    setting_window.close ()
    if new_theme != old_theme:
        gui.window.close ()
        gui.window = create_gui (new_theme)
        cfg['Appearance']['Theme'] = new_theme
        save_config ()

def clean_up ():
    save_config ()

if __name__ == "__main__":
    gui.window = gui.create_gui (default_theme)

    while True:
        gui_exit = gui.handle (setting_cb = call_settings, open_cb = call_open)
        if gui_exit:
            break

    clean_up ()
    gui.window.close()
