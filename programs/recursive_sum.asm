# recursive_sum.asm
# Computes the sum of numbers from N down to 1 recursively.

main:
    addi $a0, $zero, 10      # Set argument N = 10
    jal  sum_recursive       # Call function. $ra stores return address.
    
    # 1. Print Result Message / Integer
    add  $a0, $zero, $v0     # Move the final sum from $v0 to $a0 for printing
    addi $v0, $zero, 1       # Syscall 1: print_int
    syscall
    
    # 2. Clean Termination
    addi $v0, $zero, 10      # Syscall 10: exit
    syscall

sum_recursive:
    # Allocate space on the stack frame (8 bytes)
    addi $sp, $sp, -8
    sw   $ra, 4($sp)         # Store current Return Address
    sw   $a0, 0($sp)         # Store current argument N

    # Base Case: If N == 0, jump to base_case
    beq  $a0, $zero, base_case

    # Recursive Step: Compute sum_recursive(N - 1)
    addi $a0, $a0, -1        # N = N - 1
    jal  sum_recursive       # Nested function call

    # --- Pop Stack Values Back Upon Return ---
    lw   $a0, 0($sp)         # Restore N for this stack layer
    lw   $ra, 4($sp)         # Restore Return Address for this stack layer
    addi $sp, $sp, 8         # Deallocate stack frame

    add  $v0, $v0, $a0       # Return Value = sum_recursive(N-1) + N
    jr   $ra                 # Return up to the caller

base_case:
    addi $v0, $zero, 0       # sum(0) = 0
    addi $sp, $sp, 8         # Collapse stack frame for base layer
    jr   $ra                 # Jump back up to initiate unwinding