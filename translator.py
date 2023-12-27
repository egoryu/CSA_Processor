import sys
import re
from typing import Final

from exception import UnexpectedDataValue, RepeatedVariableName
from isa import is_integer, is_string, Instruction, op_commands, registers, write_code, int_to_binary, get_data_line

SECTION_TEXT: Final = 'section .text'
SECTION_DATA: Final = 'section .data'


def remove_comment(line: str) -> str:
    return re.sub(r';.*', '', line)


def remove_spaces(line: str) -> str:
    return re.sub(r'\s+', ' ', line)


def clean_text(asm_text: str) -> str:
    lines: list[str] = asm_text.splitlines()

    remove_comments = map(remove_comment, lines)
    strip_lines = map(str.strip, remove_comments)
    remove_empty_lines = filter(bool, strip_lines)
    remove_extra_spaces = map(remove_spaces, remove_empty_lines)
    clean_text: str = '\n'.join(remove_extra_spaces)

    return clean_text


def parse_data_line(line: str, variable: dict[str, int]) -> tuple[str, list[int]]:
    key, value = map(str.strip, line.split(':', 1))

    constant_mem: list[int]
    if value.startswith('buf '):
        param = value.split(' ')
        if len(param) == 3:
            constant_mem = [int(param[2]) for _ in range(int(param[1]))]
        elif len(param) == 2:
            constant_mem = [0 for _ in range(int(param[2]))]
        else:
            raise UnexpectedDataValue(value)
    elif is_integer(value):
        constant_mem = [int(value)]
    elif is_string(value):
        string: str = value[1:-1]
        constant_mem = [len(string)] + [ord(char) for char in string]
    else:
        constant_mem = [variable[value]]

    return key, constant_mem
def parse_data_section(code: str) -> tuple[dict[str, int], list[int]]:
    variable: dict[str, int] = {
        'JMPS': 0,
        'INT': 1,
    }
    memory: list[int] = [
        0,
        0,
    ]

    for line in code.splitlines():
        key, constant_mem = parse_data_line(line, variable)
        if key in variable:
            raise RepeatedVariableName(key)
        variable[key] = len(memory)
        memory.extend([constant for constant in constant_mem])

    print(memory)
    return variable, memory

def get_binary_line(line: str) -> str:
    words = line.split(' ')
    op_code = format(op_commands.index(words[0]), "08b")
    for word in words[1:]:
        arg: str
        if word.startswith('%'):
            arg = format(1, "04b") + format(registers.index(word[1:]), "016b")
        elif word.startswith('#'):
            arg = format(2, "04b") + format(int(word[1:]), "016b")
        elif word.startswith('!'):
            arg = format(3, "04b") + format(int(word[1:]), "016b")
        elif word.startswith('*'):
            arg = format(4, "04b") + format(int(word[1:]), "016b")
        else:
            arg = format(0, "04b") + int_to_binary(int(word))
        op_code += arg

    for _ in range(3 - len(words)):
        op_code += format(0, "020b")

    return op_code

def generate_binary(code: list[str], data: list[int]):
    binary_code: list[Instruction] = []
    cur: int = 0

    for line in data:
        binary_code.append(Instruction(cur, get_data_line(line), str(line)))
        cur += 1
    for line in code:
        binary_code.append(Instruction(cur, get_binary_line(line), line))
        cur += 1

    return binary_code

def parse_text_section(variable: dict[str, int], code: str, cur: int):
    lines: list[str] = []
    labels: dict[str, int] = {}

    for line in code.splitlines():
        if line.startswith('.'):
            name, command = map(str.strip, line.split(':', 1))
            labels[name] = cur
            line = command

        string = line.split(' ')
        if len(string) <= 3:
            lines.append(line)
        else:
            name, argS, *args = string
            lines.extend([name + ' ' + argS + ' ' + arg for arg in args])
            cur += len(args) - 1

        cur += 1

    for index, line in enumerate(lines):
        words = line.split(' ')
        if len(words) == 1:
            continue

        ans: str
        ans = words[0]
        for word in words[1:]:
            if is_integer(word) or word.startswith('%') or word.startswith('!'):
                ans += ' ' + word
            elif word.startswith('#'):
                ans += ' #' + str(variable[word[1:]])
            elif word.startswith('.'):
                ans += ' ' + str(labels[word])
            elif word.startswith('*'):
                ans += ' *' + str(variable[word[1:]])
            else:
                name, offset = word.split('[')
                ans += ' #' + str(variable[name] + int(offset[:-1]))
        lines[index] = ans

    return lines


def translate(code: str):
    text_index: int = code.find(SECTION_TEXT)
    data_index: int = code.find(SECTION_DATA)

    variable, memory = parse_data_section(code[data_index + len(SECTION_DATA) + 1:text_index])
    memory[0] = len(memory)
    code = parse_text_section(variable, code[text_index + len(SECTION_DATA) + 1:], memory[0])
    binary_code = generate_binary(code, memory)

    print(variable)
    print(memory)
    print(code)

    for line in binary_code:
        print(line)

    return binary_code

def main(source, target):
    with open(source, encoding="utf-8") as f:
        source = f.read()

    source = clean_text(source)
    code = translate(source)

    write_code(code, target)
    print("source LoC:", len(source.split("\n")), "code instr:", len(code))


if __name__ == "__main__":
    assert len(sys.argv) == 3, "Wrong arguments: translator.py <input_file> <target_file>"
    _, source, target = sys.argv
    main(source, target)