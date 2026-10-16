# Fiche romhacking.net — Gran Turismo Overlay Cheat

Textes à copier dans le formulaire « Submit a hack ». Le site est en anglais ; la version
française de la description est en bas. La fiche de GT2 est dans le dépôt
GranTurismo2-OverlayCheat (`romhacking/FICHE_ROMHACKING.md`) : deux envois séparés, un par jeu.

## Fichiers à envoyer

- **Patch** : `GT1-OverlayCheat-v1.1.zip` (https://raw.githubusercontent.com/soaresden/GranTurismo1-OverlayCheat/main/romhacking/GT1-OverlayCheat-v1.1.zip) (PPF + xdelta + README.txt + LISEZMOI.txt)
- **Captures** (PNG, résolution d'origine du jeu), dans cet ordre ; romhacking.net les prend
  par URL, les adresses directes sur GitHub sont sous chaque ligne :
  1. `screenshots/0_menu_city_map.png` — le menu sur la carte du mode GT (640 × 480)
     https://raw.githubusercontent.com/soaresden/GranTurismo1-OverlayCheat/main/romhacking/screenshots/0_menu_city_map.png
  2. `screenshots/1_menu_licence_list.png` — le menu sur la liste des permis B (640 × 480)
     https://raw.githubusercontent.com/soaresden/GranTurismo1-OverlayCheat/main/romhacking/screenshots/1_menu_licence_list.png
  3. `screenshots/2_menu_licence_test.png` — le menu pendant le permis B-1 (320 × 240)
     https://raw.githubusercontent.com/soaresden/GranTurismo1-OverlayCheat/main/romhacking/screenshots/2_menu_licence_test.png
  4. `screenshots/3_licence_timer_frozen.png` — le chrono figé à 0:00.040 en permis (320 × 240)
     https://raw.githubusercontent.com/soaresden/GranTurismo1-OverlayCheat/main/romhacking/screenshots/3_licence_timer_frozen.png

## Champs du formulaire

| Champ | Valeur |
|---|---|
| Title | Gran Turismo Overlay Cheat Menu |
| Hack of | Gran Turismo |
| Platform | PlayStation |
| Category | Cheat *(sinon : Improvement)* |
| Status | Fully Playable |
| Version | 1.1 |
| Release date | 2026-10-16 |
| Language | English *(le menu ; le jeu reste dans sa langue)* |
| Author | soaresden |
| Website | https://github.com/soaresden/GranTurismo1-OverlayCheat |
| Region / version | PAL (Europe), SCES-00984 |
| Patch format | PPF 3.0 and xdelta3 |

**ROM / ISO information** (champ « Source ROM ») :

```
Gran Turismo (Europe) (En,Fr,De,Es,It).bin
Single track, MODE2/2352, 691,652,640 bytes
CRC32: DBA21C42
SHA-1: 1da2e8b50b6f506335b73d84223db2277f843e3f
```

**Short description** (une ligne) :

> Hold SELECT (or L1+R1+L2+R2) for an overlay menu: freeze the licence test timer and change your credits live.

**Description** :

```
An overlay cheat menu for Gran Turismo (PAL). Hold SELECT, or press L1 + R1 + L2 + R2 together,
and a small menu appears over the game: on the city map, in the dealers, in races and in
licence tests.

- FREEZE TIMER: stops the clock of the licence tests. Turned on before the start, the clock stops
  at 0:00.040; stop in the target zone and the gold is yours.
- MONEY: change your credits live, with an adjustable step (R1 / L1), Triangle for the maximum
  (99,999,999) and Square for zero.

While the menu is open the game does not receive the pad; a short tap of SELECT is still given to
the game. The L1 + R1 + L2 + R2 combo keeps the menu open (START closes it): use it in RetroArch,
where SELECT is often the hotkey button.

The menu is there once Gran Turismo mode has been opened at least once since power on (not on the
title screen nor in the Arcade mode menus).

The patch only changes the three executables (GTOS.EXE, GTMENU.EXE, GTMAIN.EXE: two words of
their packed header and free bytes after the loader; the game code is not touched), so the PPF
also applies to a disc already modded in other files. For a .chd or .cue, use the Python tool of
the project (patch_disc.py).

Tested in PCSX-Redux (Sony BIOS). Sources and technical notes on GitHub.
```

## Description en français

```
Un menu de triche en surimpression pour Gran Turismo (PAL). Maintenez SELECT, ou appuyez
L1 + R1 + L2 + R2 ensemble, et un petit menu apparaît par-dessus le jeu : sur la carte de la
ville, chez les concessionnaires, en course et en permis.

- FREEZE TIMER : arrête le chronomètre des permis. Activé avant le départ, le chrono s'arrête à
  0:00.040 ; arrêtez-vous dans la zone et l'or est à vous.
- MONEY : changez vos crédits en direct, avec un pas réglable (R1 / L1), Triangle pour le maximum
  (99 999 999) et Carré pour zéro.

Tant que le menu est ouvert, le jeu ne reçoit plus la manette ; un appui bref sur SELECT reste
transmis au jeu. La combinaison L1 + R1 + L2 + R2 garde le menu ouvert (START le referme) : à
utiliser dans RetroArch, où SELECT est souvent la touche « hotkey ».

Le menu existe une fois le mode Gran Turismo ouvert au moins une fois depuis l'allumage (pas sur
l'écran titre ni dans les menus du mode Arcade).

Le patch ne modifie que les trois exécutables (GTOS.EXE, GTMENU.EXE, GTMAIN.EXE : deux mots de
leur en-tête compressé et des octets libres après le chargeur ; le code du jeu n'est pas touché),
donc le PPF s'applique aussi à un disque déjà modifié dans d'autres fichiers. Pour un .chd ou un
.cue, utilisez l'outil Python du projet (patch_disc.py).

Essayé dans PCSX-Redux (BIOS Sony). Sources et notes techniques sur GitHub.
```

## À vérifier avant d'envoyer

- Le CRC32 / SHA-1 de **ton** image doit être celui ci-dessus. Je ne l'ai pas comparé à la
  fiche Redump : si ta copie a d'autres valeurs, dis-le moi et je refais les patchs depuis la
  bonne image.
- Essayé seulement dans PCSX-Redux : si tu l'essaies dans RALibretro / RetroArch (cœur Beetle
  PSX), ajoute-le à la ligne « Tested » de la description.
- Romhacking.net demande souvent que la première capture soit l'écran titre ; ici le menu
  n'existe pas sur l'écran titre, la première capture est donc la carte du mode GT.
