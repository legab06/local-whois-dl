# local-whois-dl

Petite application Streamlit destinée à préparer un bundle de données IP/WHOIS compatible avec **$whoami - Lookup**.

L'application télécharge uniquement des sources officielles prédéfinies :

- les 6 dumps RIPE NCC utilisés par le constructeur IPDB de `$whoami` ;
- le rapport mondial NRO `delegated-extended`.

Elle valide les fichiers téléchargés, calcule leur SHA-256, génère un `manifest.json`, puis crée une archive ZIP que l'utilisateur peut importer localement.

## Sources incluses

RIPE NCC :

- `ripe.db.organisation.gz`
- `ripe.db.aut-num.gz`
- `ripe.db.inetnum.gz`
- `ripe.db.inet6num.gz`
- `ripe.db.route.gz`
- `ripe.db.route6.gz`

NRO :

- `nro-delegated-stats`

Aucune URL fournie par l'utilisateur n'est exécutée ou téléchargée.

## Lancer localement

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Sous Windows PowerShell :

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

## Déploiement Streamlit Community Cloud

1. connecter ce dépôt à Streamlit Community Cloud ;
2. choisir `app.py` comme fichier principal ;
3. déployer.

Aucun secret n'est nécessaire.

## Sécurité et intégrité

- liste blanche d'URLs officielles ;
- téléchargement HTTP(S) en streaming, sans shell ;
- taille maximale par source ;
- contrôle de la signature gzip pour les dumps RIPE ;
- contrôle minimal de l'en-tête NRO ;
- SHA-256 de chaque fichier ;
- manifeste versionné ;
- répertoires temporaires isolés et nettoyage des anciens travaux.

## Format du bundle

Le ZIP produit contient les 7 fichiers sources ainsi qu'un `manifest.json`. Les fichiers RIPE gardent exactement les noms attendus par `$whoami`.

Le manifeste est prévu pour permettre ensuite à `$whoami` de vérifier la fraîcheur, l'intégrité et la compatibilité du bundle avant une installation atomique de la nouvelle IPDB.

## Développement

```bash
pip install -r requirements-dev.txt
pytest
```

Projet indépendant ; les données téléchargées restent la propriété et sous les conditions de leurs producteurs respectifs.
