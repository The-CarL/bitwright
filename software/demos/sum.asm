; Read a digit 0..9, sum 1..N with a loop, and print the hexadecimal result.
; Example input 9 => 2D (45 decimal). Uses RAM and nested calls on the CPU stack.
PUTC = $FFEF
GETC = $FE00
PUTHEX = $FE03
NEWLINE = $FE06
PROMPT = $FF03
TOTAL = $0080
COUNT = $0081
.org $0300
start:
    CLD
    LDX #0
ask_loop:
    LDA question,X
    BEQ read_digit
    JSR PUTC
    INX
    BNE ask_loop
read_digit:
    JSR GETC
    CMP #'0'
    BCC read_digit
    CMP #':'
    BCS read_digit
    JSR PUTC
    SEC
    SBC #'0'
    STA COUNT
    JSR accumulate
    JSR NEWLINE
    LDX #0
result_loop:
    LDA result,X
    BEQ print_total
    JSR PUTC
    INX
    BNE result_loop
print_total:
    LDA TOTAL
    JSR PUTHEX
    JSR NEWLINE
    JMP PROMPT
accumulate:
    LDA #0
    STA TOTAL
    LDX COUNT
    BEQ accumulate_done
sum_loop:
    TXA
    CLC
    ADC TOTAL
    STA TOTAL
    DEX
    BNE sum_loop
accumulate_done:
    RTS
question:
    .byte "SUM 1..N. DIGIT 0-9: ",0
result:
    .byte "SUM (HEX) = ",0
