; Bitwright monitor: original implementation, not a copy of the Woz ROM.
; Apple-1-style command subset:
;   0300           examine one byte
;   0300.030F      examine an inclusive address range
;   0300: A9 41 60 store hexadecimal bytes
;   0300R          run at address (program returns with JMP $FF03)
; Command input folds ASCII lowercase to uppercase; program GETC stays raw.
; Backspace edits the pending line; ESC cancels it.
; 79-character input lines. Errors print '?'. RAM is 0000..0FFF.
; Zero page 20..27, stack 0100..01FF, input buffer 0200..024F reserved.
; Deposits reject those reserved regions and non-RAM before each byte write.
; A rejected byte ends the command; an earlier accepted prefix stays written.
; Public services preserve X/Y: FE00 getc, FE03 hex byte, FE06 newline,
; FFEF putc. Getc returns 7-bit ASCII; putc accepts it, waits for display.
; FE03 preserves processor flags, including decimal mode. Monitor entry clears D.
KBD = $D010
KBDCR = $D011
DSP = $D012
DSPCR = $D013
PTR = $20
LIMIT = $22
VALUE = $24
DIGITS = $26
NIBBLE = $27
LINE = $0200

.org $F000
reset:
    CLD
    SEI
    LDX #$FF
    TXS
    LDA #$A7
    STA KBDCR
    STA DSPCR
    LDX #0
banner_loop:
    LDA banner,X
    BEQ prompt
    JSR putc
    INX
    BNE banner_loop
prompt:
    CLD
    LDX #$FF
    TXS
    JSR newline
    LDA #'\\'
    JSR putc
    LDA #' '
    JSR putc
    LDX #0
line_loop:
    JSR getc
    ; Printable input is the common path during assembly-file loading.
    CMP #' '
    BCC control_key
    CMP #$7F
    BEQ backspace
    CPX #79
    BCS line_loop
    CMP #'a'
    BCC command_char
    CMP #'z'+1
    BCS command_char
    AND #$5F
command_char:
    STA LINE,X
    INX
echo_line_char:
    BIT DSP
    BMI echo_line_char
    STA DSP
    JMP line_loop
control_key:
    CMP #$1B
    BEQ prompt
    CMP #$08
    BEQ backspace
    CMP #$0D
    BEQ line_done
    CMP #$0A
    BEQ line_done
    JMP line_loop
backspace:
    CPX #0
    BEQ line_loop
    DEX
    LDA #$08
    JSR putc
    JMP line_loop
line_done:
    LDA #0
    STA LINE,X
    JSR newline
    LDY #0
    LDX #0                  ; (PTR,X) stores preserve the parser index Y.
    JSR spaces
    LDA LINE,Y
    BEQ prompt
    JSR read_hex
    BCC parse_error
    LDA VALUE
    STA PTR
    LDA VALUE+1
    STA PTR+1
    JSR spaces
    LDA LINE,Y
    BEQ examine_one
    CMP #':'
    BEQ store_loop
    CMP #'R'
    BEQ run_program
    CMP #'.'
    BEQ examine_range
parse_error:
    LDA #'?'
    JSR putc
    JMP prompt
run_program:
    INY
    JSR spaces
    LDA LINE,Y
    BNE parse_error
    JMP (PTR)
examine_one:
    LDA PTR
    STA LIMIT
    LDA PTR+1
    STA LIMIT+1
    JMP dump_loop
examine_range:
    INY
    JSR read_hex
    BCC parse_error
    LDA VALUE
    STA LIMIT
    LDA VALUE+1
    STA LIMIT+1
    JSR spaces
    LDA LINE,Y
    BNE parse_error
    LDA LIMIT
    CMP PTR
    LDA LIMIT+1
    SBC PTR+1
    BCC parse_error
    JMP dump_loop
store_loop:
    INY
    JSR spaces
    LDA LINE,Y
    BEQ store_done
    JSR read_byte
    BCC parse_error
    ; Common program RAM is 0300..0FFF; low RAM needs workspace protection.
    LDA PTR+1
    CMP #$03
    BCC store_low
    CMP #$10
    BCS parse_error
store_valid:
    LDA VALUE
deposit_byte:
    STA (PTR,X)
    INC PTR
    BNE store_advanced
    INC PTR+1
store_advanced:
    LDA LINE,Y
    BEQ store_done
    CMP #' '
    BEQ store_loop
    JMP parse_error
store_low:
    JSR valid_store
    BCS store_valid
    JMP parse_error
store_done:
    JMP prompt
dump_loop:
    LDA PTR+1
    JSR puthex
    LDA PTR
    JSR puthex
    LDA #':'
    JSR putc
    LDA #' '
    JSR putc
    LDY #0
    LDA (PTR),Y
    JSR puthex
    JSR newline
    LDA PTR
    CMP LIMIT
    BNE dump_next
    LDA PTR+1
    CMP LIMIT+1
    BEQ store_done
dump_next:
    JSR inc_ptr
    JMP dump_loop
inc_ptr:
    INC PTR
    BNE inc_done
    INC PTR+1
inc_done:
    RTS
valid_store:
    LDA PTR+1
    CMP #$10
    BCS store_rejected
    CMP #$01
    BEQ store_rejected
    CMP #$02
    BNE store_zero_page
    LDA PTR
    CMP #$50
    BCC store_rejected
    BCS store_allowed
store_zero_page:
    CMP #$00
    BNE store_allowed
    LDA PTR
    CMP #$20
    BCC store_allowed
    CMP #$28
    BCC store_rejected
store_allowed:
    SEC
    RTS
store_rejected:
    CLC
    RTS
spaces:
    LDA LINE,Y
    CMP #' '
    BNE spaces_done
    INY
    BNE spaces
spaces_done:
    RTS
read_hex:
    JSR spaces
read_hex_nospace:
    LDA #0
    STA VALUE
    STA VALUE+1
    STA DIGITS
hex_loop:
    LDA LINE,Y
    CMP #'0'
    BCC hex_end
    CMP #':'
    BCC decimal_digit
    CMP #'A'
    BCC hex_end
    CMP #'G'
    BCS hex_end
    SEC
    SBC #'A'-10
    JMP digit_ready
decimal_digit:
    SEC
    SBC #'0'
digit_ready:
    STA NIBBLE
    INC DIGITS
    LDA DIGITS
    CMP #5
    BCS hex_fail
    LDA VALUE
    ASL A
    ROL VALUE+1
    ASL A
    ROL VALUE+1
    ASL A
    ROL VALUE+1
    ASL A
    ROL VALUE+1
    ORA NIBBLE
    STA VALUE
    INY
    BNE hex_loop
hex_end:
    LDA DIGITS
    BEQ hex_fail
    SEC
    RTS
hex_fail:
    CLC
    RTS
read_byte:
    ; Deposits only need eight result bits. Accept the same one-to-four hex
    ; digits as read_hex (including leading zeros), but reject overflow before
    ; truncation. X counts digits locally and is restored to zero for (PTR,X).
    LDX #0
    LDA #0
    STA VALUE
byte_loop:
    LDA LINE,Y
    CMP #'0'
    BCC byte_end
    CMP #':'
    BCC byte_decimal
    CMP #'A'
    BCC byte_end
    CMP #'G'
    BCS byte_end
    SEC
    SBC #'A'-10
    JMP byte_digit
byte_decimal:
    SEC
    SBC #'0'
byte_digit:
    STA NIBBLE
    INX
    CPX #5
    BCS byte_fail
    LDA VALUE
    CMP #$10
    BCS byte_fail
    ASL A
    ASL A
    ASL A
    ASL A
    ORA NIBBLE
    STA VALUE
    INY
    BNE byte_loop
byte_end:
    CPX #0
    BEQ byte_fail
    LDX #0
    SEC
    RTS
byte_fail:
    LDX #0
    CLC
    RTS
getc:
    LDA KBDCR
    BPL getc
    LDA KBD
    AND #$7F
    RTS
putc:
    BIT DSP
    BMI putc
    STA DSP
    RTS
newline:
    LDA #$0D
    JMP putc
puthex:
    PHP
    CLD
    PHA
    LSR A
    LSR A
    LSR A
    LSR A
    JSR putnibble
    PLA
    AND #$0F
    JSR putnibble
    PLP
    RTS
putnibble:
    CMP #10
    BCC putdigit
    CLC
    ADC #'A'-10
    JMP putc
putdigit:
    CLC
    ADC #'0'
    JMP putc
banner:
    .byte "BITWRIGHT 6502", $0D, "ADDR  ADDR.END  ADDR: BYTES  ADDRR", 0

.org $FE00
    JMP getc
    JMP puthex
    JMP newline
.org $FF00
    JMP reset
    JMP prompt
.org $FFEF
    JMP putc
.org $FFFA
    .word reset, $FF00, reset
