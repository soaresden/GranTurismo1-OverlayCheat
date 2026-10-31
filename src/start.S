/* First words of the resident block (0x8000F000): GTMAIN's stub checks them before calling
   cheat_boot, so that it never jumps into whatever else could be in low RAM. */
    .section .text.start, "ax"
    .globl _start
_start:
    .word PAYLOAD_MAGIC
    .word PAYLOAD_VERSION
    .word 0                     /* options (OPTIONS of cheat.c): written by gt1cheat/patcher.py */
