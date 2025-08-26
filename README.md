# Difficulty Map / Carte de Difficulté
## English Version

### Project Overview

This project is a tool for analyzing terrain difficulty based on trails, roads, and slope data. Users can select a study area, generate study points, and compute local difficulty metrics considering distance, slope, and trail connectivity.

### Run the App

Python must be installed. Version 3.12.3 of python was used for the development.

Use the provided **run_app.command** (Mac) or **run_app.bat**(Windows) scripts for a click-and-run experience.

![running the app gif](https://github.com/ThunderBipBoup/Difficulty_Map/tree/main/rm_gif/extrait1.gif)

### Features

- Interactive study area selection

- Random or user-imported study points

- Terrain slope visualization

- Trail and road network analysis

- Difficulty computation (on-trail and off-trail weights)

- Export results as CSV and shapefiles

- Optional buffer grid analysis


### Usage

1. In the main page, select the study area and starting point.

    You can check the box "Show Slope" to verify that your study area is in the slope raster range. Otherwise it won't work.

2. Optionally enable buffer analysis.

3. Confirm study points or import your CSV.

4. Adjust weights for difficulty computation.

5. Visualize results and download CSV/shapefiles.


###  Running the app manually

Python must be installed. Version 3.12.3 of python was used for development

#### Mac / Linux:

```
python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt

streamlit run difficulty_map/app/Main_page.py
```

#### Windows:

```
python -m venv venv
call venv\Scripts\activate.bat
pip install -r requirements.txt

streamlit run difficulty_map/app/Main_page.py
```

----------
----------

## Version française

### Aperçu du projet

Ce projet est un outil d'analyse de la difficulté du terrain basé sur des données relatives aux sentiers, aux routes et aux pentes. Les utilisateurs peuvent sélectionner une zone d'étude, générer des points d'étude et calculer la difficulté locale et autres métriques en tenant compte de la distance, de la pente et de la connectivité des sentiers.

### Exécuter l'application

Python doit être installé. La version 3.12.3 de Python a été utilisée pour le développement.

Double_cliquez sur les scripts **run_app.command** (Mac) ou **run_app.bat** (Windows) fournis pour lancer directement l'application.

### Caractéristiques

- Sélection interactive de la zone d'étude

- Points d'étude aléatoires ou importés par l'utilisateur

- Visualisation de la pente du terrain

- Analyse du réseau de sentiers et de routes

- Calcul de la difficulté (pondération sur piste et hors piste)

- Exportation des résultats au format CSV et shapefiles

- Analyse de la grille tampon optionnelle

### Utilisation

1. Dans la page principale, sélectionnez la zone d'étude et le point de départ.

    Vous pouvez cocher la case "Show Slope" pour vérifier que votre zone d'étude se trouve dans la gamme de rasters de pente. Sinon, cela ne fonctionnera pas.

2. Activez éventuellement l'analyse des zones tampons.

3. Confirmez les points d'étude ou importez votre CSV.

4. Ajustez les poids pour le calcul de la difficulté.

5. Visualiser les résultats et télécharger les fichiers CSV/de forme.

### Exécution manuelle de l'application

Python doit être installé. La version 3.12.3 de python a été utilisée pour le développement.

#### Mac / Linux :

```
python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt

streamlit run difficulty_map/app/Main_page.py
```
#### Windows :
```
python -m venv venv
call venv\Scripts\activate.bat
pip install -r requirements.txt

streamlit run difficulty_map/app/Main_page.py
```