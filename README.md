# agent-vdesktop

MCP-Server, mit dem ein AI-Agent **Microsoft Virtual Desktops auf Windows 11** steuern kann: Desktops erstellen/wechseln, Layouts anwenden (Spalten, Grid, Multi-Monitor), Chrome/Terminal/VS Code in einen Slot starten, Apps über mehrere Desktops pinnen, Fenster nach Label oder Inhalt addressieren.

Funktioniert nativ unter Windows und aus WSL heraus.

## Install (Claude Code)

```
/plugin marketplace add Seretos/agent-marketplace
/plugin install agent-vdesktop@agent-marketplace
```

Das wars. Kein Python, kein `pip install` — die `.exe` ist self-contained.

## Ausprobieren

Sag dem Agent z.B.:

> erstelle einen Desktop "demo", 3-Spalten-Layout, links Chrome, mitte ein Terminal, rechts VS Code

## Aus dem Source bauen

```powershell
py -3 -m pip install -e ".[build]"
.\scripts\build.ps1 -Clean -Package
```

Benötigt Python 3.11+. Output: `bin/vdesktop.exe` + `dist/vdesktop-plugin-<version>.zip`.
