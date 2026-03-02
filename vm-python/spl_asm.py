#!/usr/bin/env python3
"""SPL Assembler — Assembles .spl source files to .rom bytecode.

Usage: python spl_asm.py <input.spl> [output.rom]

If output is omitted, writes to <input>.rom (replacing .spl extension).
"""

import sys
import os

# Instruction table: name -> (opcode, arg_type)
# arg_type: 'none', 'val8', 'port8', 'addr16', 'target16'
#   none     = no arguments
#   val8     = 8-bit immediate value (push)
#   port8    = 8-bit port number (in/out)
#   addr16   = 16-bit address, numeric only (load/store)
#   target16 = 16-bit address, label or numeric (jump/call)
INSTRUCTIONS = {
    'halt':             (0x00, 'none'),
    'push':             (0x01, 'val8'),
    'drop':             (0x02, 'none'),
    'dup':              (0x03, 'none'),
    'swap':             (0x04, 'none'),
    'over':             (0x05, 'none'),
    'add':              (0x10, 'none'),
    'sub':              (0x11, 'none'),
    'mul':              (0x12, 'none'),
    'div':              (0x13, 'none'),
    'mod':              (0x14, 'none'),
    'and':              (0x15, 'none'),
    'or':               (0x16, 'none'),
    'xor':              (0x17, 'none'),
    'not':              (0x18, 'none'),
    'lt':               (0x19, 'none'),
    'gt':               (0x1A, 'none'),
    'load':             (0x20, 'addr16'),
    'store':            (0x21, 'addr16'),
    'load-indirect':    (0x22, 'none'),
    'store-indirect':   (0x23, 'none'),
    'print-cstring':    (0x42, 'addr16'),
    'print-rom-string': (0x43, 'target16'),  # Accepts labels like jump
    'jump':             (0x30, 'target16'),
    'jump-if-zero':     (0x31, 'target16'),
    'jump-if-not-zero': (0x32, 'target16'),
    'call':             (0x33, 'target16'),
    'return':           (0x34, 'none'),
    'in':               (0x40, 'port8'),
    'out':              (0x41, 'port8'),
}

# Byte sizes: none=1, val8=2, port8=2, addr16=3, target16=3
ARG_SIZES = {'none': 1, 'val8': 2, 'port8': 2, 'addr16': 3, 'target16': 3}


def error(msg, line=None):
    prefix = f"Error line {line}: " if line else "Error: "
    print(prefix + msg, file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------

def tokenize(source, filename="<input>"):
    """Tokenize SPL source into a list of (type, value, line) tuples."""
    tokens = []
    i = 0
    line = 1
    n = len(source)

    while i < n:
        c = source[i]

        if c == '\n':
            line += 1
            i += 1
        elif c in ' \t\r':
            i += 1
        elif c == ';':
            # Comment — skip to end of line
            while i < n and source[i] != '\n':
                i += 1
        elif c == '(':
            tokens.append(('LPAREN', '(', line))
            i += 1
        elif c == ')':
            tokens.append(('RPAREN', ')', line))
            i += 1
        elif c == '"':
            # String literal: "..." with escape sequences
            i += 1  # skip opening quote
            string_val = []
            while i < n and source[i] != '"':
                if source[i] == '\\':
                    i += 1
                    if i >= n:
                        error("unterminated string escape", line)
                    esc = source[i]
                    if esc == 'n':    string_val.append('\n')
                    elif esc == 't':  string_val.append('\t')
                    elif esc == '\\': string_val.append('\\')
                    elif esc == '"':  string_val.append('"')
                    elif esc == '0':  string_val.append('\0')
                    else:
                        error(f"unknown escape '\\{esc}'", line)
                elif source[i] == '\n':
                    error("unterminated string literal", line)
                else:
                    string_val.append(source[i])
                i += 1
            if i >= n:
                error("unterminated string literal", line)
            i += 1  # skip closing quote
            tokens.append(('STRING', ''.join(string_val), line))
        elif c.isalpha():
            # Identifier: letter { letter | digit | '-' | '_' }
            start = i
            i += 1
            while i < n and (source[i].isalnum() or source[i] in '-_'):
                i += 1
            tokens.append(('IDENT', source[start:i], line))
        elif c.isdigit():
            # Number: decimal or 0x hex
            start = i
            if i + 1 < n and source[i] == '0' and source[i + 1] in 'xX':
                i += 2
                if i >= n or source[i] not in '0123456789abcdefABCDEF':
                    error("invalid hex literal", line)
                while i < n and source[i] in '0123456789abcdefABCDEF':
                    i += 1
            else:
                while i < n and source[i].isdigit():
                    i += 1
            tokens.append(('NUMBER', source[start:i], line))
        else:
            error(f"unexpected character '{c}'", line)

    return tokens


def tokenize_with_includes(source, filename, include_stack=None):
    """Tokenize source, recursively processing (include "file") directives."""
    if include_stack is None:
        include_stack = []

    abs_path = os.path.abspath(filename)
    if abs_path in include_stack:
        error(f"circular include: '{filename}'")
    include_stack.append(abs_path)

    raw_tokens = tokenize(source, filename)
    result = []
    i = 0
    n = len(raw_tokens)

    while i < n:
        # Detect pattern: ( include "path" )
        if (i + 3 < n
                and raw_tokens[i][0] == 'LPAREN'
                and raw_tokens[i + 1] == ('IDENT', 'include', raw_tokens[i + 1][2])
                and raw_tokens[i + 2][0] == 'STRING'
                and raw_tokens[i + 3][0] == 'RPAREN'):
            inc_line = raw_tokens[i + 1][2]
            inc_path = raw_tokens[i + 2][1]

            base_dir = os.path.dirname(abs_path)
            resolved = os.path.normpath(os.path.join(base_dir, inc_path))

            try:
                with open(resolved, 'r', encoding='utf-8') as f:
                    inc_source = f.read()
            except FileNotFoundError:
                error(f"include file not found: '{inc_path}'", inc_line)

            inc_tokens = tokenize_with_includes(inc_source, resolved, include_stack)
            result.extend(inc_tokens)
            i += 4
        else:
            result.append(raw_tokens[i])
            i += 1

    include_stack.pop()
    return result


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def parse(tokens):
    """Parse tokens into (expressions, macros).

    expressions: list of (instruction, args, line) tuples.
    macros: dict mapping macro name -> list of (instr, args, line) body expressions.
    """
    expressions = []
    macros = {}
    i = 0
    n = len(tokens)

    while i < n:
        # Expect '('
        if tokens[i][0] != 'LPAREN':
            error(f"expected '(', got '{tokens[i][1]}'", tokens[i][2])
        i += 1

        # Expect identifier (instruction name)
        if i >= n:
            error("unexpected end of file after '('")
        if tokens[i][0] != 'IDENT':
            error(f"expected instruction name, got '{tokens[i][1]}'", tokens[i][2])
        instr = tokens[i][1]
        instr_line = tokens[i][2]
        i += 1

        if instr == 'include':
            # Malformed include that was not resolved at tokenization
            error("'include' requires exactly one string argument: "
                  '(include "file.spl")', instr_line)

        if instr == 'macro':
            # --- Macro definition: (macro name (body-instr args...)...) ---
            if i >= n or tokens[i][0] != 'IDENT':
                error("'macro' requires a name identifier", instr_line)
            macro_name = tokens[i][1]
            macro_line = tokens[i][2]
            i += 1

            if macro_name in INSTRUCTIONS:
                error(f"macro name '{macro_name}' conflicts with instruction", macro_line)
            if macro_name in ('label', 'data', 'macro', 'include'):
                error(f"macro name '{macro_name}' is a reserved word", macro_line)
            if macro_name in macros:
                error(f"duplicate macro '{macro_name}'", macro_line)

            body = []
            while i < n and tokens[i][0] != 'RPAREN':
                # Each body element is an S-expression: (instr args...)
                if tokens[i][0] != 'LPAREN':
                    error(f"expected '(' for macro body instruction, "
                          f"got '{tokens[i][1]}'", tokens[i][2])
                i += 1  # skip (

                if i >= n or tokens[i][0] != 'IDENT':
                    error("expected instruction name in macro body",
                          tokens[i][2] if i < n else instr_line)
                body_instr = tokens[i][1]
                body_line = tokens[i][2]
                i += 1

                body_args = []
                while i < n and tokens[i][0] != 'RPAREN':
                    if tokens[i][0] not in ('IDENT', 'NUMBER', 'STRING'):
                        error(f"expected argument, got '{tokens[i][1]}'",
                              tokens[i][2])
                    body_args.append(tokens[i])
                    i += 1

                if i >= n:
                    error("unexpected end of file in macro body, expected ')'")
                i += 1  # skip ) closing body instruction

                body.append((body_instr, body_args, body_line))

            if i >= n:
                error("unexpected end of file, expected ')' to close macro")
            i += 1  # skip ) closing macro

            if len(body) == 0:
                error(f"macro '{macro_name}' has empty body", instr_line)

            macros[macro_name] = body
        else:
            # --- Normal instruction ---
            args = []
            while i < n and tokens[i][0] != 'RPAREN':
                if tokens[i][0] not in ('IDENT', 'NUMBER', 'STRING'):
                    error(f"expected argument, got '{tokens[i][1]}'", tokens[i][2])
                args.append(tokens[i])
                i += 1

            if i >= n:
                error("unexpected end of file, expected ')'")
            i += 1  # skip ')'

            expressions.append((instr, args, instr_line))

    return expressions, macros


# ---------------------------------------------------------------------------
# Macro expansion
# ---------------------------------------------------------------------------

def expand_macros(expressions, macros):
    """Replace macro invocations with their body expressions."""
    if not macros:
        return expressions

    MAX_DEPTH = 64

    def expand(exprs, depth):
        if depth > MAX_DEPTH:
            error("macro expansion depth exceeded (possible infinite recursion)")
        result = []
        for instr, args, line in exprs:
            if instr in macros:
                if len(args) > 0:
                    error(f"macro '{instr}' does not accept arguments", line)
                body = macros[instr]
                result.extend(expand(body, depth + 1))
            else:
                result.append((instr, args, line))
        return result

    return expand(expressions, 0)


# ---------------------------------------------------------------------------
# Number parsing
# ---------------------------------------------------------------------------

def parse_number(token, line):
    """Parse a NUMBER token into an integer."""
    if token[0] != 'NUMBER':
        error(f"expected a number, got '{token[1]}'", line)
    text = token[1]
    try:
        if text.startswith(('0x', '0X')):
            return int(text, 16)
        else:
            return int(text)
    except ValueError:
        error(f"invalid number '{text}'", line)


# ---------------------------------------------------------------------------
# Assembler (two-pass)
# ---------------------------------------------------------------------------

def assemble(expressions):
    """Two-pass assembly: resolve labels, emit bytecode."""

    # --- Pass 1: collect labels and compute byte offsets ---
    labels = {}
    offset = 0

    for instr, args, line in expressions:
        if instr == 'label':
            if len(args) != 1 or args[0][0] != 'IDENT':
                error("'label' requires exactly one identifier argument", line)
            name = args[0][1]
            if name in labels:
                error(f"duplicate label '{name}'", line)
            if name in INSTRUCTIONS:
                error(f"label '{name}' conflicts with instruction name", line)
            labels[name] = offset
            # label emits no bytes
        elif instr == 'data':
            if len(args) < 2:
                error("'data' requires a label and at least one data argument", line)
            if args[0][0] != 'IDENT':
                error("'data' first argument must be a label name", line)
            name = args[0][1]
            if name in labels:
                error(f"duplicate label '{name}'", line)
            if name in INSTRUCTIONS:
                error(f"label '{name}' conflicts with instruction name", line)
            labels[name] = offset
            for arg in args[1:]:
                if arg[0] == 'NUMBER':
                    offset += 1
                elif arg[0] == 'STRING':
                    offset += len(arg[1])
                else:
                    error(f"'data' arguments after label must be numbers (0-255) or strings, got '{arg[1]}'", line)
        elif instr in INSTRUCTIONS:
            _, arg_type = INSTRUCTIONS[instr]
            offset += ARG_SIZES[arg_type]
        else:
            error(f"unknown instruction '{instr}'", line)

    # --- Pass 2: emit bytecode ---
    bytecode = bytearray()

    for instr, args, line in expressions:
        if instr == 'label':
            continue

        if instr == 'data':
            for arg in args[1:]:  # skip label (first arg)
                if arg[0] == 'NUMBER':
                    val = parse_number(arg, line)
                    if val < 0 or val > 255:
                        error(f"data byte {val} out of range 0..255", line)
                    bytecode.append(val)
                elif arg[0] == 'STRING':
                    for ch in arg[1]:
                        code_point = ord(ch)
                        if code_point > 127:
                            error(f"data string contains non-ASCII character '{ch}'", line)
                        bytecode.append(code_point)
            continue

        opcode, arg_type = INSTRUCTIONS[instr]

        if arg_type == 'none':
            if len(args) != 0:
                error(f"'{instr}' takes no arguments", line)
            bytecode.append(opcode)

        elif arg_type == 'val8':
            if len(args) != 1:
                error(f"'{instr}' requires exactly 1 argument", line)
            val = parse_number(args[0], line)
            if val < 0 or val > 255:
                error(f"value {val} out of range 0..255", line)
            bytecode.append(opcode)
            bytecode.append(val)

        elif arg_type == 'port8':
            if len(args) != 1:
                error(f"'{instr}' requires exactly 1 argument", line)
            val = parse_number(args[0], line)
            if val < 0 or val > 255:
                error(f"port {val} out of range 0..255", line)
            bytecode.append(opcode)
            bytecode.append(val)

        elif arg_type == 'addr16':
            if len(args) != 1:
                error(f"'{instr}' requires exactly 1 argument", line)
            if args[0][0] == 'IDENT':
                error(f"'{instr}' requires a numeric address, not a label", line)
            val = parse_number(args[0], line)
            if val < 0 or val > 65535:
                error(f"address 0x{val:04X} out of range 0..0xFFFF", line)
            bytecode.append(opcode)
            bytecode.append((val >> 8) & 0xFF)  # HI
            bytecode.append(val & 0xFF)          # LO

        elif arg_type == 'target16':
            if len(args) != 1:
                error(f"'{instr}' requires exactly 1 argument", line)
            arg = args[0]
            if arg[0] == 'IDENT':
                name = arg[1]
                if name not in labels:
                    error(f"undefined label '{name}'", line)
                val = labels[name]
            else:
                val = parse_number(arg, line)
            if val < 0 or val > 65535:
                error(f"address 0x{val:04X} out of range 0..0xFFFF", line)
            bytecode.append(opcode)
            bytecode.append((val >> 8) & 0xFF)  # HI
            bytecode.append(val & 0xFF)          # LO

    return bytecode, labels


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("Usage: python spl_asm.py <input.spl> [output.rom]", file=sys.stderr)
        sys.exit(1)

    input_path = sys.argv[1]
    if len(sys.argv) >= 3:
        output_path = sys.argv[2]
    else:
        base, _ = os.path.splitext(input_path)
        output_path = base + '.rom'

    # Read source
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            source = f.read()
    except FileNotFoundError:
        print(f"Error: file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    # Assemble
    tokens = tokenize_with_includes(source, input_path)
    expressions, macros = parse(tokens)
    expressions = expand_macros(expressions, macros)
    bytecode, labels = assemble(expressions)

    # Write ROM
    with open(output_path, 'wb') as f:
        f.write(bytecode)

    print(f"Assembled {len(expressions)} instructions -> {len(bytecode)} bytes -> {output_path}")
    if labels:
        print(f"Labels: {', '.join(f'{name}=0x{addr:04X}' for name, addr in labels.items())}")


if __name__ == '__main__':
    main()
