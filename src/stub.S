/*
 * Start-up stub of a patched executable, run by the game's own PSLZ loader once the game is
 * unpacked: the PSLZ header's "jump" word (+0x18) points here instead of 0x80010000, and its
 * loader size (+0x14) is enlarged so that the loader's copy (to out_end + 1, free memory at
 * that time) includes this stub and the piece of the resident block that follows it.
 *
 *   COPY  (GTOS: first piece, GTMENU: second piece): copy the piece to COPY_DST.
 *   BOOT  (GTMENU, GTMAIN): if the whole resident block is there (magic + version at its
 *         start, second magic at its end), FlushCache, cheat_boot(EXE_ID) (redirects the
 *         game's calls), FlushCache again (as the loader does: critical section, A0:44).
 *   then jump to the game (0x80010000).
 */
    .set noreorder
    .set noat

    .macro flush
    li      $a0, 1                  /* EnterCriticalSection */
    syscall
    li      $t2, 0xA0               /* A0:44 FlushCache */
    jalr    $t2
    li      $t1, 0x44
    li      $a0, 2                  /* ExitCriticalSection */
    syscall
    .endm

    .text
    .globl _start
_start:
#if COPY
    lui     $t0, %hi(block)
    addiu   $t0, $t0, %lo(block)
    lui     $t1, %hi(COPY_DST)
    addiu   $t1, $t1, %lo(COPY_DST)
    li      $t2, COPY_WORDS
1:  lw      $t3, 0($t0)
    addiu   $t0, $t0, 4
    addiu   $t2, $t2, -1
    sw      $t3, 0($t1)
    bnez    $t2, 1b
    addiu   $t1, $t1, 4
#endif
#if BOOT
    lui     $t0, %hi(RESIDENT)
    lw      $t1, %lo(RESIDENT)($t0)
    lw      $t2, %lo(RESIDENT + 4)($t0)
    lui     $t5, %hi(END_MAGIC_AT)
    lw      $t5, %lo(END_MAGIC_AT)($t5)
    li      $t3, PAYLOAD_MAGIC
    li      $t6, END_MAGIC
    li      $t4, PAYLOAD_VERSION
    bne     $t1, $t3, 2f
    nop
    bne     $t2, $t4, 2f
    nop
    bne     $t5, $t6, 2f
    nop
    flush
    jal     CHEAT_BOOT
    li      $a0, EXE_ID
    flush
#endif
2:  lui     $t0, %hi(GAME_ENTRY)
    addiu   $t0, $t0, %lo(GAME_ENTRY)
    jr      $t0
    nop
    .balign 4
block:
