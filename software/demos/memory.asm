; Fill a 16-byte RAM area, checksum it through a separate subroutine, print 78.
; Distinct program uses indirect-indexed access, indexed stores and CPU RAM.
PUTC = $FFEF
PUTHEX = $FE03
NEWLINE = $FE06
PROMPT = $FF03
PTR = $0082
BUFFER = $0800
.org $0300
start:
    CLD
    LDX #0
fill:
    TXA
    STA BUFFER,X
    INX
    CPX #16
    BNE fill
    LDA #<BUFFER
    STA PTR
    LDA #>BUFFER
    STA PTR+1
    JSR checksum
    PHA
    LDX #0
print:
    LDA message,X
    BEQ result
    JSR PUTC
    INX
    BNE print
result:
    PLA
    JSR PUTHEX
    JSR NEWLINE
    JMP PROMPT
checksum:
    LDA #0
    LDY #0
sum_loop:
    CLC
    ADC (PTR),Y
    INY
    CPY #16
    BNE sum_loop
    RTS
message:
    .byte "RAM CHECKSUM (HEX) = ",0
