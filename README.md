# NHMzh Übersicht Module Kosten & LCA mit Docker

> **Hinweis**: Für detaillierte Informationen zu den einzelnen Modulen, bitte die [README.md im modules Verzeichnis](modules/README.md) beachten.

> **Hinweis**: Für detaillierte Informationen zur Verwendung der Skripte, siehe die [README.md im scripts Verzeichnis](scripts/README.md).

## Verzeichnisstruktur

[**NHMzh-modules/data/**](data/): Enthält Eingabedaten und generierte Ausgabedateien.

- [**NHMzh-modules/data/input/**](data/input/): Rohdaten
  - [`control_file.xlsx`](data/input/control_file.xlsx)
  - [`KBOB.csv`](data/input/KBOB.csv)
  - [`CostDB.csv`](data/input/CostDB.csv)
  - [`amortization_periods.csv`](data/input/amortization_periods.csv)
- [**NHMzh-modules/data/output/**](data/output/): Generierte Ergebnisdaten
  - [`lca_results.json`](data/output/lca_results.json)
  - [`cost_results.json`](data/output/cost_results.json)
  - [`combined_results.json`](data/output/combined_results.json)
  - [`summary_report.txt`](data/output/summary_report.txt)
- [**NHMzh-modules/data/output/qa/**](data/output/qa/): Kontrolldaten zur Überprüfung der Resultate etc.

[**NHMzh-modules/modules/**](modules/): Spezifische Module zur Ausführung von Berechnungen.

- [`lca_processor.py`](modules/lca_processor.py): Modul für Lebenszyklusbewertung.
- [`cost_processor.py`](modules/cost_processor.py): Modul für die Kostenberechnung.
- [`base_processor.py`](modules/base_processor.py): Basismodul, von dem andere erben.
- [`README.md`](modules/README.md): Detaillierte Dokumentation der Module.

[**NHMzh-modules/scripts/**](scripts/): Enthält Skripte, um die Module zu starten.

- [`run_processors.py`](scripts/run_processors.py): Hauptskript, das `LCAProcessor` und `CostProcessor` ausführt, Ergebnisse kombiniert und speichert.
- [`dataset_gen.py`](scripts/dataset_gen.py): Skript zur Generierung grosser Testdatensätze.
- [`profiler.py`](scripts/profiler.py): Skript zur Leistungsanalyse der Module.
- [`generate_summary.py`](scripts/generate_summary.py): Skript zur Erstellung von Zusammenfassungsberichten.
- [`README.md`](scripts/README.md): Detaillierte Dokumentation

[**NHMzh-modules/utils/**](utils/): Hilfsfunktionen zur Unterstützung der Module.

- [`shared_utils.py`](utils/shared_utils.py): Allgemeine Hilfsfunktionen wie `load_data()`, `save_data_to_json()`, etc.

## Module

Für eine detaillierte Beschreibung der Module, siehe die [README.md im modules Verzeichnis](modules/README.md).

### [`LCAProcessor`](modules/lca_processor.py)

Berechnet der Ökobilanz (LCA) für Bauteile und Bauteilschichten.

### [`CostProcessor`](modules/cost_processor.py)

Berechnet die prognostizierten Kosten für Bauprojekte.

### [`BaseProcessor`](modules/base_processor.py)

ist eine abstrakte Basisklasse, die die gemeinsame Struktur für alle Module bereitstellt.

## Benutzung

### Lokale Ausführung

Im Hauptverzeichnis des Projekts (NHMzh) folgenden Befehl ausführen:

```bash
python NHMzh-modules/scripts/run_processors.py data/input/control_file.xlsx
```

### Docker-Ausführung

1. Docker-Image erstellen (nicht vergessen!):

```bash
docker build -t nhmzh-modules .
```

2. Container ausführen:

```bash
docker run --rm -v ${PWD}/data:/app/data nhmzh-modules control_file.xlsx
```

Für Windows PowerShell:

```powershell
docker run --rm -v ${PWD}\data:/app/data nhmzh-modules control_file.xlsx
```

Für Windows Command Prompt (CMD):

```cmd
docker run --rm -v %cd%\data:/app/data nhmzh-modules control_file.xlsx
```

Mountet das `data`-Verzeichnis vom Host-System in den Container. So kann der Container Eingabedateien lesen und Ausgabedateien schreiben.

## Fehlerbehandlung

- **Fehlende Daten**: Fehler werden im `main()`-Funktionsblock abgefangen und protokolliert.
- **Umgang mit Fehlern**: Bauteile oder Schichten mit Fehlern werden markiert und die Ergebnisse beinhalten sowohl erfolgreiche als auch fehlgeschlagene Bauteile/Bauteilschichten.
