# Helios - Jean Meeus Solar Integration for Home Assistant

**Version:** `0.0.1-alpha`

*Read this in: [English](#english-documentation) | [Français](#documentation-française)*

---

<a name="english-documentation"></a>

## English Documentation

**Helios** is a lightweight, zero-dependency Home Assistant custom integration that calculates solar position and daily solar events using the astronomical equations from **Jean Meeus's *Astronomical Algorithms* (2nd Edition, Willmann-Bell, 1998)**.

### Key Features

* **Zero External Dependencies:** Uses exclusively Python's standard `math` and `datetime` libraries (`"requirements": []` in `manifest.json`).
* **Decoupled Architecture:** `solar_engine.py` has zero Home Assistant imports, making unit testing and equation auditing effortless.
* **Complete Solar Metrics:** Azimuth, apparent and geometric elevation, declination, right ascension, equation of time, Earth-Sun distance (AU), Julian Day, solar noon, sunrise/sunset, and civil/nautical/astronomical twilights.

### Mathematical Reference & Equations Audit

All calculations implemented in `custom_components/helios/solar_engine.py` can be verified against **Jean Meeus, *Astronomical Algorithms*, 2nd Edition (1998)**:

#### 1. Julian Day ($JD$) and Julian Century ($T$) — *Chapter 7 (Eq. 7.1) & Chapter 25 (Eq. 25.1)*

For a given UTC date $(Y, M, D)$ with decimal day $D$ (if $M \le 2$, $Y \leftarrow Y-1$ and $M \leftarrow M+12$):

$$
A = \lfloor Y / 100 \rfloor, \quad B = 2 - A + \lfloor A / 4 \rfloor
$$

$$
JD = \lfloor 365.25 (Y + 4716) \rfloor + \lfloor 30.6001 (M + 1) \rfloor + D + B - 1524.5
$$

$$
T = \frac{JD - 2451545.0}{36525}
$$

#### 2. Solar Coordinates — *Chapter 25 (Eq. 25.2 to 25.8)*

* **Geometric Mean Longitude of the Sun ($L_0$, Eq. 25.2):**
  $$
  L_0 = 280.46646^\circ + 36000.76983^\circ T + 0.0003032^\circ T^2 \pmod{360^\circ}
  $$
* **Mean Anomaly of the Sun ($M$, Eq. 25.3):**
  $$
  M = 357.52911^\circ + 35999.05029^\circ T - 0.0001537^\circ T^2 \pmod{360^\circ}
  $$
* **Eccentricity of Earth's Orbit ($e$, Eq. 25.4):**
  $$
  e = 0.016708634 - 0.000042037 T - 0.0000001267 T^2
  $$
* **Sun's Equation of the Center ($C$, p. 164):**
  $$
  C = (1.914602^\circ - 0.004817^\circ T - 0.000014^\circ T^2)\sin(M) + (0.019993^\circ - 0.000101^\circ T)\sin(2M) + 0.000289^\circ\sin(3M)
  $$
* **True Longitude ($\odot$), True Anomaly ($v$), and Earth-Sun Distance ($R$ in AU, Eq. 25.5):**
  $$
  \odot = L_0 + C, \quad v = M + C, \quad R = \frac{1.000001018(1 - e^2)}{1 + e\cos(v)}
  $$
* **Apparent Longitude ($\lambda$, Eq. 25.8):**
  $$
  \Omega = 125.04^\circ - 1934.136^\circ T, \quad \lambda = \odot - 0.00569^\circ - 0.00478^\circ\sin(\Omega)
  $$

#### 3. Obliquity of the Ecliptic & Equatorial Coordinates — *Chapter 22 (Eq. 22.2) & Chapter 25 (Eq. 25.6–25.8)*

* **Mean ($\varepsilon_0$) and Corrected Obliquity ($\varepsilon$):**

  $$
  \varepsilon_0 = 23^\circ 26' 21.448'' - 46.8150'' T - 0.00059'' T^2 + 0.001813'' T^3
  $$

  $$
  \varepsilon = \varepsilon_0 + 0.00256^\circ\cos(\Omega)
  $$
* **Right Ascension ($\alpha$, Eq. 25.6) and Declination ($\delta$, Eq. 25.7):**

  $$
  \tan(\alpha) = \frac{\cos(\varepsilon)\sin(\lambda)}{\cos(\lambda)}, \quad \sin(\delta) = \sin(\varepsilon)\sin(\lambda)
  $$

#### 4. Sidereal Time & Horizontal Coordinates (Azimuth & Elevation) — *Chapter 12 (Eq. 12.4) & Chapter 13 (Eq. 13.5–13.6)*

* **Mean Sidereal Time at Greenwich ($\theta_0$, Eq. 12.4):**

  $$
  \theta_0 = 280.46061837^\circ + 360.98564736629^\circ(JD - 2451545.0) + 0.000387933^\circ T^2 - \frac{T^3}{38710000}
  $$
* **Local Hour Angle ($H$) with East-positive longitude ($L_{\text{east}}$):**

  $$
  H = \theta_0 + L_{\text{east}} - \alpha
  $$
* **True Geometric Altitude ($h_0$, Eq. 13.6) and Compass Azimuth ($A_{\text{north}}$, Eq. 13.5):**

  $$
  \sin(h_0) = \sin(\phi)\sin(\delta) + \cos(\phi)\cos(\delta)\cos(H)
  $$

  $$
  \tan(A_{\text{south}}) = \frac{\sin(H)}{\cos(H)\sin(\phi) - \tan(\delta)\cos(\phi)}, \quad A_{\text{north}} = (A_{\text{south}} + 180^\circ) \pmod{360^\circ}
  $$

#### 5. Atmospheric Refraction — *Chapter 16 (Saemundsson's Formula, Eq. 16.4)*

$$
R_{\text{arcmin}} = \frac{1.02}{\tan\left(h_0 + \frac{10.3}{h_0 + 5.11}\right)}, \quad h_{\text{apparent}} = h_0 + \frac{R_{\text{arcmin}}}{60}
$$

#### 6. Equation of Time ($E$) & Rising/Transit/Setting — *Chapter 28 (Eq. 28.3) & Chapter 15 (Eq. 15.1)*

* **Equation of Time ($E$):**
  With $y = \tan^2(\varepsilon / 2)$:

  $$
  E_{\text{rad}} = y\sin(2L_0) - 2e\sin(M) + 4ey\sin(M)\cos(2L_0) - \frac{1}{2}y^2\sin(4L_0) - \frac{5}{4}e^2\sin(2M)
  $$
* **Sunrise, Sunset, and Twilights Hour Angle ($H_0$, Eq. 15.1):**

  $$
  \cos(H_0) = \frac{\sin(h_{\text{target}}) - \sin(\phi)\sin(\delta)}{\cos(\phi)\cos(\delta)}
  $$

  Where $h_{\text{target}}$ is $-0.8333^\circ$ (sunrise/sunset), $-6^\circ$ (civil), $-12^\circ$ (nautical), and $-18^\circ$ (astronomical).

---

<a name="documentation-française"></a>

## Documentation Française

**Helios** est une intégration personnalisée pour Home Assistant, sans aucune bibliothèque tierce, qui calcule la position du soleil et les heures solaires quotidiennes en appliquant les équations de **Jean Meeus (*Astronomical Algorithms*, 2e édition, Willmann-Bell, 1998)**.

### Caractéristiques principales

* **Zéro dépendance externe :** Utilise exclusivement les modules standards `math` et `datetime` de Python (`"requirements": []` dans `manifest.json`).
* **Maintenance simplifiée :** Le fichier `solar_engine.py` est totalement indépendant de Home Assistant. Vous pouvez le tester ou le modifier directement avec Python.
* **Données complètes :** Azimut, élévation apparente et géométrique vraie, déclinaison, ascension droite, équation du temps, distance Terre-Soleil (UA), Jour Julien, midi solaire, lever/coucher du soleil et crépuscules civil, nautique et astronomique.

### Références des équations pour vérification

Toutes les formules codées dans `custom_components/helios/solar_engine.py` suivent l'ouvrage **Jean Meeus, *Astronomical Algorithms*, 2nd Edition (1998)** :

1. **Jour Julien ($JD$) et Siècle Julien ($T$) :** Chapitre 7 (Éq. 7.1, p. 61) et Chapitre 25 (Éq. 25.1, p. 163).
2. **Longitude moyenne ($L_0$), Anomalie moyenne ($M$) et Excentricité ($e$) :** Chapitre 25 (Éq. 25.2, 25.3 et 25.4, p. 163).
3. **Équation du centre ($C$), Distance ($R$) et Longitude apparente ($\lambda$) :** Chapitre 25 (Éq. 25.5 et 25.8, p. 164).
4. **Obliquité de l'écliptique ($\varepsilon_0, \varepsilon$) :** Chapitre 22 (Éq. 22.2, p. 147) et Chapitre 25 (Éq. 25.8, p. 165).
5. **Coordonnées équatoriales (Ascension droite $\alpha$ et Déclinaison $\delta$) :** Chapitre 25 (Éq. 25.6 et 25.7, p. 165).
6. **Temps sidéral à Greenwich ($\theta_0$) :** Chapitre 12 (Éq. 12.4, p. 88).
7. **Coordonnées horizontales locales (Azimut $A$ et Hauteur vraie $h_0$) :** Chapitre 13 (Éq. 13.5 et 13.6, p. 93). *Note : Jean Meeus mesure l'azimut à partir du Sud vers l'Ouest ; le moteur y ajoute $180^\circ \pmod{360^\circ}$ pour fournir l'azimut géographique standard (Nord = $0^\circ$, Est = $90^\circ$).*
8. **Réfraction atmosphérique ($R$) :** Chapitre 16 (Formule de Saemundsson, Éq. 16.4, p. 106).
9. **Équation du temps ($E$) :** Chapitre 28 (Éq. 28.3, p. 185).
10. **Lever, passage au méridien et coucher ($H_0$) :** Chapitre 15 (Éq. 15.1, p. 101-103) avec double itération pour affiner la déclinaison et l'équation du temps à l'instant exact de chaque événement.

### Installation via HACS ou Manuelle

1. **Via HACS :** Ajoutez `https://github.com/Greg50100/Helios` en tant que dépôt personnalisé (*Custom Repository*, catégorie *Integration*), puis installez **Helios**.
2. **Manuelle :** Copiez le dossier `custom_components/helios` dans le répertoire `custom_components/` de votre configuration Home Assistant, puis redémarrez Home Assistant.
3. Allez dans **Paramètres -> Appareils et services -> Ajouter une intégration** et recherchez **Helio**


# Helios - Jean Meeus Solar Integration for Home Assistant

*Read this in: [English](#english-documentation) | [Français](#documentation-française)*

---

<a name="english-documentation"></a>

## 🇬🇧 English Documentation

**Helios** is a lightweight, zero-dependency Home Assistant custom integration that calculates solar position and daily solar events using the astronomical equations from **Jean Meeus's *Astronomical Algorithms* (2nd Edition, Willmann-Bell, 1998)**.

### Key Features

* **Zero External Dependencies:** Uses exclusively Python's standard `math` and `datetime` libraries (`"requirements": []` in `manifest.json`).
* **Decoupled Architecture:** `solar_engine.py` has zero Home Assistant imports, making unit testing and equation auditing effortless.
* **Complete Solar Metrics:** Azimuth, apparent and geometric elevation, declination, right ascension, equation of time, Earth-Sun distance (AU), Julian Day, solar noon, sunrise/sunset, and civil/nautical/astronomical twilights.

### Mathematical Reference & Equations Audit

All calculations implemented in `custom_components/helios/solar_engine.py` can be verified against **Jean Meeus, *Astronomical Algorithms*, 2nd Edition (1998)**:

#### 1. Julian Day ($JD$) and Julian Century ($T$) — *Chapter 7 (Eq. 7.1) & Chapter 25 (Eq. 25.1)*

For a given UTC date $(Y, M, D)$ with decimal day $D$ (if $M \le 2$, $Y \leftarrow Y-1$ and $M \leftarrow M+12$):

$$
A = \lfloor Y / 100 \rfloor, \quad B = 2 - A + \lfloor A / 4 \rfloor
$$

$$
JD = \lfloor 365.25 (Y + 4716) \rfloor + \lfloor 30.6001 (M + 1) \rfloor + D + B - 1524.5
$$

$$
T = \frac{JD - 2451545.0}{36525}
$$

#### 2. Solar Coordinates — *Chapter 25 (Eq. 25.2 to 25.8)*

* **Geometric Mean Longitude of the Sun ($L_0$, Eq. 25.2):**
  $$
  L_0 = 280.46646^\circ + 36000.76983^\circ T + 0.0003032^\circ T^2 \pmod{360^\circ}
  $$
* **Mean Anomaly of the Sun ($M$, Eq. 25.3):**
  $$
  M = 357.52911^\circ + 35999.05029^\circ T - 0.0001537^\circ T^2 \pmod{360^\circ}
  $$
* **Eccentricity of Earth's Orbit ($e$, Eq. 25.4):**
  $$
  e = 0.016708634 - 0.000042037 T - 0.0000001267 T^2
  $$
* **Sun's Equation of the Center ($C$, p. 164):**
  $$
  C = (1.914602^\circ - 0.004817^\circ T - 0.000014^\circ T^2)\sin(M) + (0.019993^\circ - 0.000101^\circ T)\sin(2M) + 0.000289^\circ\sin(3M)
  $$
* **True Longitude ($\odot$), True Anomaly ($v$), and Earth-Sun Distance ($R$ in AU, Eq. 25.5):**
  $$
  \odot = L_0 + C, \quad v = M + C, \quad R = \frac{1.000001018(1 - e^2)}{1 + e\cos(v)}
  $$
* **Apparent Longitude ($\lambda$, Eq. 25.8):**
  $$
  \Omega = 125.04^\circ - 1934.136^\circ T, \quad \lambda = \odot - 0.00569^\circ - 0.00478^\circ\sin(\Omega)
  $$

#### 3. Obliquity of the Ecliptic & Equatorial Coordinates — *Chapter 22 (Eq. 22.2) & Chapter 25 (Eq. 25.6–25.8)*

* **Mean ($\varepsilon_0$) and Corrected Obliquity ($\varepsilon$):**

  $$
  \varepsilon_0 = 23^\circ 26' 21.448'' - 46.8150'' T - 0.00059'' T^2 + 0.001813'' T^3
  $$

  $$
  \varepsilon = \varepsilon_0 + 0.00256^\circ\cos(\Omega)
  $$
* **Right Ascension ($\alpha$, Eq. 25.6) and Declination ($\delta$, Eq. 25.7):**

  $$
  \tan(\alpha) = \frac{\cos(\varepsilon)\sin(\lambda)}{\cos(\lambda)}, \quad \sin(\delta) = \sin(\varepsilon)\sin(\lambda)
  $$

#### 4. Sidereal Time & Horizontal Coordinates (Azimuth & Elevation) — *Chapter 12 (Eq. 12.4) & Chapter 13 (Eq. 13.5–13.6)*

* **Mean Sidereal Time at Greenwich ($\theta_0$, Eq. 12.4):**

  $$
  \theta_0 = 280.46061837^\circ + 360.98564736629^\circ(JD - 2451545.0) + 0.000387933^\circ T^2 - \frac{T^3}{38710000}
  $$
* **Local Hour Angle ($H$) with East-positive longitude ($L_{\text{east}}$):**

  $$
  H = \theta_0 + L_{\text{east}} - \alpha
  $$
* **True Geometric Altitude ($h_0$, Eq. 13.6) and Compass Azimuth ($A_{\text{north}}$, Eq. 13.5):**

  $$
  \sin(h_0) = \sin(\phi)\sin(\delta) + \cos(\phi)\cos(\delta)\cos(H)
  $$

  $$
  \tan(A_{\text{south}}) = \frac{\sin(H)}{\cos(H)\sin(\phi) - \tan(\delta)\cos(\phi)}, \quad A_{\text{north}} = (A_{\text{south}} + 180^\circ) \pmod{360^\circ}
  $$

#### 5. Atmospheric Refraction — *Chapter 16 (Saemundsson's Formula, Eq. 16.4)*

$$
R_{\text{arcmin}} = \frac{1.02}{\tan\left(h_0 + \frac{10.3}{h_0 + 5.11}\right)}, \quad h_{\text{apparent}} = h_0 + \frac{R_{\text{arcmin}}}{60}
$$

#### 6. Equation of Time ($E$) & Rising/Transit/Setting — *Chapter 28 (Eq. 28.3) & Chapter 15 (Eq. 15.1)*

* **Equation of Time ($E$):**
  With $y = \tan^2(\varepsilon / 2)$:
  $$
  E_{\text{rad}} = y\sin(2L_0) - 2e\sin(M) + 4ey\sin(M)\cos(2L_0) - \frac{1}{2}y^2\sin(4L_0) - \frac{5}{4}e^2\sin(2M)
  $$
* **Sunrise, Sunset, and Twilights Hour Angle ($H_0$, Eq. 15.1):**
  $$
  \cos(H_0) = \frac{\sin(h_{\text{target}}) - \sin(\phi)\sin(\delta)}{\cos(\phi)\cos(\delta)}
  $$

  Where $h_{\text{target}}$ is $-0.8333^\circ$ (sunrise/sunset), $-6^\circ$ (civil), $-12^\circ$ (nautical), and $-18^\circ$ (astronomical).

---

<a name="documentation-française"></a>

## 🇫🇷 Documentation Française

**Helios** est une intégration personnalisée pour Home Assistant, sans aucune bibliothèque tierce, qui calcule la position du soleil et les heures solaires quotidiennes en appliquant les équations de **Jean Meeus (*Astronomical Algorithms*, 2e édition, Willmann-Bell, 1998)**.

### Caractéristiques principales

* **Zéro dépendance externe :** Utilise exclusivement les modules standards `math` et `datetime` de Python (`"requirements": []` dans `manifest.json`).
* **Maintenance simplifiée :** Le fichier `solar_engine.py` est totalement indépendant de Home Assistant. Vous pouvez le tester ou le modifier directement avec Python.
* **Données complètes :** Azimut, élévation apparente et géométrique vraie, déclinaison, ascension droite, équation du temps, distance Terre-Soleil (UA), Jour Julien, midi solaire, lever/coucher du soleil et crépuscules civil, nautique et astronomique.

### Références des équations pour vérification

Toutes les formules codées dans `custom_components/helios/solar_engine.py` suivent l'ouvrage **Jean Meeus, *Astronomical Algorithms*, 2nd Edition (1998)** :

1. **Jour Julien ($JD$) et Siècle Julien ($T$) :** Chapitre 7 (Éq. 7.1, p. 61) et Chapitre 25 (Éq. 25.1, p. 163).
2. **Longitude moyenne ($L_0$), Anomalie moyenne ($M$) et Excentricité ($e$) :** Chapitre 25 (Éq. 25.2, 25.3 et 25.4, p. 163).
3. **Équation du centre ($C$), Distance ($R$) et Longitude apparente ($\lambda$) :** Chapitre 25 (Éq. 25.5 et 25.8, p. 164).
4. **Obliquité de l'écliptique ($\varepsilon_0, \varepsilon$) :** Chapitre 22 (Éq. 22.2, p. 147) et Chapitre 25 (Éq. 25.8, p. 165).
5. **Coordonnées équatoriales (Ascension droite $\alpha$ et Déclinaison $\delta$) :** Chapitre 25 (Éq. 25.6 et 25.7, p. 165).
6. **Temps sidéral à Greenwich ($\theta_0$) :** Chapitre 12 (Éq. 12.4, p. 88).
7. **Coordonnées horizontales locales (Azimut $A$ et Hauteur vraie $h_0$) :** Chapitre 13 (Éq. 13.5 et 13.6, p. 93). *Note : Jean Meeus mesure l'azimut à partir du Sud vers l'Ouest ; le moteur y ajoute $180^\circ \pmod{360^\circ}$ pour fournir l'azimut géographique standard (Nord = $0^\circ$, Est = $90^\circ$).*
8. **Réfraction atmosphérique ($R$) :** Chapitre 16 (Formule de Saemundsson, Éq. 16.4, p. 106).
9. **Équation du temps ($E$) :** Chapitre 28 (Éq. 28.3, p. 185).
10. **Lever, passage au méridien et coucher ($H_0$) :** Chapitre 15 (Éq. 15.1, p. 101-103) avec double itération pour affiner la déclinaison et l'équation du temps à l'instant exact de chaque événement.

### Installation

1. Copiez le dossier `custom_components/helios` dans le répertoire `custom_components/` de votre configuration Home Assistant.
2. Redémarrez Home Assistant.
3. Allez dans **Paramètres -> Appareils et services -> Ajouter une intégration** et recherchez **Helios**.
