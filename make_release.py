"""Make the test disc and the patches (needs gt1cheat/payload.py: python build.py).

    python make_release.py --src "Gran Turismo [SCES_009.84].chd" --test "TEST_CHEAT"
    python make_release.py --src "Gran Turismo [SCES_009.84].chd" --patches

--test DIR   DIR/Gran Turismo [Cheat].bin/.cue + LISEZMOI.txt (stock game + cheat)
--patches    patch/Gran Turismo (Europe) [Overlay Cheat].ppf, computed from the changed
             sectors only, and the .xdelta (xdelta3, from build/orig.bin and build/cheat.bin,
             both written there, not published)
Before writing anything: the static checks of gt1cheat/check.py on the three executables.
"""
import argparse
import glob
import hashlib
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
from gt1cheat import check, disc, exes, patcher, payload, ppf  # noqa: E402

STEM = 'Gran Turismo (Europe) [Overlay Cheat]'
TEST_NAME = 'Gran Turismo [Cheat].bin'

LISEZMOI = """Gran Turismo (PS1, PAL SCES-00984) — menu de triche en surimpression
=====================================================================

Disque de TEST : le jeu d'origine + la triche (aucune autre modification).
Ouvrir « Gran Turismo [Cheat].cue » dans DuckStation (ou RetroArch / Beetle PSX),
avec un BIOS PAL, et partir d'un démarrage du disque (pas d'une sauvegarde d'état
faite avec le jeu non modifié : elle ne contient pas la triche).

Commandes (manette 1)
---------------------
Deux façons d'ouvrir le petit menu « GT1 CHEAT », en haut de l'écran :
  - maintenir SELECT : le menu apparaît après un court instant et disparaît
    quand on relâche ;
  - appuyer L1 + R1 + L2 + R2 ensemble : le menu s'ouvre et reste ouvert ;
    START (ou les quatre gâchettes à nouveau) le referme. À utiliser dans
    RetroArch / Batocera, où SELECT est souvent la touche « hotkey ».
Tant que le menu est ouvert, le jeu ne reçoit plus la manette (en course, la
voiture continue sur sa lancée).

  Haut / Bas                choisir la ligne

  Ligne FREEZE TIMER (chrono des permis) :
    Gauche / Droite / Croix / Rond    ON / OFF
    ON : dans un permis, le chronomètre s'arrête. S'il était déjà ON au départ,
    il s'arrête à 0:00.040, juste après le départ (un permis dont le chrono
    reste à 0 ne se termine jamais).

  Ligne MONEY (crédits, changés tout de suite) :
    Droite / Gauche           + / - le pas (maintenu : répétition)
    R1 / L1                   pas x10 / pas ÷10 (de 1 à 10 000 000)
    Triangle                  99 999 999 (le maximum du jeu)
    Carré                     0

Un appui bref sur SELECT (sans autre touche) est rendu au jeu quand on le relâche.

Le choix FREEZE TIMER est gardé d'un écran à l'autre (jusqu'à l'extinction).
Le menu marche dans les menus du jeu (carte, garage, concessionnaires…) et en
course / en permis. Il n'apparaît qu'une fois le mode Gran Turismo ouvert au
moins une fois depuis l'allumage (pas dans la démo du début, ni sur l'écran
titre, ni dans les menus du mode Arcade ; les courses Arcade l'ont ensuite).

Essayé dans PCSX-Redux (BIOS SCPH-5502) : menu sur la carte et en permis, argent
mis à jour à l'écran, permis B-1 avec FREEZE TIMER ON : « YOU WIN GOLD », 0:00.059.

À tester dans DuckStation
-------------------------
1. Démarrer le .cue, aller jusqu'à la carte de la ville, maintenir SELECT :
   le menu doit apparaître, lisible, sans scintiller.
2. MONEY : Droite / R1 / Triangle, relâcher SELECT : l'argent affiché en bas
   (licences, concessionnaire) doit avoir changé ; acheter une voiture.
3. FREEZE TIMER ON, puis un permis : le chrono reste à 0:00.040 ; réussir le
   permis (médaille), le temps doit être enregistré.
4. Revenir aux menus après le permis : SELECT doit toujours ouvrir le menu, et
   FREEZE TIMER doit être resté ON.
5. Changer l'argent pendant un permis (menu SELECT), sortir : vérifier l'argent.
6. L1 + R1 + L2 + R2 sur la carte : le menu reste ouvert sans rien tenir ;
   START le referme.
7. Sauvegarder sur la carte mémoire, éteindre, recharger : rien d'anormal.
"""


def tool(pattern, name):
    dirs = [os.path.join(ROOT, 'tools', 'xdelta'), r'D:\DOCS\Documents\GitHub\Resident Evil 1 Hotkey\tools\xdelta']
    for d in dirs:
        hits = glob.glob(os.path.join(d, pattern))
        if hits:
            return hits[0]
    return shutil.which(name)


def sha1_file(path):
    h = hashlib.sha1()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', required=True, help='stock disc (.chd, .cue, .bin)')
    ap.add_argument('--test', help='folder of the test disc')
    ap.add_argument('--patches', action='store_true')
    a = ap.parse_args()

    d = disc.Disc(a.src)
    new, problems = {}, []
    for name in exes.EXES:
        orig = d.read(name)
        new[name] = patcher.patch_exe(name, orig)
        problems += check.check_exe(name, orig, new[name], payload)
    if problems:
        sys.exit('check.py:\n  ' + '\n  '.join(problems))
    print('executables patched and checked: %s' % ', '.join(exes.EXES))
    prog = lambda i, n: print('\r  %3d %%' % (100 * i // n), end='', flush=True)

    if a.test:
        os.makedirs(a.test, exist_ok=True)
        out = os.path.join(a.test, TEST_NAME)
        d.write_bin(out, new, prog)
        open(os.path.join(a.test, 'LISEZMOI.txt'), 'w', encoding='utf-8-sig', newline='\r\n').write(LISEZMOI)
        print('\rtest disc: %s (+ .cue, LISEZMOI.txt) sha1 %s' % (out, sha1_file(out)))

    if a.patches:
        os.makedirs(os.path.join(ROOT, 'patch'), exist_ok=True)
        changes = []
        for name, data in new.items():
            lba = d.files[name][0]
            for i in range((len(data) + 2047) // 2048):
                old = d.c.sector(lba + i)
                sec = disc.make_sector(old, data[i * 2048:(i + 1) * 2048])
                if sec != old:
                    changes.append(((lba + i) * disc.SECTOR, old, sec))
        pp = ppf.make(changes, 'Gran Turismo PAL - overlay cheat v%08X' % payload.VERSION)
        ppf_path = os.path.join(ROOT, 'patch', STEM + '.ppf')
        open(ppf_path, 'wb').write(pp)
        print('PPF: %s (%d bytes, %d sectors)' % (ppf_path, len(pp), len(changes)))
        build = os.path.join(ROOT, 'build')
        os.makedirs(build, exist_ok=True)
        orig_bin, cheat_bin = os.path.join(build, 'orig.bin'), os.path.join(build, 'cheat.bin')
        if not os.path.exists(orig_bin):
            d.write_bin(orig_bin, {}, prog)
        d.write_bin(cheat_bin, new, prog)
        print('\rorig.bin sha1 %s, cheat.bin sha1 %s' % (sha1_file(orig_bin), sha1_file(cheat_bin)))
        # the PPF applied to orig.bin must give cheat.bin
        tmp = os.path.join(build, 'ppf_test.bin')
        shutil.copyfile(orig_bin, tmp)
        with open(tmp, 'r+b') as f:
            ppf.apply(pp, f)
        if sha1_file(tmp) != sha1_file(cheat_bin):
            sys.exit('the PPF does not give cheat.bin')
        os.remove(tmp)
        print('PPF checked on orig.bin')
        x = tool('xdelta3*.exe', 'xdelta3')
        if x:
            xd = os.path.join(ROOT, 'patch', STEM + '.xdelta')
            if os.path.exists(xd):
                os.remove(xd)
            subprocess.run([x, '-e', '-9', '-s', 'orig.bin', 'cheat.bin', xd], cwd=build, check=True)
            back = os.path.join(build, 'xdelta_test.bin')
            if os.path.exists(back):
                os.remove(back)
            subprocess.run([x, '-d', '-s', 'orig.bin', xd, 'xdelta_test.bin'], cwd=build, check=True)
            if sha1_file(back) != sha1_file(cheat_bin):
                sys.exit('the xdelta does not give cheat.bin')
            os.remove(back)
            print('xdelta: %s (%d bytes), checked' % (xd, os.path.getsize(xd)))
        else:
            print('xdelta3 not found: no .xdelta')


if __name__ == '__main__':
    main()
