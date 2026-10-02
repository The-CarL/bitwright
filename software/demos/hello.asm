; Load at 0300, run with 0300R. Standalone program uses fixed monitor ABI.
PUTC = $FFEF
GETC = $FE00
PROMPT = $FF03
.org $0300
start:
    LDX #0
print:
    LDA message,X
    BEQ wait_key
    JSR PUTC
    INX
    BNE print
wait_key:
    JSR GETC
    JSR PUTC
    LDA #$0D
    JSR PUTC
    JMP PROMPT
message:
    .byte "HELLO FROM A LOADED PROGRAM!", $0D, "PRESS A KEY: ", 0
