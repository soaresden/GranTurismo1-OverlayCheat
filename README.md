# Gran Turismo (PS1) — menu de triche en surimpression

🇬🇧 [English version](README.en.md)

**▶ [Ajouter la triche à ton disque, dans ton navigateur](https://soaresden.github.io/GranTurismo1-OverlayCheat/)** : choisis ton `.chd` ou ton `.bin`,
la page te rend l'image disque avec le menu de triche (rien n'est envoyé sur internet).

Un patch pour **Gran Turismo** (PlayStation, version européenne **SCES-00984**) : en
maintenant **SELECT** (ou en appuyant **L1 + R1 + L2 + R2** ensemble), un petit menu apparaît
par-dessus le jeu, avec deux options :

1. **FREEZE TIMER** — arrête le chronomètre des **permis** (licences) ;
2. **MONEY** — change les crédits **en direct** (pas réglable, maximum, zéro).

Le patch ne touche que les exécutables du jeu (`GTOS.EXE`, `GTMENU.EXE`, `GTMAIN.EXE`) et ne
contient aucune donnée du jeu : il marche sur le disque d'origine **et** sur un disque déjà
modifié ailleurs (par exemple le mod MX-5 du même auteur, qui ne change pas ces fichiers).

## Commandes (manette 1)

Deux façons d'ouvrir le menu `GT1 CHEAT`, en haut de l'écran :

- **maintenir SELECT** : le menu apparaît après un court instant et disparaît quand on relâche ;
- **appuyer L1 + R1 + L2 + R2 ensemble** : le menu s'ouvre et **reste ouvert** ; **START** (ou
  les quatre gâchettes à nouveau) le referme. À utiliser dans **Batocera / RetroArch**, où
  SELECT est la touche « hotkey » : tant qu'elle est maintenue, le jeu ne reçoit rien, et
  SELECT + une touche déclenche les raccourcis de l'émulateur.

Tant que le menu est ouvert, le jeu ne reçoit plus la manette.

| Touche | Ligne FREEZE TIMER | Ligne MONEY |
|---|---|---|
| ↑ / ↓ | change de ligne | change de ligne |
| ← / → | ON / OFF | − / + le pas (maintenu : répétition) |
| ✕ / ○ | ON / OFF | |
| R1 / L1 | | pas × 10 / ÷ 10 (de 1 à 10 000 000) |
| △ | | 99 999 999 (le maximum du jeu) |
| □ | | 0 |

- **FREEZE TIMER ON** : dans un permis, le chronomètre s'arrête. S'il était déjà ON au départ,
  il s'arrête à **0:00.040** (juste après le départ) : un permis dont le chrono reste à 0 ne se
  termine jamais. Le choix est gardé d'un écran à l'autre, jusqu'à l'extinction de la console.
- **MONEY** : les crédits changent tout de suite (affichage du garage, concessionnaires…).
- Un appui **bref** sur SELECT (sans autre touche) est rendu au jeu quand on le relâche.

Essayé dans PCSX-Redux avec le BIOS PAL SCPH-5502 : menu sur la carte de la ville et en
permis, argent mis à jour à l'écran, permis B-1 réussi avec le chrono arrêté (*YOU WIN GOLD*,
0:00.059). Combinaison L1 + R1 + L2 + R2 sur la carte de la ville : le menu reste ouvert, △ met
99 999 999, START le referme, SELECT marche toujours.

## Appliquer le patch

### Avec le script (recommandé)

Python 3, rien à installer :

```bash
python patch_disc.py "Gran Turismo.chd"            # -> "Gran Turismo [Cheat].bin" + .cue
python patch_disc.py "Gran Turismo.cue" "GT cheat.bin"
```

L'entrée peut être un `.chd`, un `.cue` ou un `.bin` ; chaque exécutable est vérifié (SHA-1)
avant d'être modifié.

### Avec un patch PPF / xdelta (dossier `patch/`)

- `Gran Turismo (Europe) [Overlay Cheat].ppf` : à appliquer sur le `.bin` (2352 octets par
  secteur, une seule piste). Il ne touche que les secteurs des trois exécutables : il
  s'applique donc aussi à un disque déjà modifié dans d'autres fichiers.
- `Gran Turismo (Europe) [Overlay Cheat].xdelta` : pour le `.bin` d'origine seulement
  (xdelta vérifie la source).

`.bin` d'origine attendu (une piste MODE2/2352, 691 652 640 octets, tel que l'écrit
`patch_disc.py` / chdman depuis le CHD) : SHA-1 `1da2e8b50b6f506335b73d84223db2277f843e3f`.
Résultat : SHA-1 `9192f566ae6916e89ba96d5415999b0a4c3046b8` (build 1FE1CB19).

## Comment ça marche

Les exécutables de Gran Turismo sont compressés (« PSLZ ») et décompressés en place par un
petit chargeur à leur point d'entrée. Ce chargeur commence par se copier, avec son en-tête,
juste après la fin du code décompressé, puis décompresse et saute au jeu (0x80010000).

Le patch modifie deux mots de cet en-tête et rien d'autre du code du jeu :

- **+0x14** (taille copiée) est agrandi : la copie emporte aussi un petit **stub** écrit dans
  les octets libres (des zéros jamais lus) qui suivent le chargeur dans le fichier ;
- **+0x18** (adresse de saut) pointe sur ce stub au lieu de 0x80010000.

Le code compressé du jeu reste tel quel. Le stub, une fois le jeu décompressé :

1. recopie son morceau du **bloc résident** à 0x8000F000 (mémoire basse, libre : le tas du
   noyau du BIOS s'arrête vers 0x8000E500). Le bloc (≈ 2,7 Ko) ne tient pas dans un seul
   fichier : le 1er morceau vient de `GTOS.EXE` (lancé au démarrage, avant les menus), le 2e de
   `GTMENU.EXE` ;
2. vérifie que le bloc est complet (mot magique + CRC de la version au début, autre mot
   magique à la fin), puis appelle `cheat_boot`, qui redirige trois `jal` du jeu après avoir
   vérifié qu'ils sont bien ceux attendus ;
3. vide le cache d'instructions (A0:44, comme le chargeur) et saute au jeu.

`GTMAIN.EXE` (courses, permis) n'a qu'un stub : il utilise le bloc déjà en mémoire. Si le
bloc est absent ou d'une autre version (démo lancée avant les menus, sauvegarde d'état d'un
autre build), le stub laisse le jeu intact.

Les trois `jal` redirigés (le jeu appelle notre fonction, qui appelle la sienne) :

| | GTMAIN.EXE | GTMENU.EXE | rôle |
|---|---|---|---|
| copie de la manette | 0x8007A92C → memcpy 0x8007BD10 | 0x80041144 → memcpy 0x80045460 | une fois par image : lit SELECT, le menu, masque la manette au jeu |
| DrawOTag de l'image | 0x8007021C → 0x80086F2C | 0x80036978 → 0x8004B3A4 | après le dessin de l'image (DrawSync), dessine le menu par-dessus |
| horloge de course | 0x80052D48 → 0x80057EB4 | — | sautée en permis si FREEZE TIMER |

Adresses utiles trouvées (analyse statique, vérifiées dans PCSX-Redux) :

| Adresse | Rôle |
|---|---|
| 0x800C0940 / 0x800C09C0 (GTMAIN), 0x800A86D0 / 0x800A8750 (GTMENU) | tampons de la manette (libpad `PadInitDirect`) / copie lue par le jeu |
| 0x80093BC8 (GTMAIN) | horloge de course (ms) : +40 par image à 25 images/s (+20 à 50) |
| 0x800CB645 (GTMAIN) | mode de jeu, 4 = permis (table 0x8008BC68, cas 0x80027E80 → « license result menu ») |
| 0x800C4A94 (GTMAIN), 0x8009B874 (GTMENU) | crédits (u32), bloc d'état « GTos » + 0x44, transmis entre exécutables par la RAM du SPU |
| 0x8000F000…0x8000FA8B | bloc résident (le code de la triche) |
| 0x8000FF80 | état de la triche (FREEZE TIMER, ligne, pas…), gardé entre les exécutables |

Dessin : primitives TILE envoyées directement au GPU (GP0) après `DrawSync`, police 5×7 du
projet (`src/font.py`), taille doublée en 640 de large / 480 lignes, mode de dessin du jeu
remis ensuite. Manette : bits après inversion, SELECT = 0x0001 (octet 2 bit 0 des données
brutes), comme le code de lecture du jeu (0x8007A7D0).

## Limites connues

- Manette 1 seulement (avec multitap : sa prise A).
- Pendant que le menu est ouvert, le jeu ne voit plus la manette.
- Le menu n'existe qu'une fois le **mode Gran Turismo** ouvert au moins une fois depuis
  l'allumage : le 2e morceau du code vient de `GTMENU.EXE`. L'écran titre et les menus du mode
  Arcade n'ont pas le menu ; les courses Arcade l'ont, après un passage par le mode GT.
- Menus en 640×480 entrelacé : le jeu redessine tout l'écran à chaque image et le menu est
  dessiné après ; sur un émulateur qui affiche ligne par ligne (Beetle) ou sur console, un
  léger scintillement est possible.
- Pendant que le menu est affiché, le processeur attend la fin du dessin de chaque image (le
  jeu peut ralentir un peu, seulement tant que le menu est affiché).
- FREEZE TIMER n'agit que dans les permis (mode 4), pas en course.

## Construire depuis les sources

- `src/cheat.c`, `src/start.S`, `src/stub.S`, `src/payload.ld`, `src/font.py` : le code ;
- `gt1cheat/exes.py` : toutes les adresses du jeu ; `gt1cheat/patcher.py` : le patch ;
  `gt1cheat/check.py` : vérifications d'un exécutable patché (le chargeur du jeu est rejoué en
  Python : même code décompressé, copie = en-tête + chargeur + stub, saut sur le stub, sites
  d'origine en place) ;
- `python build.py [--list]` : compile (GCC MIPS `mipsel-none-elf-*` de PSn00bSDK, ou
  `mips-linux-gnu-*`), vérifie (`src/verify.py` : délais de chargement R3000, pas de saut dans
  un délai, mfhi/mflo, cibles des sauts, registres sauvegardés/restaurés, tables) et écrit
  `gt1cheat/payload.py` ;
- `python make_release.py --src <image> --test <dossier> --patches` : disque de test, PPF et
  xdelta (xdelta3), chacun vérifié.

Le format PSLZ (disposition de l'en-tête) vient de GT1ExecutableTool de pez2k ; le lecteur de
CHD et l'écriture des secteurs (EDC/ECC) viennent du projet MazdaMx5NDRF du même auteur.

## Licence

GPL-3.0 (voir `LICENSE`). Aucune donnée du jeu n'est fournie : il faut son propre disque.
