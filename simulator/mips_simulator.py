import sys
import os

def to_signed_32(val):
    val = val & 0xFFFFFFFF
    return val - 0x100000000 if val & 0x80000000 else val

def to_unsigned_32(val):
    return val & 0xFFFFFFFF

class MIPSHardware:
    def __init__(self, imem_size_bytes=2048, dmem_size_bytes=4096):
        self.registers = [0] * 32
        self.hi = 0
        self.lo = 0
        self.pc = 0x00000000
        
        self.imem = bytearray(imem_size_bytes) 
        self.dmem = bytearray(dmem_size_bytes) 
        self.instruction_limit = 0  
        
        self.reg_names = [
            "$zero", "$at", "$v0", "$v1", "$a0", "$a1", "$a2", "$a3",
            "$t0",   "$t1", "$t2", "$t3", "$t4", "$t5", "$t6", "$t7",
            "$s0",   "$s1", "$s2", "$s3", "$s4", "$s5", "$s6", "$s7",
            "$t8",   "$t9", "$k0", "$k1", "$gp", "$sp", "$fp", "$ra"
        ]
        
        self.registers[29] = dmem_size_bytes - 4

    def load_program(self, hex_filepath):
        if not os.path.exists(hex_filepath):
            print(f"Error: Machine code file '{hex_filepath}' not found.")
            return False
            
        address = 0
        with open(hex_filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if not line: continue
                instr_value = int(line, 16)
                
                if address + 3 >= len(self.imem):
                    print(f"Error: Program size exceeds IMEM capacity.")
                    return False
                
                self.imem[address]     = (instr_value >> 24) & 0xFF
                self.imem[address + 1] = (instr_value >> 16) & 0xFF
                self.imem[address + 2] = (instr_value >> 8) & 0xFF
                self.imem[address + 3] = instr_value & 0xFF
                address += 4
                
        self.instruction_limit = address
        self.pc = 0x00000000
        print(f"Loaded {address // 4} instructions into IMEM.")
        return True

    def read_instruction(self, address):
        if address + 3 >= len(self.imem) or address < 0:
            print(f"Runtime Error: Instruction Fetch Out of Bounds at 0x{address:08X}")
            return 0
        return (self.imem[address] << 24) | (self.imem[address + 1] << 16) | \
               (self.imem[address + 2] << 8) | self.imem[address + 3]

    def read_data_word(self, address):
        if address + 3 >= len(self.dmem) or address < 0:
            print(f"Runtime Error: DMEM Read (Word) Out of Bounds at 0x{address:08X}")
            return 0
        return (self.dmem[address] << 24) | (self.dmem[address + 1] << 16) | \
               (self.dmem[address + 2] << 8) | self.dmem[address + 3]

    def read_data_halfword(self, address):
        if address + 1 >= len(self.dmem) or address < 0:
            print(f"Runtime Error: DMEM Read (Halfword) Out of Bounds at 0x{address:08X}")
            return 0
        return (self.dmem[address] << 8) | self.dmem[address + 1]

    def read_data_byte(self, address):
        if address >= len(self.dmem) or address < 0:
            print(f"Runtime Error: DMEM Read (Byte) Out of Bounds at 0x{address:08X}")
            return 0
        return self.dmem[address]

    def write_data_word(self, address, value):
        if address + 3 >= len(self.dmem) or address < 0:
            print(f"Runtime Error: DMEM Write (Word) Out of Bounds at 0x{address:08X}")
            return
        value = to_unsigned_32(value)
        self.dmem[address]     = (value >> 24) & 0xFF
        self.dmem[address + 1] = (value >> 16) & 0xFF
        self.dmem[address + 2] = (value >> 8) & 0xFF
        self.dmem[address + 3] = value & 0xFF

    def write_data_halfword(self, address, value):
        if address + 1 >= len(self.dmem) or address < 0:
            print(f"Runtime Error: DMEM Write (Halfword) Out of Bounds at 0x{address:08X}")
            return
        self.dmem[address]     = (value >> 8) & 0xFF
        self.dmem[address + 1] = value & 0xFF

    def write_data_byte(self, address, value):
        if address >= len(self.dmem) or address < 0:
            print(f"Runtime Error: DMEM Write (Byte) Out of Bounds at 0x{address:08X}")
            return
        self.dmem[address] = value & 0xFF

    def set_register(self, reg_idx, value):
        if reg_idx != 0:
            self.registers[reg_idx] = to_unsigned_32(value)

    def print_state(self):
        print("\n" + "="*55)
        print(f"  CPU STATE   [ PC: 0x{self.pc:08X} ]")
        print(f"  HI: 0x{self.hi:08X}   LO: 0x{self.lo:08X}")
        print("="*55)
        
        for i in range(0, 32, 4):
            reg_strs = []
            for j in range(4):
                idx = i + j
                reg_strs.append(f"{self.reg_names[idx]:<6}: 0x{self.registers[idx]:08X}")
            print("  ".join(reg_strs))
            
        print("-"*55)
        print("  DATA MEMORY (DMEM Non-zero entries):")
        has_data = False
        for addr in range(0, len(self.dmem), 4):
            val = self.read_data_word(addr)
            if val != 0:
                print(f"  DMEM Addr [0x{addr:03X}]: 0x{val:08X}")
                has_data = True
        if not has_data:
            print("  [All data memory locations are 0x00000000]")
        print("="*55 + "\n")


class SIMCore:
    def __init__(self, hardware):
        self.cpu = hardware

    def execute_single_cycle(self):
        if self.cpu.pc >= self.cpu.instruction_limit:
            return False

        instruction = self.cpu.read_instruction(self.cpu.pc)
        
        opcode = (instruction >> 26) & 0x3F
        rs = (instruction >> 21) & 0x1F
        rt = (instruction >> 16) & 0x1F
        rd = (instruction >> 11) & 0x1F
        shamt = (instruction >> 6) & 0x1F
        funct = instruction & 0x3F
        imm = instruction & 0xFFFF
        
        imm_signed = imm if not (imm & 0x8000) else imm - 0x10000
        imm_unsigned = imm

        pc_modified = False

        if opcode == 2:    # j
            self.cpu.pc = (self.cpu.pc & 0xF0000000) | ((instruction & 0x3FFFFFF) << 2)
            pc_modified = True
        elif opcode == 3:  # jal
            self.cpu.set_register(31, self.cpu.pc + 4)
            self.cpu.pc = (self.cpu.pc & 0xF0000000) | ((instruction & 0x3FFFFFF) << 2)
            pc_modified = True

        elif opcode == 0:
            rs_val_u = self.cpu.registers[rs]
            rt_val_u = self.cpu.registers[rt]
            rs_val_s = to_signed_32(rs_val_u)
            rt_val_s = to_signed_32(rt_val_u)

            if funct == 0:    # sll
                self.cpu.set_register(rd, rt_val_u << shamt)
            elif funct == 2:  # srl
                self.cpu.set_register(rd, rt_val_u >> shamt)
            elif funct == 3:  # sra
                self.cpu.set_register(rd, rt_val_s >> shamt)
            elif funct == 8:  # jr
                self.cpu.pc = rs_val_u
                pc_modified = True
            elif funct == 9:  # jalr
                self.cpu.set_register(rd, self.cpu.pc + 4)
                self.cpu.pc = rs_val_u
                pc_modified = True
            elif funct == 12: # syscall
                v0 = self.cpu.registers[2]
                if v0 == 1: # print integer
                    print(to_signed_32(self.cpu.registers[4]), end="", flush=True)
                elif v0 == 10: # exit cleanly
                    self.cpu.pc += 4
                    print("\n[Syscall] Program terminated normally.")
                    return False
                elif v0 == 11: # print character
                    print(chr(self.cpu.registers[4] & 0xFF), end="", flush=True)
                else:
                    print(f"\n[!] RUNTIME ERROR: Unsupported Syscall {v0}")
                    return False
            elif funct == 16: # mfhi
                self.cpu.set_register(rd, self.cpu.hi)
            elif funct == 18: # mflo
                self.cpu.set_register(rd, self.cpu.lo)
            elif funct == 24: # mult
                res = rs_val_s * rt_val_s
                self.cpu.lo = to_unsigned_32(res)
                self.cpu.hi = to_unsigned_32(res >> 32)
            elif funct == 26: # div
                if rt_val_s != 0:
                    self.cpu.lo = to_unsigned_32(int(rs_val_s / rt_val_s))
                    self.cpu.hi = to_unsigned_32(rs_val_s - (to_signed_32(self.cpu.lo) * rt_val_s))
            elif funct == 32: # add
                self.cpu.set_register(rd, rs_val_s + rt_val_s)
            elif funct == 33: # addu
                self.cpu.set_register(rd, rs_val_u + rt_val_u)
            elif funct == 34: # sub
                self.cpu.set_register(rd, rs_val_s - rt_val_s)
            elif funct == 35: # subu
                self.cpu.set_register(rd, rs_val_u - rt_val_u)
            elif funct == 36: # and
                self.cpu.set_register(rd, rs_val_u & rt_val_u)
            elif funct == 37: # or
                self.cpu.set_register(rd, rs_val_u | rt_val_u)
            elif funct == 38: # xor
                self.cpu.set_register(rd, rs_val_u ^ rt_val_u)
            elif funct == 39: # nor
                self.cpu.set_register(rd, ~(rs_val_u | rt_val_u))
            elif funct == 42: # slt
                self.cpu.set_register(rd, 1 if rs_val_s < rt_val_s else 0)
            elif funct == 43: # sltu
                self.cpu.set_register(rd, 1 if rs_val_u < rt_val_u else 0)
            else:
                print(f"\n[!] RUNTIME ERROR: Unknown R-Type Funct Code: {funct}")
                return False

        else:
            rs_val_u = self.cpu.registers[rs]
            rs_val_s = to_signed_32(rs_val_u)
            rt_val_u = self.cpu.registers[rt]

            if opcode == 4:   # beq
                if rs_val_u == rt_val_u:
                    self.cpu.pc = self.cpu.pc + 4 + (imm_signed << 2)
                    pc_modified = True
            elif opcode == 5: # bne
                if rs_val_u != rt_val_u:
                    self.cpu.pc = self.cpu.pc + 4 + (imm_signed << 2)
                    pc_modified = True
            elif opcode == 8: # addi
                self.cpu.set_register(rt, rs_val_s + imm_signed)
            elif opcode == 9: # addiu
                self.cpu.set_register(rt, rs_val_u + imm_signed)
            elif opcode == 10: # slti
                self.cpu.set_register(rt, 1 if rs_val_s < imm_signed else 0)
            elif opcode == 11: # sltiu
                self.cpu.set_register(rt, 1 if rs_val_u < to_unsigned_32(imm_signed) else 0)
            elif opcode == 12: # andi
                self.cpu.set_register(rt, rs_val_u & imm_unsigned)
            elif opcode == 13: # ori
                self.cpu.set_register(rt, rs_val_u | imm_unsigned)
            elif opcode == 14: # xori
                self.cpu.set_register(rt, rs_val_u ^ imm_unsigned)
            elif opcode == 15: # lui
                self.cpu.set_register(rt, imm_unsigned << 16)
            
            # --- DMEM OPERATIONS ---
            elif opcode in [32, 33, 35, 36, 37, 40, 41, 43, 48, 56]: 
                addr = to_unsigned_32(rs_val_s + imm_signed)
                
                if opcode == 35 or opcode == 48: # lw / ll
                    self.cpu.set_register(rt, self.cpu.read_data_word(addr))
                elif opcode == 43: # sw
                    self.cpu.write_data_word(addr, rt_val_u)
                elif opcode == 56: # sc 
                    self.cpu.write_data_word(addr, rt_val_u)
                    self.cpu.set_register(rt, 1)
                elif opcode == 32: # lb
                    b = self.cpu.read_data_byte(addr)
                    self.cpu.set_register(rt, b if not (b & 0x80) else b - 0x100)
                elif opcode == 36: # lbu
                    self.cpu.set_register(rt, self.cpu.read_data_byte(addr))
                elif opcode == 40: # sb
                    self.cpu.write_data_byte(addr, rt_val_u)
                elif opcode == 33: # lh
                    hw = self.cpu.read_data_halfword(addr)
                    self.cpu.set_register(rt, hw if not (hw & 0x8000) else hw - 0x10000)
                elif opcode == 37: # lhu
                    self.cpu.set_register(rt, self.cpu.read_data_halfword(addr))
                elif opcode == 41: # sh
                    self.cpu.write_data_halfword(addr, rt_val_u)
            else:
                print(f"\n[!] RUNTIME ERROR: Unknown Opcode: {opcode}")
                return False

        if not pc_modified:
            self.cpu.pc += 4
            
        return True

def main():
    print("MIPS32 CLI Simulator Initialization")
    
    if len(sys.argv) < 2:
        print("\n| ERROR | No input file specified.")
        print("Usage: python mips_simulator.py <path_to_compiled_hex_file>")
        sys.exit(1)
        
    hex_file = sys.argv[1]
    hw = MIPSHardware()
    sim = SIMCore(hw)
    
    print(f"Loading machine code file: '{hex_file}'")
        
    # Attempt to load the program into IMEM
    if not hw.load_program(hex_file):
        print("Initialization failed. Exiting.")
        sys.exit(1)

    hw.print_state()

    while True:
        cmd = input("Commands: [s] Step | [r] Run | [d] Dump state | [q] Quit \n> ").strip().lower()

        if cmd == 's':
            if not sim.execute_single_cycle():
                print("Program execution halted (Reached end of instructions or hit exit syscall).")
            hw.print_state()
                
        elif cmd == 'r':
            steps = 0
            MAX_STEPS = 1000
            while sim.execute_single_cycle():
                steps += 1
                if steps >= MAX_STEPS:
                    print(f"\n[!] WARNING: Execution paused after {MAX_STEPS} cycles to prevent infinite loops.")
                    print("    Type 'r' again to resume for another 1000 cycles.")
                    break
            
            if steps < MAX_STEPS:
                print(f"\nProgram finished in {steps} cycles.")
            hw.print_state()
            
        elif cmd == 'd':
            hw.print_state()
            
        elif cmd == 'q':
            print("Exiting simulator.")
            break
        else:
            print("Unknown command.")

if __name__ == "__main__":
    main()
