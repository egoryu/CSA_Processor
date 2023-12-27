import re
from typing import Final

registers: list[str] = ["rax", "rbx", "rdx", "rip", "rst", "rsp"]
branch_commands: list[str] = ["jmp", "jz", "jnz", "jn", "jp"]
alu_commands: list[str] = ["add", "sub", "mul", "div", "mod", "xor", "and", "or", "cmp"]
two_op_commands: list[str] = alu_commands + ["mov", "movi", "movo"]
one_op_commands: list[str] = branch_commands
zero_op_commands: list[str] = ["iret", "di", "ei", "hlt"]
op_commands: list[str] = ["nop"] + two_op_commands + one_op_commands + zero_op_commands

RE_STR: Final = r'^(\'.*\')|(\".*\")$'
MAX_NUM: Final = 1 << 15
MAX_MEMORY: Final = 1 << 11

class Instruction:
    def __init__(self, address: int, binary_code: str, mnemonic: str):
        self.address = address
        self.binary_code = binary_code
        self.mnemonic = mnemonic

    def __str__(self):
        return f"{self.address} {binary_to_hex(self.binary_code)} {self.mnemonic}"

def get_type_adress(type: int, arg: int) -> str:
    if type == 0:
        return str(arg)
    elif type == 1:
        return '%' + registers[arg]
    elif type == 2:
        return '#' + str(arg)
    else:
        return '!' + str(arg)

class Command:
    def __init__(self, hex_string):
        self.hex_string = hex_string
        self.command_type, self.arg1_type, self.arg1_value, self.arg2_type, self.arg2_value = parse_command(hex_string)

    def __str__(self):
        if op_commands[self.command_type] in two_op_commands:
            return f"{op_commands[self.command_type]} {get_type_adress(self.arg1_type, self.arg1_value)} {get_type_adress(self.arg2_type, self.arg2_value)}"
        elif op_commands[self.command_type] in one_op_commands:
            return f"{op_commands[self.command_type]} {get_type_adress(self.arg1_type, self.arg1_value)}"
        else:
            return f"{op_commands[self.command_type]}"

def is_integer(string: str) -> bool:
    return bool(re.match(r'^-?\d+$', string))

def is_string(string: str) -> bool:
    return bool(re.fullmatch(RE_STR, string))

def int_to_binary(n: int) -> str:
    if n >= 0:
        binary = format(n, "016b")
    else:
        binary = format(n & 0xffff, "016b")

    return binary

def binary_to_hex(binary_code: str) -> str:
    return format(int(binary_code, 2), '012x')
def get_data_line(line: int) -> str:
    return format(0, "012b") + int_to_binary(line) + format(0, "020b")
def binary_to_integer(binary: str) -> int:
    if binary[0] == '1':
        complement = ''.join(['1' if x == '0' else '0' for x in binary])
        integer = -(int(complement, 2) + 1)
    else:
        integer = int(binary, 2)

    return integer

def parse_command(hex_string):
    # Разбиваем строку на две части: первые 8 символов и остальную часть
    first_8_bits = hex_string[:2]
    remaining_bits = hex_string[2:]

    # Получаем тип команды из первых 8 битов
    command_type = int(first_8_bits, 16)

    # Получаем тип первого аргумента из первых 2 битов оставшейся части
    arg1_type = int(remaining_bits[:1], 16)

    # Получаем значение первого аргумента из следующих 4 битов оставшейся части
    arg1_value = binary_to_integer(format(int(remaining_bits[1:5], 16), "016b"))

    # Получаем тип второго аргумента из следующих 2 битов оставшейся части
    arg2_type = int(remaining_bits[5:6], 16)

    # Получаем значение второго аргумента из следующих 4 битов оставшейся части
    arg2_value = binary_to_integer(format(int(remaining_bits[6:10], 16), "016b"))

    return command_type, arg1_type, arg1_value, arg2_type, arg2_value

def write_code(instructions: list[Instruction], source: str):
    with open(source, "w") as file:
        for instruction in instructions:
            file.write(str(instruction) + "\n")

def read_code(filename):
    instr: list[str] = []

    with open(filename, encoding="utf-8") as file:
        code = file.read()

    for line in code.splitlines():
        instr.append(line.split(' ')[1])

    start_addr = parse_command(instr[0])[2]

    return start_addr, instr
