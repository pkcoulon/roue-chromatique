# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Langue

Tout le dépôt est en français : identifiants JS, commentaires, textes d'interface, messages de commit (sujet impératif court, ex. « Colonne de gauche redimensionnable horizontalement »). Continuer en français.

## Deux artefacts indépendants

- **`index.html`** — l'application web complète dans un seul fichier (CSS + HTML + JS inline, ~2200 lignes). Aucun framework, aucun build, aucun npm. Déployée par GitHub Pages : un push sur `main` publie sur https://vgonnot.fr (fichier `CNAME`).
- **`roue_lab.py`** — version bureau autonome (numpy + matplotlib) qui génère 3 PNG et ouvre 3 fenêtres interactives. Documentée dans `README.txt`, réglages en tête de fichier (`L_FOND`, `CHROMA_MAX`, `POINTS`…). Lancement : `pip install -r requirements.txt && python roue_lab.py`.

Les deux implémentent le même moteur colorimétrique (Lab ↔ sRGB en D65, limites de MacAdam recalculées depuis les CMF CIE 1931 + SPD D65) — une correction dans l'un se reporte souvent dans l'autre.

## Développement local (web)

```bash
python3 -m http.server 8642        # puis http://127.0.0.1:8642/index.html
```

Pas de tests ni de linter. La porte de connexion Firebase (`#porte`) bloque toute l'interface ; pour tester sans compte, dans la console : `document.getElementById('porte').hidden = true` (les fonctions Bibliothèque/Compte resteront inertes, tout le reste marche en local).

## Architecture de `index.html`

- **Vues** : le menu déroulant `#sel-vue` bascule entre « roue » et « spectre » en masquant tout élément portant `data-vue` différent (`appliquerVue`). Les éléments sans `data-vue` (Compte, sélecteur) restent visibles. Vue mémorisée dans `localStorage`.
- **Canvas** : quatre canvas (`cv-roue`, `cv-3d`, `cv-lc`, `cv-spectre`), toujours en thème sombre (constantes `G`), redessinés via `redessiner()`/`majTout()` + un `ResizeObserver` sur `.zone-canvas`. Chaque dessinateur commence par `if (!cv.clientWidth) return;` — un canvas de la vue masquée a une taille nulle et `ctx.arc` à rayon négatif lève une exception qui casse tout le rafraîchissement. Utilitaires partagés : `prepCanvas` (DPR), `pilule` (étiquettes).
- **Boutons génériques** : `data-png` (export PNG) et `data-plein` (quasi plein écran, sortie par Échap) sont câblés une fois au chargement par `querySelectorAll` — un bouton ajouté dans le HTML statique est pris en charge automatiquement.
- **État et persistance** : palette → `rouelab.points.v1`, spectres → `rouelab.spectres.v1`, vue → `rouelab.vue`, largeur de colonne → `rouelab.asideW` (localStorage). La Bibliothèque, elle, vit uniquement sur le compte Firestore (`bibliotheques/{uid}`), poussée avec un debounce (`planifierPousseCloud`).
- **Firebase** : SDK compat chargé depuis jsdelivr avec empreintes SRI. Création de comptes désactivée côté serveur (comptes créés à la main dans la console Firebase) ; les règles Firestore limitent chaque compte à son propre document. La config `FIREBASE_CONFIG` est publique par conception.
- **Import Excel** : SheetJS chargé à la demande une seule fois (`chargerXLSX`, SRI). Deux parseurs : `pointsDepuisFeuille` (palette L/a/b) et `spectreDepuisFeuille` (spectre λ/A). Les deux détectent la ligne d'en-tête et acceptent la virgule décimale française.

## Conventions de sécurité (à respecter pour tout nouveau code)

- Toute donnée d'origine non fiable (localStorage, JSON importé, Firestore, Excel) passe par une fonction `normaliser*` (`normaliserPoint`, `normaliserDossiers`, `normaliserMesure`, `normaliserColorants`) : nombres bornés, chaînes forcées. Ajouter une source de données = ajouter/réutiliser un normaliseur.
- Ne jamais interpoler une chaîne non fiable dans du `innerHTML` : construire avec `textContent`, `.value`, `new Option(...)` (correctif XSS de `175e212`).
- La CSP (balise `<meta>`) n'autorise que les scripts self + jsdelivr et les connexions googleapis. Un nouveau script CDN exige son empreinte SRI et, si besoin, une mise à jour de la CSP.

## Pièges CSS connus

- Règle globale `[hidden] { display: none !important; }` : nécessaire car toute règle d'affichage (`display:flex` sur `.actions`…) écraserait sinon l'attribut `hidden`.
- Thème clair/sombre par variables CSS (`prefers-color-scheme` + surcharge `data-theme`) pour l'interface ; les surfaces canvas restent sombres quel que soit le thème.
- Suppressions en deux clics via `armerSuppr` (pas de `confirm()` bloquant).
