# NHMzh Scripts

> **Hinweis**: Für eine Übersicht des gesamten Projekts, siehe die [Haupt-README.md](../README.md).

Dieses Verzeichnis enthält verschiedene Skripte zur Ausführung, Analyse und Unterstützung der NHMzh-Module.

## Skripte

### [`run_processors.py`](run_processors.py)

Hauptskript zur Ausführung der LCA- und Kostenberechnungen.

- **Zweck**: Verarbeitet Eingabedaten, führt LCA- und Kostenberechnungen durch und kombiniert die Ergebnisse.
- **Verwendung**: `python run_processors.py <Pfad_zur_Eingabedatei> `
- **Funktionen**:
  - Lädt Eingabedaten
  - Führt LCAProcessor und CostProcessor aus
  - Kombiniert und speichert die Ergebnisse

### [`dataset_gen.py`](dataset_gen.py)

Skript zur Generierung großer Testdatensätze.

- **Zweck**: Erstellt umfangreiche Datensätze für Leistungs- und Skalierungstests.
- **Verwendung**: `python dataset_gen.py `
- **Funktionen**:
  - Generiert zufällige, aber realistische Testdaten
  - Speichert den generierten Datensatz als CSV-Datei

### [`profiler.py`](profiler.py)

Skript zur Leistungsanalyse der Module.

- **Zweck**: Führt Leistungsprofile der Hauptfunktionen aus und generiert Berichte.
- **Verwendung**: `python profiler.py <Pfad_zur_Eingabedatei> `
- **Funktionen**:
  - Führt die Hauptverarbeitung mit Profiling aus
  - Generiert detaillierte Leistungsberichte
  - Speichert Profiling-Daten zur weiteren Analyse

### [`generate_summary.py`](generate_summary.py)

Skript zur Erstellung von Zusammenfassungsberichten.

- **Zweck**: Erstellt übersichtliche Zusammenfassungen der Berechnungsergebnisse.
- **Verwendung**: `python generate_summary.py `
- **Funktionen**:
  - Liest die kombinierten Ergebnisdaten
  - Berechnet Gesamtsummen und Statistiken
  - Generiert einen lesbaren Zusammenfassungsbericht

## Verwendung

Die Skripte sind für eine sequenzielle Ausführung konzipiert:

1. `dataset_gen.py` zur Erstellung von Testdaten (falls erforderlich).
2. `run_processors.py` zur Durchführung der Hauptberechnungen.
3. `profiler.py` zur Leistungsanalyse (optional).
4. `generate_summary.py` zur Erstellung eines Überblicks über die Ergebnisse.
