#!/usr/bin/env python

import ply.lex as lex

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
    r'(\b[Oo][Rr]\b|\|)'
    t.type = 'OR'
    return t

def t_NOT (t):
    r'\b[Nn][Oo][Tt]\b'
    t.type = 'NOT'
    return t

def t_IDEN (t):
    r'\b[_a-zA-Z0-9]+\b'
    t.type = 'IDEN'
    return t

# Error handling rule
def t_error(t):
    print("Illegal character '%s'" % t.value[0])
    t.lexer.skip(1)

lexer = lex.lex ()

if __name__ == '__main__':
    data = '& labels | label_aaa bbb & tag_ccc ddd tags | 123 tagcc tag_1'

    lexer.input (data)
    # Tokenize
    for tok in lexer:
        print (tok)
