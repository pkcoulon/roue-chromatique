# -*- coding: utf-8 -*-
"""
Chromathèque — version bureau
=============================

Génère deux visualisations de l'espace CIE L*a*b* (illuminant D65) :

  1. Un disque 2D du plan a*/b*, colorié pixel par pixel via la vraie
     conversion Lab -> sRGB, avec les points de couleur placés dessus.
  2. Un plan luminosité / chroma, avec en fond la limite des couleurs
     visibles par l'oeil (limites de MacAdam).

Sauvegarde roue_lab_2d.png et roue_lab_LC.png, puis affiche les deux.

Utilisation :
    python roue_lab.py

Compatible Windows / macOS / Linux (Python 3.8+).
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe

# ============================================================================
# RÉGLAGES — modifiez cette section sans toucher au reste du code
# ============================================================================

# Luminosité L* du fond du disque 2D (0 = noir, 100 = blanc).
L_FOND = 70.0

# Chroma maximum affiché : rayon du disque dans le plan a*/b*.
CHROMA_MAX = 120.0

# Résolution du disque 2D en pixels (largeur = hauteur).
RESOLUTION = 1200

# Liste des points à placer : (nom, L, a, b)
# ---------------------------------------------------------------------------
# Pour AJOUTER un point  : ajoutez une ligne, ex. ("Turquoise", 75, -40, -10),
# Pour RETIRER un point  : supprimez ou commentez sa ligne.
# ---------------------------------------------------------------------------
POINTS = [
    ("Rouge vif",    55,  70,  50),
    ("Orange",       70,  40,  70),
    ("Jaune",        90, -10,  85),
    ("Vert feuille", 60, -55,  45),
    ("Cyan",         75, -35, -25),
    ("Bleu roi",     45,  15, -60),
    ("Violet",       40,  55, -50),
    ("Magenta",      55,  75, -20),
    ("Gris neutre",  60,   0,   0),
]

# Fichiers PNG de sortie.
FICHIER_2D = "roue_lab_2d.png"
FICHIER_LC = "roue_lab_LC.png"

# --- Thème graphique (sombre : met les couleurs en valeur) ------------------
FOND = "#101014"          # fond des figures
ENCRE = "#e6e6ea"          # texte principal
ENCRE_2 = "#9a9aa2"        # texte secondaire / repères
TRAIT = "#3a3a42"          # lignes discrètes (axes, cercles)

# ============================================================================
# CONVERSIONS COLORIMÉTRIQUES (formules standard CIE, illuminant D65)
# ============================================================================

# Blanc de référence D65 (observateur 2°), normalisé Y = 1.
_D65 = np.array([0.95047, 1.00000, 1.08883])

# Matrices sRGB <-> XYZ (standard IEC 61966-2-1, D65).
_XYZ_VERS_RGB = np.array([
    [ 3.2406, -1.5372, -0.4986],
    [-0.9689,  1.8758,  0.0415],
    [ 0.0557, -0.2040,  1.0570],
])
_RGB_VERS_XYZ = np.array([
    [0.4124, 0.3576, 0.1805],
    [0.2126, 0.7152, 0.0722],
    [0.0193, 0.1192, 0.9505],
])

_DELTA = 6.0 / 29.0  # seuil des fonctions f / f⁻¹ de la définition CIE


def lab_to_rgb(L, a, b):
    """
    Convertit CIE L*a*b* (D65) -> sRGB.

    Vectorisée : accepte des scalaires ou des tableaux numpy de forme
    quelconque (broadcastés entre eux).

    Retour : tableau (..., 3), valeurs sRGB dans [0, 1]
             (écrêtées si la couleur est hors gamut sRGB).
    """
    L = np.asarray(L, dtype=np.float64)
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)

    # --- Lab -> XYZ (inversion des formules CIE 1976) -----------------------
    fy = (L + 16.0) / 116.0
    fx = fy + a / 500.0
    fz = fy - b / 200.0

    def _f_inv(t):
        return np.where(t > _DELTA, t ** 3,
                        3.0 * _DELTA ** 2 * (t - 4.0 / 29.0))

    xyz = np.stack([_D65[0] * _f_inv(fx),
                    _D65[1] * _f_inv(fy),
                    _D65[2] * _f_inv(fz)], axis=-1)

    # --- XYZ -> RGB linéaire ------------------------------------------------
    rgb_lin = xyz @ _XYZ_VERS_RGB.T

    # --- Correction gamma sRGB (encodage) -----------------------------------
    rgb_lin = np.clip(rgb_lin, 0.0, 1.0)  # écrêtage du gamut avant gamma
    rgb = np.where(rgb_lin <= 0.0031308,
                   12.92 * rgb_lin,
                   1.055 * np.power(rgb_lin, 1.0 / 2.4) - 0.055)
    return np.clip(rgb, 0.0, 1.0)


def rgb_to_hex(rgb):
    """Convertit un triplet RGB ([0, 1]) en code hexadécimal '#RRGGBB'."""
    r, g, b = (int(round(float(c) * 255)) for c in np.asarray(rgb).reshape(3))
    return "#{:02X}{:02X}{:02X}".format(r, g, b)


# ============================================================================
# LIMITE DES COULEURS VISIBLES (limites de MacAdam)
# ============================================================================
# La frontière de ce que l'œil peut percevoir comme couleur de surface est
# donnée par les « couleurs optimales » (Schrödinger / MacAdam) : des
# réflectances théoriques valant 1 sur une bande de longueurs d'onde et 0
# ailleurs (ou l'inverse). Aucune surface réelle ne peut être plus saturée.
# On les calcule avec les fonctions colorimétriques CIE 1931 (observateur 2°)
# et l'illuminant D65, échantillonnés de 380 à 780 nm par pas de 10 nm.

# Fonctions colorimétriques CIE 1931 2° : colonnes x̄, ȳ, z̄.
_CMF = np.array([
    [0.001368, 0.000039, 0.006450], [0.004243, 0.000120, 0.020050],
    [0.014310, 0.000396, 0.067850], [0.043510, 0.001210, 0.207400],
    [0.134380, 0.004000, 0.645600], [0.283900, 0.011600, 1.385600],
    [0.348280, 0.023000, 1.747060], [0.336200, 0.038000, 1.772110],
    [0.290800, 0.060000, 1.669200], [0.195360, 0.090980, 1.287640],
    [0.095640, 0.139020, 0.812950], [0.032010, 0.208020, 0.465180],
    [0.004900, 0.323000, 0.272000], [0.009300, 0.503000, 0.158200],
    [0.063270, 0.710000, 0.078250], [0.165500, 0.862000, 0.042160],
    [0.290400, 0.954000, 0.020300], [0.433450, 0.994950, 0.008750],
    [0.594500, 0.995000, 0.003900], [0.762100, 0.952000, 0.002100],
    [0.916300, 0.870000, 0.001650], [1.026300, 0.757000, 0.001100],
    [1.062200, 0.631000, 0.000800], [1.002600, 0.503000, 0.000340],
    [0.854450, 0.381000, 0.000190], [0.642400, 0.265000, 0.000050],
    [0.447900, 0.175000, 0.000020], [0.283500, 0.107000, 0.000000],
    [0.164900, 0.061000, 0.000000], [0.087400, 0.032000, 0.000000],
    [0.046770, 0.017000, 0.000000], [0.022700, 0.008210, 0.000000],
    [0.011359, 0.004102, 0.000000], [0.005790, 0.002091, 0.000000],
    [0.002899, 0.001047, 0.000000], [0.001440, 0.000520, 0.000000],
    [0.000690, 0.000249, 0.000000], [0.000332, 0.000120, 0.000000],
    [0.000166, 0.000060, 0.000000], [0.000083, 0.000030, 0.000000],
    [0.000042, 0.000015, 0.000000],
])

# Répartition spectrale de l'illuminant D65 (mêmes longueurs d'onde).
_D65_SPD = np.array([
    49.98, 54.65, 82.75, 91.49, 93.43, 86.68, 104.86, 117.01, 117.81,
    114.86, 115.92, 108.81, 109.35, 107.80, 104.79, 107.69, 104.41,
    104.05, 100.00, 96.33, 95.79, 88.69, 90.01, 89.60, 87.70, 83.29,
    83.70, 80.03, 80.21, 82.28, 78.28, 69.72, 71.61, 74.35, 61.60,
    69.89, 75.09, 63.59, 46.42, 66.81, 63.38,
])


def limite_visible(n_bandes_L=81):
    """
    Calcule la limite de MacAdam dans le plan L*/C* : le chroma maximum
    perceptible par l'œil à chaque niveau de luminosité (couleurs de
    surface sous D65, toutes teintes confondues).

    Méthode : on énumère toutes les réflectances « optimales » (bandes
    passantes et bandes coupantes de largeur variable, avec repli cyclique
    sur le spectre), on convertit chacune en Lab, puis on garde le chroma
    max par tranche de L*.

    Retour : (centres_L, chroma_max_par_L)
    """
    # Interpolation des tables de 10 nm à 2 nm : indispensable pour obtenir
    # une enveloppe lisse (les bords de bande tombent sinon tous les 10 nm).
    lam10 = np.arange(380.0, 781.0, 10.0)
    lam2 = np.arange(380.0, 780.1, 2.0)
    cmf = np.stack([np.interp(lam2, lam10, _CMF[:, k]) for k in range(3)],
                   axis=-1)
    spd = np.interp(lam2, lam10, _D65_SPD)

    n = len(lam2)
    ponderation = spd[:, None] * cmf                # S(λ)·(x̄, ȳ, z̄)
    blanc = ponderation.sum(axis=0)                 # XYZ du blanc (diffuseur)
    blanc = blanc / blanc[1]                        # normalisé Y = 1

    # Toutes les bandes cycliques [début, début + largeur) : le repli en
    # bout de spectre engendre naturellement les bandes coupantes
    # (violet + rouge = pourpres). Énumération vectorisée.
    cumul = np.vstack([np.zeros(3), np.cumsum(
        np.concatenate([ponderation, ponderation]), axis=0)])
    debuts = np.arange(n)
    largeurs = np.arange(1, n)
    idx = debuts[:, None] + largeurs[None, :]       # (n, n-1)
    xyz = cumul[idx] - cumul[debuts][:, None]       # (n, n-1, 3)
    xyz = xyz.reshape(-1, 3)

    # Normalisation : le blanc (réflectance 1 partout) doit donner Y = 1.
    xyz = xyz / ponderation.sum(axis=0)[1]

    # --- XYZ -> Lab (même blanc de référence que le reste du script) --------
    t = xyz / blanc
    f = np.where(t > _DELTA ** 3, np.cbrt(t),
                 t / (3.0 * _DELTA ** 2) + 4.0 / 29.0)
    L = 116.0 * f[:, 1] - 16.0
    a = 500.0 * (f[:, 0] - f[:, 1])
    b = 200.0 * (f[:, 1] - f[:, 2])
    chroma = np.hypot(a, b)

    # --- Enveloppe : chroma max par tranche de L* ---------------------------
    bords_L = np.linspace(0, 100, n_bandes_L + 1)
    centres_L = 0.5 * (bords_L[:-1] + bords_L[1:])
    idx = np.clip(np.digitize(L, bords_L) - 1, 0, n_bandes_L - 1)
    chroma_max = np.zeros(n_bandes_L)
    np.maximum.at(chroma_max, idx, chroma)
    return centres_L, chroma_max


# ============================================================================
# RENDU 2D — disque a*/b*
# ============================================================================

def construire_disque(L_fond, chroma_max, resolution):
    """
    Image RGBA du disque : chaque pixel (a, b) est colorié via la vraie
    conversion Lab -> sRGB à L* constant. Bord anti-aliasé, extérieur
    transparent.
    """
    coords = np.linspace(-chroma_max, chroma_max, resolution)
    aa, bb = np.meshgrid(coords, coords)

    rgb = lab_to_rgb(np.full_like(aa, L_fond), aa, bb)

    # Alpha : 1 dans le disque, dégradé doux sur ~1.5 px au bord (anti-alias).
    chroma = np.sqrt(aa ** 2 + bb ** 2)
    lissage = 1.5 * (2.0 * chroma_max / resolution)
    alpha = np.clip((chroma_max - chroma) / lissage, 0.0, 1.0)

    rgba = np.dstack([rgb, alpha])
    extent = (-chroma_max, chroma_max, -chroma_max, chroma_max)
    return rgba, extent


def tracer_2d():
    """Figure 2D : disque, repères discrets, points étiquetés."""
    fig, ax = plt.subplots(figsize=(10, 10), facecolor=FOND)
    ax.set_facecolor(FOND)

    # --- Disque coloré ------------------------------------------------------
    rgba, extent = construire_disque(L_FOND, CHROMA_MAX, RESOLUTION)
    ax.imshow(rgba, extent=extent, origin="lower", interpolation="bilinear",
              zorder=1)

    # --- Repères discrets : croix centrale + cercles de chroma --------------
    ax.axhline(0, color=TRAIT, linewidth=0.8, zorder=2)
    ax.axvline(0, color=TRAIT, linewidth=0.8, zorder=2)

    for c in np.arange(40, CHROMA_MAX, 40):
        ax.add_patch(plt.Circle((0, 0), c, fill=False, color=TRAIT,
                                linewidth=0.7, linestyle=(0, (2, 4)),
                                zorder=2))
        # Petite graduation de chroma, posée à 45° sur chaque cercle
        # (léger liseré sombre pour rester lisible sur le disque coloré).
        ax.text(c * 0.7071 + 2, c * 0.7071 + 2, f"{c:g}",
                fontsize=8, color=ENCRE, zorder=2,
                path_effects=[pe.withStroke(linewidth=2, foreground="#1a1a20")])

    # Cercle de bordure.
    ax.add_patch(plt.Circle((0, 0), CHROMA_MAX, fill=False,
                            color=ENCRE_2, linewidth=1.2, zorder=3))

    # --- Étiquettes des directions d'axes, hors du disque -------------------
    d = CHROMA_MAX * 1.07
    etiquettes_axes = [
        (d, 0, "+a*\nrouge", "left", "center"),
        (-d, 0, "−a*\nvert", "right", "center"),
        (0, d, "+b*  jaune", "center", "bottom"),
        (0, -d, "−b*  bleu", "center", "top"),
    ]
    for x, y, txt, ha, va in etiquettes_axes:
        ax.text(x, y, txt, ha=ha, va=va, fontsize=10, color=ENCRE_2,
                linespacing=1.3)

    # --- Points de couleur --------------------------------------------------
    for nom, L, a, b in POINTS:
        couleur = lab_to_rgb(L, a, b)   # vraie couleur du point
        hexa = rgb_to_hex(couleur)
        contour = "white" if L < 50 else "black"

        ax.scatter(a, b, s=230, color=couleur.reshape(1, 3),
                   edgecolors=contour, linewidths=1.6, zorder=5)

        # Étiquette décalée radialement (vers l'extérieur du disque) pour
        # dégager le centre ; pastille sombre semi-transparente.
        norme = np.hypot(a, b)
        ux, uy = (a / norme, b / norme) if norme > 1e-9 else (0.35, 0.9)
        ax.annotate(
            f"{nom}  ·  {hexa}",
            xy=(a, b), xytext=(a + ux * 14, b + uy * 14),
            textcoords="data",
            ha="center" if abs(ux) < 0.4 else ("left" if ux > 0 else "right"),
            va="center" if abs(uy) < 0.4 else ("bottom" if uy > 0 else "top"),
            fontsize=9, color=ENCRE, zorder=6,
            bbox=dict(boxstyle="round,pad=0.35", facecolor="#1a1a20",
                      edgecolor="#4a4a52", linewidth=0.6, alpha=0.88),
        )

    # --- Habillage ----------------------------------------------------------
    marge = CHROMA_MAX * 1.22
    ax.set_xlim(-marge, marge)
    ax.set_ylim(-marge, marge)
    ax.set_aspect("equal")
    ax.set_axis_off()  # pas de cadre : le disque et ses repères suffisent

    ax.set_title("Roue chromatique CIE L*a*b*",
                 fontsize=16, color=ENCRE, pad=18)

    fig.tight_layout()
    return fig




# ============================================================================
# RENDU L*/CHROMA — luminosité en ordonnée, chroma en abscisse
# ============================================================================

def tracer_lc():
    """
    Figure 2D : chaque point est placé à (chroma, L*) avec
    chroma = √(a² + b²). En fond, la limite des couleurs visibles par
    l'œil humain (limites de MacAdam) : le chroma maximum perceptible à
    chaque L*, toutes teintes confondues.
    """
    fig, ax = plt.subplots(figsize=(10, 8), facecolor=FOND)
    ax.set_facecolor(FOND)

    # --- Limite de l'œil : chroma max perceptible par tranche de L* ---------
    centres_L, chroma_max_par_L = limite_visible()

    ax.fill_betweenx(centres_L, 0, chroma_max_par_L,
                     color="#1e1e26", zorder=1)
    ax.plot(chroma_max_par_L, centres_L, color=TRAIT, linewidth=1.0,
            zorder=2)

    # Borne droite du graphique : adaptée à l'étendue de la limite visible.
    x_max = max(CHROMA_MAX, chroma_max_par_L.max()) * 1.06
    ax.text(x_max * 0.98, 10, "limite des couleurs visibles\n"
            "(MacAdam, surfaces sous D65)", fontsize=8.5, color=ENCRE_2,
            ha="right", va="center", linespacing=1.4)

    # --- Grille discrète ----------------------------------------------------
    ax.grid(True, color=TRAIT, linewidth=0.5, linestyle=(0, (2, 4)), zorder=0)
    ax.set_axisbelow(True)

    # --- Zones qualitatives délimitées --------------------------------------
    # Le plan L*/C* se lit en 4 quadrants, séparés par deux seuils :
    #   L* = 50  (clair / sombre)   et   C* = 50  (peu / très saturé)
    #     - CLAIR   : L* > 50, C* < 50  (pastels, tons lumineux doux)
    #     - SATURÉ  : L* > 50, C* > 50  (couleurs vives)
    #     - TERNE   : L* < 50, C* < 50  (proche des gris)
    #     - PROFOND : L* < 50, C* > 50  (sombre mais coloré)
    SEUIL_L = 50.0
    SEUIL_C = 50.0

    # Lignes de séparation, un cran plus visibles que la grille.
    ax.axhline(SEUIL_L, color=ENCRE_2, linewidth=0.9,
               linestyle=(0, (6, 4)), alpha=0.5, zorder=2)
    ax.axvline(SEUIL_C, color=ENCRE_2, linewidth=0.9,
               linestyle=(0, (6, 4)), alpha=0.5, zorder=2)

    # Libellés centrés dans leur quadrant.
    zones = [
        ("CLAIR",   SEUIL_C * 0.5,           (SEUIL_L + 100) / 2),
        ("TERNE",   SEUIL_C * 0.5,           SEUIL_L * 0.5),
        ("SATURÉ",  (SEUIL_C + x_max) / 2,   (SEUIL_L + 100) / 2),
        ("PROFOND", (SEUIL_C + x_max) / 2,   SEUIL_L * 0.5),
    ]
    for texte, cx, cy in zones:
        ax.text(cx, cy, texte, fontsize=15, color=ENCRE_2, alpha=0.55,
                ha="center", va="center", fontstyle="italic",
                fontweight="bold", zorder=1)

    # --- Points -------------------------------------------------------------
    # Placement d'étiquettes anti-collision : pour chaque point on essaie
    # 4 directions (haut-droite, haut-gauche, bas-droite, bas-gauche) et on
    # garde la première dont le cadre estimé ne recouvre ni une étiquette
    # déjà posée, ni un autre point.
    # Estimation de la taille d'une étiquette en unités de données
    # (≈ 5.5 pt par caractère en largeur, ≈ 15 pt en hauteur).
    echelle_x = x_max / 620.0     # ~620 pt de large utile pour l'axe x
    echelle_y = 100.0 / 480.0     # ~480 pt de haut utile pour l'axe y

    def _cadre(cx, cy, texte, dx, dy, ha):
        """Rectangle (x0, x1, y0, y1) estimé de l'étiquette en données."""
        largeur = len(texte) * 5.5 * echelle_x
        hauteur = 15.0 * echelle_y
        x0 = cx + dx * echelle_x - (largeur if ha == "right" else 0)
        y0 = cy + dy * echelle_y - (hauteur / 2 if dy < 0 else 0)
        return (x0, x0 + largeur, y0, y0 + hauteur)

    def _aire_commune(r1, r2):
        """Aire de recouvrement entre deux rectangles (0 si disjoints)."""
        return (max(0.0, min(r1[1], r2[1]) - max(r1[0], r2[0]))
                * max(0.0, min(r1[3], r2[3]) - max(r1[2], r2[2])))

    directions = [(10, 8, "left"), (-10, 8, "right"),
                  (10, -18, "left"), (-10, -18, "right")]
    cadres = []       # cadres des étiquettes déjà posées
    tous_points = [(float(np.hypot(a, b)), L) for _, L, a, b in POINTS]

    for (nom, L, a, b), (chroma, _) in zip(POINTS, tous_points):
        couleur = lab_to_rgb(L, a, b)
        hexa = rgb_to_hex(couleur)
        contour = "white" if L < 50 else "black"
        texte = f"{nom}  ·  {hexa}"

        ax.scatter(chroma, L, s=230, color=couleur.reshape(1, 3),
                   edgecolors=contour, linewidths=1.6, zorder=5)

        # Score de chaque direction : surface de recouvrement avec les
        # étiquettes déjà posées + forte pénalité si un marqueur est couvert.
        # On garde la direction au score minimal (0 = emplacement libre).
        def _score(direction):
            dx, dy, ha = direction
            cadre = _cadre(chroma, L, texte, dx, dy, ha)
            cout = sum(_aire_commune(cadre, c) for c in cadres)
            for px, py in tous_points:
                if (px, py) != (chroma, L):
                    boite_pt = (px - 2.5, px + 2.5, py - 1.8, py + 1.8)
                    cout += 10.0 * _aire_commune(cadre, boite_pt)
            return cout

        dx, dy, ha = min(directions, key=_score)
        cadres.append(_cadre(chroma, L, texte, dx, dy, ha))
        ax.annotate(
            texte,
            xy=(chroma, L), xytext=(dx, dy), textcoords="offset points",
            ha=ha, fontsize=9, color=ENCRE, zorder=6,
            bbox=dict(boxstyle="round,pad=0.35", facecolor="#1a1a20",
                      edgecolor="#4a4a52", linewidth=0.6, alpha=0.88),
        )

    # --- Habillage ----------------------------------------------------------
    ax.set_xlim(-3, x_max)
    ax.set_ylim(0, 100)
    for cote in ("top", "right"):
        ax.spines[cote].set_visible(False)
    for cote in ("bottom", "left"):
        ax.spines[cote].set_color(TRAIT)
    ax.tick_params(colors=ENCRE_2, labelsize=9)
    ax.set_xlabel("Chroma  C* = √(a*² + b*²)", fontsize=11, color=ENCRE)
    ax.set_ylabel("L*  (luminosité)", fontsize=11, color=ENCRE)
    ax.set_title("Luminosité / chroma des points",
                 fontsize=15, color=ENCRE, pad=14)

    fig.tight_layout()
    return fig


# ============================================================================
# POINT D'ENTRÉE
# ============================================================================

if __name__ == "__main__":
    fig2d = tracer_2d()
    fig2d.savefig(FICHIER_2D, dpi=150, facecolor=FOND)
    print(f"Image sauvegardée : {FICHIER_2D}")

    figlc = tracer_lc()
    figlc.savefig(FICHIER_LC, dpi=150, facecolor=FOND)
    print(f"Image sauvegardée : {FICHIER_LC}")

    # Affichage à l'écran (deux fenêtres).
    plt.show()
