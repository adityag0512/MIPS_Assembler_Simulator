# branch_loop.asm
# Uses a loop to sum integers from 1 to 10.
# Expected result: 1+2+3+4+5+6+7+8+9+10 = 55
#
# This validates:
#   - beq / bne branch offset calculation (backward jump)
#   - That the loop body runs exactly 10 times, not 9 or 11
#   - syscall 1 (print_int) to confirm the result visibly

start:
    # 1. Initialise registers
    addi $t0, $zero, 0          # $t0 = counter, starts at 0
    addi $t1, $zero, 0          # $t1 = running sum
    addi $t2, $zero, 10         # $t2 = loop limit

loop:
    # 2. Add current counter value to sum
    add  $t1, $t1, $t0          # sum += counter

    # 3. Increment counter
    addi $t0, $t0, 1            # counter++

    # 4. If counter <= 10, keep looping
    #    We do this as: if counter != limit+1, loop back
    #    i.e. loop while $t0 <= 10 -> exit when $t0 == 11
    addi $t3, $zero, 11         # $t3 = 11 (the exit sentinel)
    bne  $t0, $t3, loop         # if counter != 11, go back to loop

done:
    # 5. Print the result (should print 55)
    addi $v0, $zero, 1          # syscall 1 = print_int
    add  $a0, $t1, $zero        # argument = sum
    syscall

    # 6. Clean exit
    addi $v0, $zero, 10         # Exit syscall
    syscall