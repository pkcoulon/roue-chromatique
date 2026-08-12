============================================================
ROUE CHROMATIQUE CIE L*a*b* — roue_lab.py
============================================================

LANCEMENT
---------
    pip install -r requirements.txt
    python roue_lab.py

Le script génère 2 images PNG puis ouvre 2 fenêtres (thème sombre).


CE QU'IL PRODUIT
----------------

1. roue_lab_2d.png — La roue chromatique
   Disque du plan a*/b* colorié pixel par pixel à luminosité
   constante (L* = 70), avec cercles de chroma, directions d'axes
   (rouge / vert / jaune / bleu) et les points de la palette
   placés dessus.

2. roue_lab_LC.png — Le plan luminosité / chroma
   Chaque point placé à (C*, L*) avec C* = racine(a*² + b*²).
   Quatre quadrants délimités et nommés (CLAIR / SATURÉ / TERNE /
   PROFOND, seuils à 50), et en fond la limite des couleurs
   visibles par l'œil humain (limites de MacAdam).

Chaque point de couleur est affiché avec sa vraie couleur, un
contour blanc ou noir selon sa luminosité, et une étiquette
« nom · code hex » (placement anti-collision sur le graphique L/C).


LE MOTEUR COLORIMÉTRIQUE
------------------------
Tout est implémenté à la main, sans dépendance hors numpy et
matplotlib :

- lab_to_rgb(L, a, b)
  Conversion CIE Lab -> XYZ -> sRGB (illuminant D65, matrices
  standard, gamma sRGB), vectorisée numpy. Sert à colorier le
  disque 2D et tous les marqueurs.

- rgb_to_hex(rgb)
  Pour les étiquettes.

- limite_visible()
  Calcule les limites de MacAdam : à partir des fonctions
  colorimétriques CIE 1931 (observateur 2°) et du spectre de
  l'illuminant D65 (tables embarquées dans le fichier,
  interpolées à 2 nm), le script énumère ~40 000 « couleurs
  optimales » (spectres en bandes) et en déduit le chroma maximum
  que l'œil peut percevoir à chaque niveau de luminosité.
  NB : les tables spectrales sont les valeurs standard publiées ;
  pour un usage métrologique, les vérifier contre les tables
  officielles CIE.


CE QUE TU PEUX MODIFIER (section RÉGLAGES en haut du fichier)
-------------------------------------------------------------
    L_FOND = 70.0        # luminosité du fond du disque 2D
    CHROMA_MAX = 120.0   # rayon du disque
    RESOLUTION = 1200    # finesse du disque en pixels

    POINTS = [           # ta palette : (nom, L, a, b)
        ("Rouge vif", 55, 70, 50),
        ...              # ajouter / retirer une ligne suffit
    ]

Ainsi que les couleurs du thème (FOND, ENCRE...), les noms des
fichiers de sortie, et dans tracer_lc() les seuils des quadrants
(SEUIL_L, SEUIL_C).


EN UNE PHRASE
-------------
Un petit atelier colorimétrique autonome : on déclare une palette
en coordonnées Lab, et il la situe dans l'espace perceptif — sur
la roue des teintes et par rapport aux limites de la vision
humaine.
