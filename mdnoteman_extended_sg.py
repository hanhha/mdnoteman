#!/usr/bin/env python

import FreeSimpleGUI as sg
from FreeSimpleGUI import *
from FreeSimpleGUI._utils import _error_popup_with_traceback

class Window (sg.Window):
    def add_elm (self, s_container, row_idx, *args):
        """
        Adds a single row of elements to a window's self.Rows variables.
        Generally speaking this is NOT how users should be building Window layouts.
        Users, create a single layout (a list of lists) and pass as a parameter to Window object, or call Window.Layout(layout)

        :param row_idx: index of row of interest in self.Rows list
        :type row_idx: int
        :param *args: List[Elements]
        :type *args:
        """
        CurrentRow = []  # start with a blank row and build up
        if not s_container.Rows:
            container = self
        else:
            container = s_container

        if row_idx:
            CurrentRowNumber = row_idx
        else:
            CurrentRowNumber = len (container.Rows)

        # -------------------------  Add the elements to a row  ------------------------- #
        for i, element in enumerate(args):  # Loop through list of elements and add them to the row

            if isinstance(element, tuple) or isinstance(element, list):
                self.add_row(container, *element)
                continue
                _error_popup_with_traceback(
                    'Error creating Window layout',
                    'Layout has a LIST instead of an ELEMENT',
                    'This sometimes means you have a badly placed ]',
                    'The offensive list is:',
                    element,
                    'This list will be stripped from your layout',
                )
                continue
            elif callable(element) and not isinstance(element, Element):
                _error_popup_with_traceback(
                    'Error creating Window layout',
                    'Layout has a FUNCTION instead of an ELEMENT',
                    'This likely means you are missing () from your layout',
                    'The offensive list is:',
                    element,
                    'This item will be stripped from your layout',
                )
                continue
            if element.ParentContainer is not None:
                warnings.warn(
                    '*** YOU ARE ATTEMPTING TO REUSE AN ELEMENT IN YOUR LAYOUT! Once placed in a layout, an element cannot be used in another layout. ***',
                    UserWarning,
                )
                _error_popup_with_traceback(
                    'Error detected in layout - Contains an element that has already been used.',
                    'You have attempted to reuse an element in your layout.',
                    "The layout specified has an element that's already been used.",
                    'You MUST start with a "clean", unused layout every time you create a window',
                    'The offensive Element = ',
                    element,
                    'and has a key = ',
                    element.Key,
                    'This item will be stripped from your layout',
                    'Hint - try printing your layout and matching the IDs "print(layout)"',
                )
                continue
            element.Position = (CurrentRowNumber, i)
            element.ParentContainer = container
            CurrentRow.append(element)
            # if this element is a titlebar, then automatically set the window margins to (0,0) and turn off normal titlebar
            if element.metadata == TITLEBAR_METADATA_MARKER:
                self.Margins = (0, 0)
                self.NoTitleBar = True
        # -------------------------  Append the row to list of Rows  ------------------------- #
        if row_idx:
            container.Rows.extend (CurrentRow)
        else:
            container.Rows.append (CurrentRow)

    def delete_idx (self, container, r, c):
        elm = container.Rows [r][c]
        elm.widget.destroy ()
        elm.widget.master.destroy ()
        elm.widget.master.master.destroy ()


    def new_layout (self, container, rows):
        """
        Adds new elements to an existing container element inside of this window
        If the container is a scrollable Column, you need to also call the contents_changed() method

        :param container: The container Element the layout will be placed inside of
        :type container:  Frame | Column | Tab
        :param rows:      The layout to be added
        :type rows:       (List[List[Element]]) or (List[Element])
        :return:          (Window) self so could be chained
        :rtype:           (Window)
        """

        return self.extend_layout (container, rows)
