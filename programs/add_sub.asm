# add_sub_basic.asm
# Tests core integer arithmetic: add, sub, addi, and 32-bit signed wraparound.
# Also verifies that writing to $zero has no effect.

start:
    # 1. Basic addition
    addi $t0, $zero, 15         # $t0 = 15
    addi $t1, $zero, 10         # $t1 = 10
    add  $t2, $t0, $t1          # $t2 = 15 + 10 = 25

    # 2. Basic subtraction
    sub  $t3, $t0, $t1          # $t3 = 15 - 10 = 5

    # 3. Subtraction producing a negative result
    sub  $t4, $t1, $t0          # $t4 = 10 - 15 = -5 -> should show 0xFFFFFFFB

    # 4. Adding a negative immediate (sign-extended)
    addi $t5, $zero, -7         # $t5 = -7 -> should show 0xFFFFFFF9

    # 5. Negative + positive cancelling out
    add  $t6, $t4, $t0          # $t6 = -5 + 15 = 10

    # 6. The $zero register must always read as 0, even after an attempted write
    addi $zero, $zero, 99       # Attempt to write 99 into $zero (must be ignored)
    add  $t7, $zero, $t1        # $t7 = 0 + 10 = 10  (proves $zero is still 0)

    # 7. Clean exit
    addi $v0, $zero, 10         # Exit syscall
    syscall