import logging
import sys
from typing import Callable

from isa import read_code, parse_command, alu_commands, MAX_NUM, registers, Command, get_data_line, branch_commands, \
    op_commands, one_op_commands, two_op_commands, zero_op_commands, binary_to_hex, MAX_MEMORY, is_integer

ALU_OP_HANDLERS: dict[int, Callable[[int, int], int]] = {
    op_commands.index('add'): lambda left, right: left + right,
    op_commands.index('sub'): lambda left, right: left - right,
    op_commands.index('mod'): lambda left, right: left % right,
    op_commands.index('div'): lambda left, right: left // right,
    op_commands.index('mul'): lambda left, right: left * right,
    op_commands.index('xor'): lambda left, right: left ^ right,
    op_commands.index('and'): lambda left, right: left & right,
    op_commands.index('or'): lambda left, right: left | right,
    op_commands.index('cmp'): lambda left, right: left - right,
}


class ALU:
    def __init__(self):
        self.N = 0
        self.Z = 1
        self.C = 0

    def __str__(self):
        return f"N: {self.N} Z: {self.Z} C: {self.C}"

    def perform(self, op: int, left: int, right: int) -> int:
        handler = ALU_OP_HANDLERS[op]
        value = handler(left, right)
        value = self.handle_overflow(value)
        self.set_flags(value)
        return value

    def set_flags(self, value) -> None:
        self.Z = int(value == 0)
        self.N = int(value < 0)

    def handle_overflow(self, value: int) -> int:
        if value >= MAX_NUM:
            self.C = 1
            return value - MAX_NUM
        if value <= -MAX_NUM:
            self.C = 1
            return value + MAX_NUM
        self.C = 0
        return value


class DataPath:
    reg = {name: 0 for name in registers}
    memory: list[str] = []
    alu: ALU = ALU()
    ports: dict[int, list] = []

    def __init__(self, data_memory, data_memory_size, ports, start_addr):
        assert data_memory_size > len(data_memory), "Data_memory size should be more"
        self.data_memory_size = data_memory_size
        self.memory = data_memory + [format(0, '012x')] * (data_memory_size - len(data_memory))
        self.ports = ports
        self.set_reg('rip', start_addr)
        self.set_reg('rsp', data_memory_size - 1)
        self.prev = format(0, '012x')

    def __str__(self):
        #return self.memory[self.get_reg('rip')]
        return self.prev

    def get_reg(self, reg: str) -> int:
        return self.reg[reg]

    def set_reg(self, reg: str, val: int) -> None:
        self.reg[reg] = val

    def reg_add(self, reg: str, val: int) -> None:
        self.reg[reg] += val

    def wr(self, addr: int, value: int) -> None:
        self.memory[addr] = binary_to_hex(get_data_line(value))

    def wr_port(self, port: int, val: int) -> None:
        self.ports[port].append(chr(val))
        logging.debug("OUTPUT: " + str(self.ports[port][:-1]) + ' <- ' + (str(self.ports[port][-1]) if str(self.ports[port][-1]) != '\n' else '\\n'))

    def rd(self, reg: str, addr: int) -> None:
        self.set_reg(reg, Command(self.memory[addr]).arg1_value)

    def rd_port(self, port: int, addr: int) -> None:
        if is_integer(str(self.ports[port][0][1])):
            logging.debug("INPUT: " + str(self.ports[port][0][1]))
            self.memory[addr] = binary_to_hex(get_data_line(self.ports[port].pop(0)[1]))
        else:
            logging.debug("INPUT: " + (self.ports[port][0][1] if self.ports[port][0][1] != '\n' else '\\n'))
            self.memory[addr] = binary_to_hex(get_data_line(ord(self.ports[port].pop(0)[1])))

    def latch_ip(self, value: int = -1):
        self.prev = self.memory[self.get_reg('rip')]
        if value >= 0:
            self.set_reg('rip', value - 1)
        else:
            self.set_reg('rip', self.get_reg('rip') + 1)

    def get_instruction(self) -> str:
        return self.memory[self.get_reg('rip')]

    def get_arg(self, arg_type: int, val: int = 0) -> int:
        if arg_type == 0:
            return val
        elif arg_type == 1:
            return self.get_reg(registers[val])
        elif arg_type == 2:
            return Command(self.memory[val]).arg1_value
        elif arg_type == 4:
            return self.get_arg(2, Command(self.memory[val]).arg1_value)

    def get_addr(self, arg_type: int, val: int) -> int:
        if arg_type == 2:
            return val
        elif arg_type == 4:
            return Command(self.memory[val]).arg1_value

class ControlUnit:
    def __init__(self, data_path, limit):
        self.data_path = data_path
        self.instr_counter = 0  # счетчик чтобы машина не работала бесконечно
        self._tick = 0
        self.limit = limit
        self.command = 'nop'

    def tick(self):
        self._tick += 1

    def current_tick(self):
        return self._tick

    def command_cycle(self):
        logging.debug("%s", self)
        try:
            while self.instr_counter < self.limit:
                self.decode_and_execute_instruction()
                self.data_path.latch_ip()
                logging.debug("%s", self)
                self.instr_counter += 1
                self.interruption_cycle()
        except EOFError:
            logging.warning("Input buffer is empty!")
        except StopIteration:
            logging.debug("%s", self)

        if self.instr_counter >= self.limit:
            logging.warning("Limit exceeded!")

    def update_interruption_state(self):
        input = self.data_path.ports[0]
        if len(input) and input[0][0] <= self.current_tick():
            self.data_path.set_reg('rst', self.data_path.get_reg('rst') | 2)

    def execute_interruption(self):
        self.data_path.set_reg('rst', 0)
        self.tick()

        self.data_path.wr(self.data_path.get_reg('rsp'), self.data_path.get_reg('rip'))
        self.data_path.reg_add('rsp', -1)
        self.tick()

        self.data_path.wr(self.data_path.get_reg('rsp'), self.data_path.get_reg('rax'))
        self.data_path.reg_add('rsp', -1)
        self.tick()

        self.data_path.rd('rip', 1)
        self.tick()

    def decode_and_execute_control_zero_arg_instruction(self, instr, opcode):
        if opcode == 'ei':
            self.data_path.set_reg('rst', self.data_path.get_reg('rst') | 1)
            self.tick()
        if opcode == 'di':
            self.data_path.set_reg('rst', self.data_path.get_reg('rst') & ~1)
            self.tick()
        if opcode == 'iret':
            self.data_path.reg_add('rsp', 1)
            self.data_path.rd('rax', self.data_path.get_reg('rsp'))
            self.tick()

            self.data_path.reg_add('rsp', 1)
            self.data_path.rd('rip', self.data_path.get_reg('rsp'))
            self.data_path.reg_add('rip', -1)
            self.tick()

            self.data_path.set_reg('rst', self.data_path.get_reg('rst') | 1)
            self.tick()

    def decode_and_execute_control_two_arg_instruction(self, instr, opcode):
        if opcode in alu_commands:
            if instr.arg1_type == 1:
                left = self.data_path.get_arg(instr.arg1_type, instr.arg1_value)
                right = self.data_path.get_arg(instr.arg2_type, instr.arg2_value)

                res = self.data_path.alu.perform(instr.command_type, left, right)
                if opcode != 'cmp':
                    self.data_path.set_reg(registers[instr.arg1_value], res)
                    self.tick()
            else:
                left = self.data_path.get_arg(instr.arg1_type, instr.arg1_value)
                self.tick()
                right = self.data_path.get_arg(instr.arg2_type, instr.arg2_value)
                self.tick()

                res = self.data_path.alu.perform(instr.command_type, left, right)
                if opcode != 'cmp':
                    self.data_path.wr(instr.arg1_value, res)
                    self.tick()
        if opcode == 'mov':
            if instr.arg1_type == 1:
                right = self.data_path.get_arg(instr.arg2_type, instr.arg2_value)
                self.data_path.alu.set_flags(right)
                self.data_path.set_reg(registers[instr.arg1_value], right)
                self.tick()
            elif instr.arg2_type == 1:
                right = self.data_path.get_arg(instr.arg2_type, instr.arg2_value)
                self.data_path.wr(instr.arg1_value, right)
                self.tick()
            else:
                right = self.data_path.get_arg(instr.arg2_type, instr.arg2_value)
                self.tick()

                self.data_path.wr(self.data_path.get_addr(instr.arg1_type, instr.arg1_value), right)
                self.tick()
        if opcode == 'movo':
            self.data_path.wr_port(instr.arg1_value, self.data_path.get_arg(instr.arg2_type, instr.arg2_value))
            self.tick()
        if opcode == 'movi':
            self.data_path.rd_port(instr.arg2_value, instr.arg1_value)
            self.tick()

    def decode_and_execute_control_flow_instruction(self, instr, opcode):
        """Декодировать и выполнить инструкцию управления потоком исполнения. В
        случае успеха -- вернуть `True`, чтобы перейти к следующей инструкции.
        """

        if opcode == 'jmp':
            self.data_path.latch_ip(instr.arg1_value)
            self.tick()

        if opcode == 'jz':
            if self.data_path.alu.Z:
                self.data_path.latch_ip(instr.arg1_value)
            self.tick()

        if opcode == 'jnz':
            if not self.data_path.alu.Z:
                self.data_path.latch_ip(instr.arg1_value)
            self.tick()

        if opcode == 'jn':
            if self.data_path.alu.N:
                self.data_path.latch_ip(instr.arg1_value)
            self.tick()

        if opcode == 'jp':
            if not self.data_path.alu.N:
                self.data_path.latch_ip(instr.arg1_value)
            self.tick()

    def decode_and_execute_instruction(self):
        instr = Command(self.data_path.get_instruction())
        opcode = op_commands[instr.command_type]
        self.tick()
        self.command = instr

        if opcode == 'hlt':
            raise StopIteration()

        if opcode in branch_commands:
            self.decode_and_execute_control_flow_instruction(instr, opcode)

        if opcode in two_op_commands:
            self.decode_and_execute_control_two_arg_instruction(instr, opcode)

        if opcode in zero_op_commands:
            self.decode_and_execute_control_zero_arg_instruction(instr, opcode)


    def interruption_cycle(self):
        self.update_interruption_state()
        if self.data_path.get_reg('rst') & 1 and self.data_path.get_reg('rst') >> 1 & 1:
            self.execute_interruption()

    def __repr__(self):
        register_values = ', '.join(f"{name}: {value}" for name, value in self.data_path.reg.items())
        return f"Tick: {self.current_tick()} | Registers: {register_values} Flags: {self.data_path.alu} | Instruction: {self.command}"


def simulation(code, input_tokens, memory_size, limit, start_addr):
    data_path = DataPath(code, memory_size, {0: input_tokens, 1: []}, start_addr)
    control_unit = ControlUnit(data_path, limit)
    control_unit.command_cycle()
    logging.info("output_buffer: %s", repr("".join(data_path.ports[1])))
    return "".join(data_path.ports[1]), control_unit.instr_counter, control_unit.current_tick()


def main(code_file, input_file):
    with open(input_file, encoding="utf-8") as file:
        input_text = file.read()
        if not input_text:
            input_token = []
        else:
            input_token = eval(input_text)

    start_addr, code = read_code(code_file)
    output, instr_counter, ticks = simulation(
        code,
        input_tokens=input_token,
        memory_size=MAX_MEMORY,
        limit=20000,
        start_addr=start_addr
    )

    print("".join(output))
    print("instr_counter: ", instr_counter, "ticks:", ticks)


if __name__ == "__main__":
    logging.getLogger().setLevel(logging.DEBUG)
    assert len(sys.argv) == 3, "Wrong arguments: machine.py <code_file> <input_file>"
    _, code_file, input_file = sys.argv
    main(code_file, input_file)
