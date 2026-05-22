# Transparence conditionnelle sur les marchés des stablecoins

Ce dépôt est un paquet public de données et de code destiné à reproduire une étude auditée par les sources sur la divulgation des réserves des stablecoins. Il relie les index de divulgation des émetteurs, le codage RQI/DII revu par le chercheur, les panels quotidiens de marché, les diagnostics en fenêtre d'événement, les sorties de robustesse et les contrôles de portée des affirmations.

Cette version publique ne contient que des éléments vérifiables, réexécutables et extensibles. Seuls les données, le code, la documentation et les sorties dérivées de réplication sont inclus.

## Langues

| Langue | README |
|---|---|
| English | [../../README.md](../../README.md) |
| 中文 | [README.zh-CN.md](README.zh-CN.md) |
| 日本語 | [README.ja.md](README.ja.md) |
| Français | `README.fr.md` |
| Русский | [README.ru.md](README.ru.md) |

## Démarrage rapide

```powershell
python -m pip install -r requirements.txt
python scripts\check_public_release.py
python scripts\run_public_replication.py --mode smoke
```

Commandes principales :

```powershell
python scripts\run_public_replication.py --mode analysis
python scripts\run_public_replication.py --mode all
```

Les PDF, pages web sauvegardées et captures de sources tierces ne sont pas redistribués. Le paquet public conserve les URL, dates d'accès, statuts de source, identifiants d'événement et indicateurs de revue. Les résultats doivent être lus comme des diagnostics pilotes.
