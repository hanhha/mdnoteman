#!/usr/bin/env python

import re
import markdown
from markdown import util
import requests
from PIL import Image, ImageDraw, ImageFont
from functools import reduce
from pathlib import Path

home = Path.home()

BULLET_DIAMETER = 4
IMAGE_BLOCK_HEIGHT = 1000
font_dir = str(Path.home ()) + "/Library/Fonts/"

class Markdown_Ext (markdown.Markdown):
    """
    Recusively walks the parsed markdown and renders to an image.  Uses chunks
    of IMAGE_BLOCK_HEIGHT to render parts of the markdown incrementally (without
    pre-measuring) and assembles the chunks at the end.
    """

    def init (self):
        # List of (Image, height) to be merged for the result
        self.image = None
        self.image_draw = None
        self.image_x = 0
        self.image_y = 0
        self.indent = 0
        self.links = []

        # Stack of list types and item numbers
        self.list_types = []
        self.list_item_nums = []
        self.y = 0
        self.images = []
        self.line_height = 0
        self.in_pre = False

    def __init__(self, width_spec, config = None, **kwargs):
        super().__init__ (**kwargs)
        self.image_width = max(width_spec, key=lambda x: x[2])[2]

        self.init ()

        self.config = {
            "bold_font_path": font_dir + "FreeSansBold.otf",
            "blockquote_indent": 16,
            "code_indent": 16,
            "code_font_path": font_dir + "FreeMono.otf",
            "code_font_size": 14,
            "color": (255, 255, 255, 255),
            "default_font_path": font_dir + "FreeSans.otf",
            "font_size": 12,
            "hr_color": (220, 220, 220, 255),
            "hr_padding": 0,
            "italics_font_path": font_dir + "FreeSansOblique.otf",
            "link_color": (100, 100, 255, 255),
            "list_indent": 28,
            "list_item_margin_bottom": 4,
            "bullet_outdent": 8,
            "margin_bottom": 16,
        }

        if config:
            self.config.update(config)

        font_size = self.config["font_size"]
        default_font_path = self.config["default_font_path"]
        self.default_font = ImageFont.truetype(default_font_path, font_size)
        self.bold_font = ImageFont.truetype(self.config["bold_font_path"], font_size)
        self.code_font = ImageFont.truetype(self.config["code_font_path"], self.config["code_font_size"])
        self.h1_font = ImageFont.truetype(self.config["default_font_path"], font_size * 2)
        self.h2_font = ImageFont.truetype(self.config["default_font_path"], int(font_size * 1.75))
        self.h3_font = ImageFont.truetype(self.config["default_font_path"], font_size * 1.6)
        self.h4_font = ImageFont.truetype(self.config["default_font_path"], int(font_size * 1.5))
        self.h5_font = ImageFont.truetype(self.config["default_font_path"], int(font_size * 1.25))
        self.h6_font = ImageFont.truetype(self.config["default_font_path"], int(font_size * 1))
        self.italics_font = ImageFont.truetype(self.config["italics_font_path"], font_size)

        self.width_spec = width_spec
        self.width_spec.sort()
        self.width_spec_index = -1
        self.apply_width_spec()

    def apply_width_spec(self, h=0):
        if self.width_spec_index + 1 < len(self.width_spec):
            if self.width_spec[self.width_spec_index + 1][0] <= self.y + h:
                self.width_spec_index += 1
                self.start_x = self.width_spec[self.width_spec_index][1]
                self.end_x = self.start_x + self.width_spec[self.width_spec_index][2]

    def compact_whitespace(self, text):
        return re.sub(r'\s+', ' ', text)

    def ensure_image(self, h, retain = False, draw = True):
        self.apply_width_spec(h)

        if (not retain) and (self.image_y + h > self.image.size[1]):
            if self.image_y == 0:
                print("Image block size too small!  Results will be cropped...")
                return

            self.new_image_block()
        else:
            self.image = self.image.crop ((0, 0, self.image_width, self.image_y + h))
            self.image_draw = ImageDraw.Draw(self.image)

        if draw:
            return self.image_draw
        else:
            return self.image

    def get_links(self):
        return self.links

    def handle_a (self, node):
        text = node.text

        if "href" in node.attrib:
            blocks = self.render_text(node.text, self.config["link_color"], False)
            self.links.append((node.attrib["href"], blocks))
        else:
            self.render_text(node.text, self.config["color"], False)
        self.handle_children(node)
        self.render_text(node.tail, self.config["color"], False)

    def handle_blockquote (self, node):
        indent = self.config["blockquote_indent"]
        self.indent += indent
        self.newline()
        self.handle_children(node)
        self.indent -= indent
        self.newline()

    def handle_code(self, node):
        text = node.text

        self.render_text(node.text, self.config["color"], False, font=self.code_font)
        self.handle_children(node)
        self.render_text(node.tail, self.config["color"], False)

    def handle_children (self, node):
        if len(node) > 0:
            for child in node:
                self.handle_node(child)

    def handle_div (self, node):
        if self.image_x > self.start_x + self.indent:
            self.newline()

        self.handle_children(node)

        if self.image_x > self.start_x + self.indent:
            self.newline()

    def handle_em (self, node):
        text = node.text

        self.render_text(node.text, self.config["color"], False, font=self.italics_font)
        self.handle_children(node)
        self.render_text(node.tail, self.config["color"], False)

    def handle_h (self, node):
        text = node.text

        font = getattr(self, node.tag + "_font")
        self.render_text(node.text, self.config["color"], True, font=font)
        w, h = self.textsize (node.text, font = font)
        self.line_height = max (h, self.line_height)
        self.newline()

    def handle_hr (self, node):
        self.newline()
        h = self.config["margin_bottom"]
        horizontal_padding = self.config["hr_padding"]
        self.image_draw.line((self.start_x + horizontal_padding, self.image_y + h / 2,
                              self.end_x - horizontal_padding, self.image_y + h / 2), fill=self.config["hr_color"])
        self.newline(h)

    def handle_li (self, node):
        list_type = self.list_types[-1]
        if list_type == "unordered":
            # Draw the bullet
            (w, h) = self.textsize("E", font=self.default_font)
            draw = self.ensure_image(h)

            x = self.image_x - BULLET_DIAMETER - self.config["bullet_outdent"]
            y = self.image_y + (h - BULLET_DIAMETER) / 2
            draw.ellipse((x, y,
                          x + BULLET_DIAMETER,
                          y + BULLET_DIAMETER),
                          outline=self.config["color"],
                          fill=self.config["color"])

            self.render_text(node.text, self.config["color"], True)
            self.handle_children(node)
        elif list_type == "ordered":
            # Draw the number
            current_number = "%d" % self.list_item_nums[-1]
            (w, h) = self.textsize(current_number, font=self.default_font)
            draw = self.ensure_image(h)

            x = self.image_x - w - self.config["bullet_outdent"]
            draw.text((x, self.image_y), current_number + ".",
                      font=self.default_font,
                      fill=self.config["color"])

            self.list_item_nums[-1] += 1

            self.render_text(node.text, self.config["color"], True)
            self.handle_children(node)

        # REVIEW: Ignore tail text on li items b/c.  Is this okay?
        # self.render_text(node.tail, self.config["color"], True)
        self.newline(self.config["list_item_margin_bottom"])

    def handle_node (self, node):
        #print ("Handling %s : %s : %s" % (node.tag, node.text, node.tail))
        #print (node.attrib)
        handlers = {
            "a": self.handle_a,
            "code": self.handle_code,
            "blockquote": self.handle_blockquote,
            "em": self.handle_em,
            "div": self.handle_div,
            "h1": self.handle_h,
            "h2": self.handle_h,
            "h3": self.handle_h,
            "h4": self.handle_h,
            "h5": self.handle_h,
            "h6": self.handle_h,
            "hr": self.handle_hr,
            "li": self.handle_li,
            "ol": self.handle_ol,
            "p": self.handle_p,
            "pre": self.handle_pre,
            "strong": self.handle_strong,
            "ul": self.handle_ul,
            "img": self.handle_img,
        }
        handlers.get(node.tag, self.handle_unknown)(node)
        # print "Done with %s" % node.tag

    def handle_ol (self, node):
        indent = self.config["list_indent"]
        self.indent += indent
        self.newline ()

        self.list_types.append("ordered")
        self.list_item_nums.append(1)
        self.handle_children(node)
        self.list_item_nums = self.list_item_nums[:-1]
        self.list_types = self.list_types[:-1]

        self.indent -= indent
        self.newline ()

    def handle_p (self, node):
        self.render_text(node.text, self.config["color"], False)
        self.handle_children(node)

        self.render_text(node.tail, self.config["color"], True)
        self.newline(self.config["margin_bottom"])

    def handle_pre (self, node):
        old_in_pre = self.in_pre
        self.in_pre = True

        indent = self.config["code_indent"]
        self.indent += indent
        self.newline ()

        self.handle_children(node)

        self.indent -= indent
        self.newline ()

        self.in_pre = old_in_pre

    def handle_strong (self, node):
        text = node.text

        self.render_text(node.text, self.config["color"], False, font=self.bold_font)
        self.handle_children(node)
        self.render_text(node.tail, self.config["color"], False)

    def handle_ul (self, node):
        indent = self.config["list_indent"]
        self.indent += indent
        self.newline()

        self.list_types.append("unordered")
        self.handle_children(node)
        self.list_types = self.list_types[:-1]

        self.indent -= indent
        self.newline()

    def handle_img (self, node):
        try:
            rsp = requests.get(node.attrib['src'], stream = True)
            img = Image.open (rsp.raw)
        except:
            img = None

        if img:
            self.render_img (img)
        else:
            has_alt = False
            if 'alt' in node.attrib:
                if node.attrib['alt'] != '':
                    has_alt = True
            if has_alt:
                self.render_text (node.attrib['alt'], self.config["color"], False)
            else:
                self.render_text (node.attrib['src'], self.config["color"], False)

        self.handle_children(node)
        self.render_text(node.tail, self.config["color"], False)

    def handle_unknown (self, node):
        print("Unknown tag: %s" % node.tag)
        self.handle_children(node)

    def newline (self, h= -1):
        if h == -1:
            h = self.line_height

        self.image_y += h
        self.y += h
        self.image_x = self.start_x + self.indent

        self.line_height = 0

    def new_image_block(self):
        self.save_image_block()

        self.image = Image.new("RGBA", (self.image_width, IMAGE_BLOCK_HEIGHT))
        self.image_draw = ImageDraw.Draw(self.image)
        self.image_y = 0

    @staticmethod
    def textsize(text, font):
        im = Image.new(mode="P", size=(0, 0))
        draw = ImageDraw.Draw(im)
        _, _, width, height = draw.textbbox((0, 0), text=text, font=font)
        return width, height

    def render_text(self, text, color, end_block=False, font=None, eliminate = None):
        if text is None:
            return

        blocks = []

        if font is None:
            font = self.default_font

        if self.in_pre:
            lines = text.split("\n")
            for line in lines:
                w, h = self.textsize (line, font=font)
                draw = self.ensure_image(h)

                draw.text((self.image_x, self.image_y), line, font=font, fill=color)
                blocks.append((self.image_x, self.y, w, h))

                self.line_height = max(h, self.line_height)
                self.newline()
        else:
            text = self.compact_whitespace(text)
            start_index = 0
            end_index = 0
            draw = self.image_draw

            eliminate = '' if not eliminate else eliminate
            if eliminate == '':
                parts = text
            else:
                parts = text.split(eliminate)
            while end_index < len(parts):
                w = 0
                while end_index < len(parts):
                    (w, h) = self.textsize(eliminate.join(parts[start_index:end_index + 1]),
                                           font=font)
                    if self.image_x + w > self.end_x:
                        break

                    end_index += 1

                # In the case that we can't fit a single word on this line
                # just render the first word
                if start_index == end_index:
                    end_index = start_index + 1

                text_frag = eliminate.join(parts[start_index:end_index])
                draw = self.ensure_image(h)

                self.line_height = max(h, self.line_height)

                #print ("Rendering %s" % text_frag)
                draw.text((self.image_x, self.image_y),
                          text_frag,
                          font=font, fill=color)

                # Get a real measurement segment
                (w, h) = self.textsize(text_frag,
                                       font=font)
                blocks.append((self.image_x, self.y, w, h))

                if end_index < len(parts):
                    self.newline()
                else:
                    # If we are at the end of a block, write out a newline
                    if end_block:
                        self.newline()
                    # Otherwise, leave X at the end of the last word
                    else:
                        self.image_x += w

                start_index = end_index

        return blocks

    def render_img (self, img = None):
        if img is None:
            return

        w, h = img.size

        if self.image_x + w > self.end_x:
            if w > self.image_width:
                img = img.resize ((self.image_width, int (self.image_width * (h/w))))
            self.newline ()

        draw = self.ensure_image(h, retain = True, draw = False)
        self.line_height = max (img.size[1], self.line_height)

        draw.paste (img, (self.image_x, self.y))

        if self.image_x + img.size[0] > self.end_x:
            self.newline()
        else:
            self.image_x += img.size[0]

    def save_image_block(self):
        if self.image is not None:
            self.images.append((self.image, self.image_y))
            try:
                del self.image_draw
            except:
                pass

            self.image = None

    def convert_img (self, source):
        # Fixup the source text
        if not source.strip():
            return ''  # a blank unicode string

        try:
            source = str (source)
        except UnicodeDecodeError as e:  # pragma: no cover
            # Customise error message while maintaining original trackback
            e.reason += '. -- Note: Markdown only accepts unicode input!'
            raise

        # Split into lines and run the line preprocessors.
        self.lines = source.split("\n")
        for prep in self.preprocessors:
            self.lines = prep.run(self.lines)

        # Parse the high-level elements.
        root = self.parser.parseDocument(self.lines).getroot()

        # Run the tree-processors
        for treeprocessor in self.treeprocessors:
            newRoot = treeprocessor.run(root)
            if newRoot is not None:
                root = newRoot

        self.new_image_block()
        self.handle_node(root)

        # Add the last used image if necessary
        self.save_image_block()

        height = reduce(lambda x, y: x + y[1], self.images, 0)
        final = Image.new("RGBA", (self.image_width, height))
        y = 0
        for img in self.images:
            final.paste(img[0], (0, y))
            y += img[1]

        self.init ()
        return final

def md2png(md_str, width_spec, config = None):
    """
    md_str: Valid markdown in a string
    width_spec: A list of tuples (y-offset, x-offset, width) specifying the
                the width constraints for rendering.  Each tuple in the list
                will be used for rendering of all lines between y-offset and
                the next greater y-offset.  The largest y-offset will be used
                until the end of rendering.
    """
    md = Markdown_Ext (width_spec, config)
    return md.convert_img(md_str)

if __name__ == '__main__':
    markdown_text = """
# Heading
## Subheading

This is some text with [link](https://www.google.com/) and an image ![image](https://upload.wikimedia.org/wikipedia/commons/4/47/PNG_transparency_demonstration_1.png). Tnat's it!!!
"""
    output_filename = 'output.png'
    img = md2png (markdown_text, [(0, 0, 100)])
    img.save (output_filename)
