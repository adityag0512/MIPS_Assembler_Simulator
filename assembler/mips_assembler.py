import os
import re
import sys

class MIPSAssembler:
    def __init__(self):
        # 1. Register Lookup Table
        self.registers = {
            "$zero": 0, "$at": 1, "$v0": 2, "$v1": 3,
            "$a0": 4, "$a1": 5, "$a2": 6, "$a3": 7,
            "$t0": 8, "$t1": 9, "$t2": 10, "$t3": 11, "$t4": 12, "$t5": 13, "$t6": 14, "$t7": 15,
            "$s0": 16, "$s1": 17, "$s2": 18, "$s3": 19, "$s4": 20, "$s5": 21, "$s6": 22, "$s7": 23,
            "$t8": 24, "$t9": 25, "$k0": 26, "$k1": 27,
            "$gp": 28, "$sp": 29, "$fp": 30, "$ra": 31
        }
        
        # 2. Opcodes (6 bits)
        self.opcodes = {
            "add": 0, "addu": 0, "sub": 0, "subu": 0, "and": 0, "or": 0, 
            "xor": 0, "nor": 0, "sll": 0, "srl": 0, "sra": 0, "slt": 0, 
            "sltu": 0, "mult": 0, "div": 0, "mfhi": 0, "mflo": 0, "jr": 0, "jalr": 0, "syscall": 0,
            "addi": 8, "addiu": 9, "andi": 12, "ori": 13, "xori": 14, "lui": 15,
            "slti": 10, "sltiu": 11, "beq": 4, "bne": 5,
            "lw": 35, "lh": 33, "lhu": 37, "lb": 32, "lbu": 36,
            "sw": 43, "sh": 41, "sb": 40, "ll": 48, "sc": 56,
            "j": 2, "jal": 3
        }
        
        # 3. Function codes for R-type instructions (6 bits)
        self.functs = {
            "add": 32, "addu": 33, "sub": 34, "subu": 35, "and": 36, "or": 37,
            "xor": 38, "nor": 39, "sll": 0, "srl": 2, "sra": 3, "slt": 42,
            "sltu": 43, "mult": 24, "div": 26, "mfhi": 16, "mflo": 18,
            "jr": 8, "jalr": 9, "syscall": 12
        }

        self.label_map = {}
        self.machine_code = []

    def clean_line(self, line):
        """Strips comments and replaces commas with spaces for uniform tokenizing."""
        line = line.split('#')[0].strip()
        line = line.replace(',', ' ')
        return line

    def get_register(self, reg_name, line_num, instr_text):
        """Safely looks up a register or reports a strict validation error."""
        if reg_name not in self.registers:
            print(f"| ERROR | Line {line_num}: Invalid register name '{reg_name}' in instruction: '{instr_text}'")
            sys.exit(1)
        return self.registers[reg_name]

    def check_operand_count(self, tokens, expected_count, line_num, instr_text):
        """Ensures the instruction has the correct number of fields."""
        if len(tokens) != expected_count:
            print(f"| ERROR | Line {line_num}: Expected {expected_count - 1} operands for '{tokens[0]}', got {len(tokens) - 1} instead.")
            print(f"          Context: '{instr_text}'")
            sys.exit(1)

    def pass_one(self, lines):
        """Pass 1: Address calculation and Label resolution with duplicate checking."""
        address = 0
        cleaned_lines = []
        
        for i, raw_line in enumerate(lines):
            line_num = i + 1  # Track human-readable line numbers
            line = self.clean_line(raw_line)
            if not line:
                continue
            
            # Extract Label if it exists
            if ':' in line:
                label, rest_of_line = line.split(':', 1)
                label = label.strip()
                
                # Validation: Duplicate label check
                if label in self.label_map:
                    print(f"| ERROR | Line {line_num}: Duplicate label definition found for '{label}:'")
                    sys.exit(1)
                    
                self.label_map[label] = address
                line = rest_of_line.strip()
                
            if line:
                cleaned_lines.append((address, line_num, line))
                address += 4
        return cleaned_lines

    def pass_two(self, cleaned_lines):
        """Pass 2: Safely parses and translates code, raising explicit errors if issues appear."""
        for address, line_num, line in cleaned_lines:
            tokens = [t for t in line.split() if t]
            instr = tokens[0]
            
            # Validation: Instruction checking
            if instr not in self.opcodes:
                print(f"| ERROR | Line {line_num}: Unknown/Unsupported MIPS instruction mnemonic '{instr}'")
                sys.exit(1)
                
            opcode = self.opcodes[instr]
            mc = 0

            # J-TYPE INSTRUCTIONS: j, jal
            if instr in ["j", "jal"]:
                self.check_operand_count(tokens, 2, line_num, line)
                label = tokens[1]
                if label not in self.label_map:
                    print(f"| ERROR | Line {line_num}: Jump target label '{label}' is undefined.")
                    sys.exit(1)
                target_address = self.label_map[label]
                jump_addr = (target_address >> 2) & 0x3FFFFFF
                mc = (opcode << 26) | jump_addr

            # I-TYPE INSTRUCTIONS
            # Branches: beq, bne
            elif instr in ["beq", "bne"]:
                self.check_operand_count(tokens, 4, line_num, line)
                rs = self.get_register(tokens[1], line_num, line)
                rt = self.get_register(tokens[2], line_num, line)
                label = tokens[3]
                if label not in self.label_map:
                    print(f"| ERROR | Line {line_num}: Branch target label '{label}' is undefined.")
                    sys.exit(1)
                target_address = self.label_map[label]
                offset = ((target_address - (address + 4)) >> 2) & 0xFFFF
                mc = (opcode << 26) | (rs << 21) | (rt << 16) | offset

            # Memory: lw, sw, etc. -> expected: [instr, rt, offset(rs)]
            elif instr in ["lw", "lh", "lhu", "lb", "lbu", "sw", "sh", "sb", "ll", "sc"]:
                self.check_operand_count(tokens, 3, line_num, line)
                rt = self.get_register(tokens[1], line_num, line)
                
                # Check for correctly formatted structure offset(register)
                match = re.match(r"(-?\d+)\((\$\w+)\)", tokens[2])
                if not match:
                    print(f"| ERROR | Line {line_num}: Malformed memory offset/address format in '{tokens[2]}'.")
                    print(f"          Expected syntax format: '4($sp)' or '-8($s0)'")
                    sys.exit(1)
                    
                imm = int(match.group(1)) & 0xFFFF
                rs = self.get_register(match.group(2), line_num, line)
                mc = (opcode << 26) | (rs << 21) | (rt << 16) | imm

            # LUI specific syntax -> expected: [instr, rt, imm]
            elif instr == "lui":
                self.check_operand_count(tokens, 3, line_num, line)
                rt = self.get_register(tokens[1], line_num, line)
                try:
                    imm = int(tokens[2], 0) & 0xFFFF  # supports hex formatting via base 0
                except ValueError:
                    print(f"| ERROR | Line {line_num}: Expected immediate integer/hex value, got '{tokens[2]}' instead.")
                    sys.exit(1)
                mc = (opcode << 26) | (0 << 21) | (rt << 16) | imm

            # Immediate operations -> expected: [instr, rt, rs, imm]
            elif instr in ["addi", "addiu", "andi", "ori", "xori", "slti", "sltiu"]:
                self.check_operand_count(tokens, 4, line_num, line)
                rt = self.get_register(tokens[1], line_num, line)
                rs = self.get_register(tokens[2], line_num, line)
                try:
                    imm = int(tokens[3], 0) & 0xFFFF
                except ValueError:
                    print(f"| ERROR | Line {line_num}: Expected immediate integer/hex value, got '{tokens[3]}' instead.")
                    sys.exit(1)
                mc = (opcode << 26) | (rs << 21) | (rt << 16) | imm

            # R-TYPE INSTRUCTIONS
            elif instr in self.functs:
                funct = self.functs[instr]
                rs = rt = rd = shamt = 0 
                
                # Shift logic -> expected: [instr, rd, rt, shamt]
                if instr in ["sll", "srl", "sra"]:
                    self.check_operand_count(tokens, 4, line_num, line)
                    rd = self.get_register(tokens[1], line_num, line)
                    rt = self.get_register(tokens[2], line_num, line)
                    try:
                        shamt = int(tokens[3]) & 0x1F
                    except ValueError:
                        print(f"| ERROR | Line {line_num}: Shift amount must be an integer, got '{tokens[3]}'")
                        sys.exit(1)
                
                # Mult/Div logic -> expected: [instr, rs, rt]
                elif instr in ["mult", "div"]:
                    self.check_operand_count(tokens, 3, line_num, line)
                    rs = self.get_register(tokens[1], line_num, line)
                    rt = self.get_register(tokens[2], line_num, line)
                
                # Move From logic -> expected: [instr, rd]
                elif instr in ["mfhi", "mflo"]:
                    self.check_operand_count(tokens, 2, line_num, line)
                    rd = self.get_register(tokens[1], line_num, line)
                
                # Jump Register logic -> expected: [instr, rs]
                elif instr == "jr":
                    self.check_operand_count(tokens, 2, line_num, line)
                    rs = self.get_register(tokens[1], line_num, line)
                    
                # Jump and Link Register -> expected: [instr, rd, rs]
                elif instr == "jalr":
                    self.check_operand_count(tokens, 3, line_num, line)
                    rd = self.get_register(tokens[1], line_num, line)
                    rs = self.get_register(tokens[2], line_num, line)
                
                # System Call -> expected: [instr]
                elif instr == "syscall":
                    self.check_operand_count(tokens, 1, line_num, line)

                # Standard R-Type logic -> expected: [instr, rd, rs, rt]
                else:
                    self.check_operand_count(tokens, 4, line_num, line)
                    rd = self.get_register(tokens[1], line_num, line)
                    rs = self.get_register(tokens[2], line_num, line)
                    rt = self.get_register(tokens[3], line_num, line)

                mc = (opcode << 26) | (rs << 21) | (rt << 16) | (rd << 11) | (shamt << 6) | funct

            self.machine_code.append(mc)

    def assemble(self, input_filepath, output_filepath):
        try:
            with open(input_filepath, 'r') as f:
                lines = f.readlines()
        except FileNotFoundError:
            print(f"| ERROR | File target path '{input_filepath}' does not exist.")
            sys.exit(1)
            
        cleaned_lines = self.pass_one(lines)
        self.pass_two(cleaned_lines)
        
        with open(output_filepath, 'w') as f:
            for mc in self.machine_code:
                f.write(f"0x{mc:08X}\n")
        print(f"Assembly complete! {len(self.machine_code)} instructions written to {output_filepath}")

if __name__ == "__main__":
    # Example usage: python mips_assembler.py ../programs/my_program.asm
    if len(sys.argv) < 2:
        print("Usage: python mips_assembler.py <path_to_asm_file> [optional_output_hex_path]")
        sys.exit(1)

    input_file = sys.argv[1]
    
    # If no output path is given, default to swapping .asm with .hex in the same directory
    if len(sys.argv) == 3:
        output_file = sys.argv[2]
    else:
        output_file = os.path.splitext(input_file)[0] + ".hex"

    print(f"Reading '{input_file}'...")
    assembler = MIPSAssembler()
    assembler.assemble(input_file, output_file)