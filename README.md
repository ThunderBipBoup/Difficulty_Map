# Difficulty Map / Carte de Difficulté
## English Version

### Project Overview

This project is a tool for analyzing terrain difficulty based on trails, roads, and slope data. Users can select a study area, generate study points, and compute local difficulty metrics considering distance, slope, and trail connectivity.

### Features

- Interactive study area selection
- Random or user-imported study points
- Terrain slope visualization
- Trail and road network analysis
- Difficulty computation (on-trail and off-trail weights)
- Export results as CSV and shapefiles
- Optional buffer grid analysis

### Run the App

#### 1st option : via streamlit
You can use the app on https://thunderbipboup-difficulty-map-difficulty-mapappmain-page-jo91ka.streamlit.app/.

#### 2nd option : clone or download ZIP, via github

Python must be installed. Version 3.12.3 of python was used for the development.

   ```bash
   git clone https://github.com/ThunderBipBoup/Difficulty_Map.git
   cd Difficulty_Map
   ```
   
Use the provided **run_app.command** (Mac) or **run_app.bat**(Windows) scripts for a click-and-run experience.

When you have finished using the programme, simply close the browser window and press Ctrl+C in the terminal.

![running the app gif](rm_gif/extrait1.gif)

#### 3rd option : running the app manually

Same first steps as 2nd option, then in the terminal console:

#### Mac / Linux:

```bash
python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt

streamlit run difficulty_map/app/Main_page.py
```

#### Windows:

```bash
python -m venv venv
call venv\Scripts\activate.bat
pip install -r requirements.txt

streamlit run difficulty_map/app/Main_page.py
```


### Usage

1. In the main page, select the study area and starting point.

    You can check the box "Show Slope" to verify that your study area is in the slope raster range. Otherwise it won't work.

![select a study area](rm_gif/extrait2.gif)

2. Optionally enable buffer analysis.

3. Confirm study points or import your CSV.

![study points](rm_gif/extrait-3.gif)

4. Adjust weights for difficulty computation.

5. Visualize results and download CSV/shapefiles.

### In details 

#### Main page
Study area is the red square on the large map, whose size and position can be adjusted. If this area does not overlap the slope raster, there will be an error.
Bear in mind that the algorithm is aware of roads outside the study area, but not of trails. So if a trail is not included in the study area, it is not taken into account when calculating paths and difficulties.

You can adjust the position of the User starting point (black star) throughout the map. The position of the Projected on road (red cross) is not directly adjustable, but results from the position of the User starting point: it is projected onto the nearest road. The Projected on road position will be used as the starting point on the road, to then calculate the distance travelled on the road to reach each point.

Trail connection threshold: this is the maximum distance between 2 trails for them to be considered connected. Road connection threshold is the maximum distance between a trail and a road for them to be considered connected.

By ticking enable buffer, you can set buffer width and cell size. The buffer is an area around the trails that is divided into cells, and the average difficulty of each cell is calculated and displayed, taking into account the difficulty already calculated for arriving at the nearest trail point, and the difficulty of getting from the trail to the cell.

The show slope box displays the slope on the large map, as well as on the map obtained when Confirm Study Area and Starting Point is ticked. 

#### Study points

You can choose points (their name and position), and by confirming them they will be displayed on the map below. Be careful not to select them in a Study area and then change area afterwards, otherwise the display will be stretched.

You can import a CSV file of points, but you need to be careful about the format, and you need at least one X column and one Y column (name column optional), and ‘;’ as a column delimiter.

If the difficulty has already been calculated in the zone where the points are located, a table of the different metrics for each point will be displayed. 

The total difficulty can be weighted using Weight on trails and Weight off trails. These weights will also affect the difficulty calculation for the cells, if Enable buffer is ticked. However, they will not affect the other metrics in the table.



### Potential upgrade

To **change maps**, simply change the global COUNTRY variable to ‘fr’ or ‘it’. there are currently 2 data sets, a map of a reserve in Alsace (France), and a map of a park in the Carsia mountains (Italy). 

You can add a dataset but you need to make sure that the files are in the right formats, set the reference frames (crs) correctly, and it's better if they have the same size (also, the altitude raster needs to be transformed into a slope raster).

An improvement would be to manage all this in Streamlit.

### Author

Copyright (C) 2025  Emma DELAHAIE

This program comes with ABSOLUTELY NO WARRANTY.
This is free software, and you are welcome to redistribute it
under certain conditions. See LICENSE.txt for details.

If there is any issue or question, do not hesitate to pull a request !
----------
----------

## Version française

### Aperçu du projet

Ce projet est un outil d'analyse de la difficulté du terrain basé sur des données relatives aux sentiers, aux routes et aux pentes. Les utilisateurs peuvent sélectionner une zone d'étude, générer des points d'étude et calculer la difficulté locale et autres métriques en tenant compte de la distance, de la pente et de la connectivité des sentiers.

### Caractéristiques

- Sélection interactive de la zone d'étude
- Points d'étude aléatoires ou importés par l'utilisateur
- Visualisation de la pente du terrain
- Analyse du réseau de sentiers et de routes
- Calcul de la difficulté (pondération sur piste et hors piste)
- Exportation des résultats au format CSV et shapefiles
- Analyse de la grille tampon optionnelle

### Exécuter l'application

#### 1ère option : via streamlit
Vous pouvez utiliser l'application sur https://thunderbipboup-difficulty-map-difficulty-mapappmain-page-jo91ka.streamlit.app/.

#### 2ème option : cloner ou télécharger le ZIP, via github
Python doit être installé. La version 3.12.3 de python a été utilisée pour le développement.

Double_cliquez sur les scripts **run_app.command** (Mac) ou **run_app.bat** (Windows) fournis pour lancer directement l'application.

#### 3ème option : exécuter l'application manuellement

Mêmes étapes que pour la 2ème option, mais dans la console du terminal :

#### Mac / Linux :

```bash
python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt

streamlit run difficulty_map/app/Main_page.py
````

#### Windows :

```bash
python -m venv venv
call venv\Scripts\activate.bat
pip install -r requirements.txt

streamlit run difficulty_map/app/Main_page.py
```




### Utilisation

1. Dans la page principale, sélectionnez la zone d'étude et le point de départ.

    Vous pouvez cocher la case "Show Slope" pour vérifier que votre zone d'étude se trouve dans la gamme de rasters de pente. Sinon, cela ne fonctionnera pas.

2. Activez éventuellement l'analyse des zones tampons.

3. Confirmez les points d'étude ou importez votre CSV.

4. Ajustez les poids pour le calcul de la difficulté.

5. Visualiser les résultats et télécharger les fichiers CSV/de forme.

### Plus de détails

#### Main page

Study area est le carré rouge sur la grande carte, dont on peut régler la taille et la position. Si cette zone ne recouvre pas le raster de pente, il y aura une erreur.
Il faut garder en tête que l’algorithme a conscience des routes en dehors de la study area, mais pas des trails. Donc si un trail n’est pas pris dans la study area, il n’est pas considéré dans le calcul des chemins et des difficultés.

On peut régler la position de User starting point (étoile noire) sur toute la carte. La position de Projected on road (croix rouge) n’est pas directement réglable, elle, mais résulte de la position de User starting point : elle est son projeté sur la route la plus proche. La position Projected on road sera utilisée comme point de départ sur la route, pour ensuite calculer la distance parcourue sur la route pour atteindre chaque point.

On peut régler Trail connection threshold : c’est la distance maximale entre 2 trails pour qu’ils soient considérés comme reliés. Road connection threshold est la distance maximale entre un sentier et une route pour qu’ils soient considérés comme reliés.

En cochant enable buffer, on peut régler buffer width et cell size. Le buffer est une zone autour des sentiers qui est divisé en cellules, et la difficulté moyenne de chaque cellule est calculée et affichée, en prenant en compte la difficulté déjà calculée pour arriver sur le point de sentier le plus proche, et la difficulté pour aller du sentier à la cellule. 

La case Show slope permet d’afficher la pente sur la grande carte, mais aussi sur la carte qu’on obtient quand on coche Confirm Study Area and Starting Point. 

#### Study points

On peut choisir des points (leur nom et leur position), en les confirmant ils s’afficheront sur la carte d’en dessous. Il faut faire attention à ne pas les choisir dans une Study area puis changer de zone après, car sinon l’affichage sera étiré.

On peut importer un fichier CSV de points, mais il faut faire attention au format, et il faut au moins une colonne X et une colonne Y (colonne name facultative), et « ; » en délimiteur de colonne.

Si le calcul de difficulté dans la zone où sont les points a déjà été effectué, un tableau des différentes métriques pour chaque point s’affichera. 

La difficulté totale peut être pondérée à  l’aide de Weight on trails et de Weight off trails. Ces poids impacteront également le calcul de difficulté pour les cellules, si on coche Enable buffer. Cependant ils n’affecteront pas les autres métriques du tableau.



### Amélioration potentielle

Pour **changer de carte**, il suffit de changer la variable globale COUNTRY en "fr" ou "it". Il y a actuellement 2 jeux de données, une carte d'une réserve en Alsace (France), et une carte d'un parc dans les montagnes de Carsia (Italie).

Il est possible d'ajouter un jeu de données mais vous devez vous assurer que les fichiers sont dans les bons formats, que les cadres de référence (crs) sont corrects, et qu'ils ont la même taille (également, le raster d'altitude doit être transformé en raster de pente).

Une amélioration serait de gérer tout cela dans Streamlit.

### Auteur

Copyright (C) 2025 Emma DELAHAIE

Ce programme n'est assorti d'AUCUNE GARANTIE.
Il s'agit d'un logiciel libre, et vous pouvez le redistribuer sous certaines conditions. Voir LICENSE.txt pour plus de détails.

Si vous avez un problème ou une question, n'hésitez pas à "pull a request" !