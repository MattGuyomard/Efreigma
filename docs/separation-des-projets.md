# Séparation des projets — 26 octobre 2026

`Efreigma` est le projet Python de stéganographie ; `STLO` est le jeu Roblox. Leurs dépôts Git et remotes distincts ont été conservés, sans commit ni push.

Les anciens fichiers Roblox présents ici ont été déplacés vers :

`C:/Users/Nawad/OneDrive - Efrei/STLO/.local-backups/separation-efreigma-20261026/`

| Ancien emplacement dans Efreigma | Archive locale dans ce dossier |
|---|---|
| `roblox/` | `roblox/` |
| `Knowledge-Base/` | `Knowledge-Base-historique/` |
| `blender-skills/` | `blender-skills/`, dépôt Git imbriqué conservé |
| `output/map-concept/` | `map-concept/` |
| `AGENTS.md` orienté Roblox | `AGENTS-Roblox-original.md` |

Le manifeste `manifest.json` enregistre les chemins source/destination et les SHA-256. Il permet une restauration explicite fichier par fichier. L'archive est ignorée par le Git de STLO, car les anciens exports peuvent contenir des données privées. Ne pas l'ajouter de force à Git.

L'ancienne base Obsidian n'a pas été fusionnée avec celle de STLO : la documentation maintenue du jeu reste `STLO/Knowledge-Base`. Les versions historiques restent accessibles dans l'archive.

Le code Python, `assets/`, `docs/` techniques, `examples/`, `tests/`, `views/`, les dépendances et les paramètres Streamlit ont été conservés. Le style scolaire de l'interface Python ne constitue pas un fichier Roblox. Les skills Blender installés dans le profil utilisateur sont des copies indépendantes du dépôt archivé.

Aucun script du jeu, mapping Rojo, profil joueur, remote Git ou configuration MCP globale n'a été modifié par cette séparation.

Vérifications : 2 224 fichiers archivés (437 437 690 octets), toutes les empreintes conformes ; 44 fichiers Python conservés identiques. Après séparation : **169 tests Pytest réussis**, code de sortie 0. Les instructions et cette note sont les seuls nouveaux fichiers du projet Python ajoutés par l'opération.
