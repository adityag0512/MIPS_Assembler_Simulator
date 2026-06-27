# MIPS32 Assembler and Simulator

A Python implementation of a two-pass MIPS32 assembler and a Harvard architecture processor simulator.

---

## What this is

- You write MIPS assembly, run it through the assembler, and the simulator executes the resulting machine code - register by register, cycle by cycle. The whole toolchain lives in two Python files and has no dependencies outside the standard library.

- The assembler does a proper two-pass translation: the first pass walks the source to build a label table and calculate addresses, the second pass resolves every forward reference and encodes each instruction into its 32-bit binary representation. Errors - bad register names, unknown mnemonics, malformed memory offsets, duplicate labels - are caught at assembly time with the offending line number printed, not buried inside a runtime crash.

- The simulator models a Harvard architecture, meaning instruction memory and data memory are physically separate arrays. This isn't just an aesthetic choice; it means a `sw` can never overwrite your own program, and the fetch path is independent of the data path. 

---

## Supported instructions

**R-type** — `add`, `addu`, `sub`, `subu`, `and`, `or`, `xor`, `nor`, `slt`, `sltu`, `sll`, `srl`, `sra`, `mult`, `div`, `mfhi`, `mflo`, `jr`, `jalr`

**I-type** — `addi`, `addiu`, `andi`, `ori`, `xori`, `lui`, `slti`, `sltiu`, `beq`, `bne`, `lw`, `lh`, `lhu`, `lb`, `lbu`, `sw`, `sh`, `sb`, `ll`, `sc`

**J-type** — `j`, `jal`

**Syscalls** (via `syscall` with `$v0`) — `1` print integer, `11` print character, `10` exit

---

## Project layout

```
mips32-simulator/
├── assembler/
│   └── mips_assembler.py
├── simulator/
│   └── mips_simulator.py
├── programs/
│   └── add_sub.asm
|   └── array_swap.asm
|   └── branch_loop.asm
|   └── recursive_sum.asm
|   
└── README.md
```

The `programs/` folder is where you put `.asm` files. The assembler writes a `.hex` file next to them, and the simulator reads that hex file directly.

---

## Test  programs

The `programs/` directory contains standard test scripts designed to comprehensively exercise the entire ISA:

* **`add_sub.asm`**: Verifies foundational integer arithmetic (`add`, `sub`, `addi`), tests 32-bit signed wraparound boundaries, and checks that writes to `$zero` are safely ignored.
* **`array_swap.asm`**: Exercises partial-word memory access channels (`lb`, `lbu`, `lh`, `lhu`, `sb`, `sh`) by reading sub-word bytes, checking explicit sign extensions, and packing values back into aligned slots.
* **`branch_loop.asm`**: Implements an iterative summation from 1 to 10 to validate backward offset calculation for conditional branches (`bne`) and visible execution via integer printing (`syscall 1`).
* **`recursive_sum.asm`**: Computes a nested summation from 10 down to 1 to stress-test complex control flow jumps (`jal`, `jr`), runtime stack frame management via `$sp`, and program termination (`syscall 10`).


## Getting started

You need Python 3.8 or newer. No pip installs required.

**Step 1 - assemble your program**

```bash
python assembler/mips_assembler.py programs/array_swap.asm array_swap.hex
```

This produces `array_swap.hex`, one 32-bit word per line in hex.

**Step 2 - run the simulator**

```bash
python simulator/mips_simulator.py
```

You'll be prompted for the path to the `.hex` file. Type `array_swap.hex` and press enter.

---

## CLI commands

Once a program is loaded, you get a small interactive loop:

| Key | What it does |
|-----|-------------|
| `s` | Execute one instruction and print full CPU state |
| `r` | Run to completion (or until the next 1000-cycle checkpoint) |
| `d` | Dump current register file and non-zero data memory |
| `q` | Quit |

The state dump after every step shows all 32 registers in a grid, the HI/LO pair, the current PC, and every non-zero word in DMEM.

---

## Memory layout

| Region | Size | Notes |
|--------|------|-------|
| IMEM | 2048 bytes | Instructions only. PC starts at `0x00000000`. |
| DMEM | 4096 bytes | Data only. `$sp` initialised to top of DMEM. |

Byte, halfword, and word accesses all go through dedicated read/write functions with bounds checking. Reads from uninitialised addresses print a runtime error and return zero rather than crashing the process.

---

## Error handling

**At assembly time** - the assembler validates every line before emitting a single byte of machine code. It reports the exact line number and instruction context for: unknown mnemonics, invalid register names, wrong operand counts, malformed `offset(register)` syntax, undefined labels, and duplicate label definitions.

**At runtime** - the simulator reports unknown opcodes and funct codes, division by zero (silently skips the instruction per MIPS convention), out-of-bounds memory access, and unsupported syscall codes. Unknown instructions return an error and halt execution rather than silently skipping.

---

## Writing a program


Notes on syntax the assembler expects:
- Comments start with `#`
- Labels end with `:`
- Registers use the `$name` form - `$t0`, `$s1`, `$zero`, etc.
- Memory operands are written as `offset($register)` - e.g. `lw $t0, 4($sp)`
- Commas between operands are optional (stripped during tokenisation)

---

## Known limitations

- No `.data` section or assembler directives (`la`, `.word`, `.asciiz`). Static data has to be loaded via `lui`/`ori` pairs or written to DMEM at runtime.
- No pseudo-instruction expansion beyond what the assembler explicitly handles.
- IMEM is capped at 512 instructions (2048 bytes). For larger programs, increase `imem_size_bytes` when constructing `MIPSHardware`.
- No pipeline simulation - execution is single-cycle. One instruction completes fully before the next begins.