# array_swap.asm
# Loads individual bytes, packs them into halfwords/words, and stores them back.

start:
    # 1. Initialize addresses in Data Memory
    addi $s0, $zero, 0       # Source base address = 0
    addi $s1, $zero, 16      # Destination base address = 16

    # 2. Write raw byte data using sb (Store Byte)
    addi $t0, $zero, 0x7F    # Positive max byte
    addi $t1, $zero, 0x8A    # Negative-signed byte (if interpreted as signed)
    sb   $t0, 0($s0)
    sb   $t1, 1($s0)

    # 3. Test sign-extension differences on load
    lb   $t2, 0($s0)         # Should load 0x0000007F
    lb   $t3, 1($s0)         # Should sign-extend 0x8A -> 0xFFFFFF8A
    lbu  $t4, 1($s0)         # Unsigned: Should load 0x0000008A

    # 4. Pack into a halfword and store
    sll  $t2, $t2, 8         # Shift byte
    or   $t5, $t2, $t4       # Combine bytes into a halfword
    sh   $t5, 0($s1)         # Store halfword to address 16

    # 5. Clean exit
    addi $v0, $zero, 10      # Exit Syscall
    syscall