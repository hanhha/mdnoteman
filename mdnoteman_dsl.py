#!/usr/bin/env python

import ply.lex as lex
import re

# Token definitions
tokens = (
    'LABEL',
    'TAG',
    'AND',
    'OR',
    'NOT',
    'IDEN',
    'LPAREN',
    'RPAREN',
    'CTN',
)

# Ignore chars
t_ignore = ' \t'

# Token regular expressions
t_LPAREN    = r'\('
t_RPAREN    = r'\)'

def t_LABEL (t):
    r'\b[Ll][Aa][Bb][Ee][Ll][Ss]?\b'
    t.type = 'LABEL'
    return t

def t_TAG (t):
    r'\b[Tt][Aa][Gg][Ss]?\b'
    t.type = 'TAG'
    return t

def t_AND (t):
    r'(\b[Aa][Nn][Dd]\b|&)'
    t.type = 'AND'
    return t

def t_OR (t):
    r'(\b[Oo][Rr]\b|\||,)'
    t.type = 'OR'
    return t

def t_NOT (t):
    r'\b[Nn][Oo][Tt]\b|!|~'
    t.type = 'NOT'
    return t

def t_IDEN (t):
    r'\b[^,|&!~\s|]+\b'
    t.type = 'IDEN'
    return t

def t_CTN (t):
    r'["\'](\b.+\b)+["\']'
    t.type = 'CTN'
    return t

# Error handling rule
def t_error(t):
    print("Illegal character '%s'" % t.value[0])
    t.lexer.skip(1)

lexer = lex.lex ()

class Node():
    def __init__ (self, type, value = False, children = None):
        self._type  = type
        self._value = value
        self._children  = children or []

    def analyze (self, **kwargs):
        pass

    def acquire (self, Node):
        self._children.append (Node)
        return True

    def __str__ (self, indent = '  '):
        str_ = f"{self.type}: {self.value}" + '\n'
        str_ += f"{indent}" + ('\n' + indent).join([c.__str__() for c in self._children])
        return str_

    def reduce (self):
        i = 0
        if len(self._children) > 0:
            while (True):
                if (self._children[i].type == self.type):
                    tmp = self._children.pop (i)
                    extra = tmp._children
                    for e in extra:
                        self._children.insert (i, e)
                if self._children[i].type != self.type:
                    reduced = self._children[i].reduce ()
                    if reduced is not None:
                        self._children[i] = reduced
                    i += 1
                    if i == len (self._children):
                        break
        if len (self._children) == 1 and self.type in ('OR', 'AND'):
            return self._children [0]
        else:
            return None

    @property
    def type (self):
        return self._type

    @property
    def value (self):
        return self._value

class NotNode (Node):
    def __init__ (self, value = False, children = None):
        super().__init__ (type = 'NOT', children = children)

    def analyze (self, **kwargs):
        if len (self._children) == 1:
            self._value = not self._children[0].analyze (**kwargs)
        else:
            raise ValueError ("Invald AST - NOT must have only 1 child node")
        return self._value

    def acquire (self, Node):
        if len(self._children) == 0:
            self._children.append (Node)
            return True
        else:
            return False

    def __str__ (self, indent = '  '):
        str_ = self.type + '\n'
        str_ += indent + ('\n'+indent).join([c.__str__(indent + '  ') for c in self._children])
        return str_

class OrNode (Node):
    def __init__ (self, value = False, children = None):
        super().__init__ (type = 'OR', children = children)

    def analyze (self, **kwargs):
        self._value = False
        if len(self._children) > 0:
            for child in self._children:
                if child.analyze (**kwargs):
                    self._value = True
                    break
        else:
            raise ValueError ("Invald AST - OR must have at least 1 child node")
        return self._value

    def __str__ (self, indent = '  '):
        str_ = self.type + '\n'
        str_ += indent + ('\n'+indent).join([c.__str__(indent + '  ') for c in self._children])
        return str_

class AndNode (Node):
    def __init__ (self, value = False, children = None):
        super().__init__ (type = 'AND', children = children)

    def analyze (self, **kwargs):
        self._value = True
        if len(self._children) > 0:
            for child in self._children:
                if not child.analyze (**kwargs):
                    self._value = False
                    break
        else:
            raise ValueError ("Invald AST - AND must have at least 1 child node")
        return self._value

    def __str__ (self, indent = '  '):
        str_ = self.type + '\n'
        str_ += indent + ('\n'+indent).join([c.__str__(indent + '  ') for c in self._children])
        return str_

class EqlNode (Node):
    def __init__ (self, children = None):
        super().__init__ (type = 'EQL', children = children)

    def __str__ (self, indent = '  '):
        return f"{self.type}  {self._children[0].type} == {self._children[0].value}"

    def analyze (self, **kwargs):
        if len(self._children) == 1:
            self._value = False
            if self._children[0].type == 'LABEL':
                if 'labels' in kwargs:
                    for lbl in kwargs['labels']:
                        if self._children[0].value.lower() == lbl.lower():
                           self._value = True
                           break
            elif self._children[0].type == 'TAG':
                if self._children[0].value.lower() == 'all':
                    self._value = True
                elif 'tags' in kwargs:
                    for tag in kwargs['tags']:
                        if self._children[0].value.lower() == tag.lower():
                           self._value = True
                           break
            elif self._children[0].type == 'CTN':
                if 'ctn' in kwargs:
                    self._value = re.sub(' +', ' ', self._children[0].value.casefold()) in  re.sub(' +', ' ', kwargs['ctn'].casefold())
            else:
                raise ValueError ("Invald AST - Invalid type %s in EQL node" %(self._children[0]))
        else:
            raise ValueError ("Invald AST - EQL must have only 1 child node")
        return self._value

    def acquire (self, Node):
        if len(self._children) == 0:
            self._children.append (Node)
            return True
        else:
            return False

def build_ast (tokens, factor = None):
    stack      = [OrNode()]
    indent     = 0
    _factor     = factor
    inv_factor = False
    inv        = False
    subtoks    = []

    for tok in tokens:
        if tok.type == 'LPAREN':
            indent += 1
        elif tok.type == 'RPAREN':
            indent -= 1
            if (indent == 0):
                if (len(subtoks) > 0):
                    node = build_ast (subtoks, _factor)
                    stack[-1].acquire (node)
                    subtoks = []
                else:
                    raise ValueError ("Invald syntax - ')' is not expected")
        else:
            if indent > 0:
                subtoks.append (tok)
            else:
                #print (f"{tok.type} -> {tok.value}")
                if tok.type == 'CTN':
                    _factor = None
                    node = EqlNode ([Node(tok.type, tok.value)])
                    if not stack[-1].acquire (node):
                        tmp_node = stack.pop ()
                        stack[-1].acquire (tmp_node)
                        stack.append (node)
                elif tok.type in ('LABEL', 'TAG'):
                    _factor = tok.type
                    node = OrNode ()
                    stack.append (node)
                elif tok.type == 'NOT':
                    node = NotNode ()
                    stack.append (node)
                elif tok.type == 'IDEN':
                    if _factor is None:
                        node = EqlNode ([Node('CTN', tok.value)])
                    else:
                        node = EqlNode ([Node(_factor, tok.value)])
                    if not stack[-1].acquire (node):
                        tmp_node = stack.pop ()
                        stack[-1].acquire (tmp_node)
                        stack.append (node)
                elif tok.type == 'AND':
                    prev_node = stack.pop ()
                    if prev_node.type == 'OR':
                        stack.append (prev_node)
                        prev_node = stack[-1]._children.pop ()
                    node = AndNode (children = [prev_node])
                    stack.append (node)
                elif tok.type == 'OR':
                    prev_node = stack.pop ()
                    node = OrNode (children = [prev_node])
                    stack.append (node)

    while len(stack) > 1:
        node = stack.pop ()
        if not stack[-1].acquire (node):
            tmp_node = stack.pop ()
            stack[-1].acquire (tmp_node)
            stack.append (node)
    reduced = stack[0].reduce ()
    #print (stack[0])
    return reduced if reduced is not None else stack [0]

def filter (query_str):
    lexer.input (query_str)
    return (build_ast(lexer))

if __name__ == '__main__':
    #data = '"mama mama mama" (labels label_aaa/bbb, bbb & tag_ccc, ddd) ,  (tags 123, tagcc, tag_1)'
    data = '"mama mama mama" labels label_aaa/bbb, bbb & tag_ccc, ddd & tags 123, tagcc, tag_1'

    print (filter (data))
