#!/usr/bin/env python

import FreeSimpleGUI as sg

class Graph (sg.Graph):
    def __init__ (self, comm_right_click_menu = None, fig_right_click_menu = None, *args, **kwargs):
        super().__init__ (*args, **kwargs, right_click_menu = comm_right_click_menu)
        self.fig_right_click_menu  = fig_right_click_menu
        self.comm_right_click_menu = comm_right_click_menu
        self.selected_fig = None

    def _RightClickMenuCallback (self, event):
        #graph = self.Widget
        fig   = self.get_figures_at_location ((event.x, event.y))
        if len(fig) == 0:
            self.set_right_click_menu (self.comm_right_click_menu)
        else:
            self.set_right_click_menu (self.fig_right_click_menu)
            self.selected_fig = fig

        super()._RightClickMenuCallback (event)
