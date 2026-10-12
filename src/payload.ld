SECTIONS
{
    . = 0x8000F000;
    .text : {
        KEEP(*(.text.start))
        *(.text .text.*)
        __code_end = .;
        *(.rodata .rodata.*)
        *(.data .data.* .sdata .sdata.*)
        . = ALIGN(4);
    }
    .bss : { *(.bss .bss.* .sbss .sbss.* COMMON) }
    /DISCARD/ : { *(.comment) *(.pdr) *(.reginfo) *(.MIPS.abiflags) *(.gnu.attributes) *(.note*) }
}
