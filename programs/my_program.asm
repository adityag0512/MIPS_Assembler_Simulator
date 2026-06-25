# my_program.asm
start:
    addi $t0, $zero, 10   # Initialize loop counter to 10
    addi $t1, $zero, 0    # Initialize sum to 0

loop:
    beq  $t0, $zero, done # If counter == 0, jump to done
    add  $t1, $t1, $t0    # sum = sum + counter
    addi $t0, $t0, -1     # counter = counter - 1
    j    loop             # Repeat loop

done:
    sw   $t1, 0($sp)      # Store final sum in memory