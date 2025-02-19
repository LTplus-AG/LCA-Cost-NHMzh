# NHMzh Übersicht Module Kosten & LCA mit Docker

![Demo Web App zeigt Funktionsweise der Module als Mock Up](assets/Demo_webApp.gif)

_Mock-Up aus früher Projektphase, stellt nicht das endgültige Ergebnis dar._

> [!NOTE]
> Für detaillierte Informationen zu den einzelnen Modulen, bitte die [README.md im modules Verzeichnis](modules/README.md) beachten.

> [!NOTE]
> Für detaillierte Informationen zur Verwendung der Skripte, siehe die [README.md im scripts Verzeichnis](scripts/README.md).

### 📊 Eingabedaten

### 📁 NHMzh-modules/data/

Enthält Eingabedaten und generierte Ausgabedateien.

#### 📥 data/input/

Rohdaten:

- Haupteingabedatei mit IFC-Elementen und deren Materialien
- KBOB Materialdaten für LCA-Berechnungen (Umgebungsvariable: `KBOB_DATA_PATH`)
  - UUID-Nummer
  - Treibhausgasemissionen [kg CO2-eq]
  - Primärenergie nicht erneuerbar [kWh oil-eq]
  - UBP (Total)
  - BAUMATERIALIEN (Name)
  - Rohdichte/Flächenmasse
- Kostenkennwerte für Kostenberechnungen (Umgebungsvariable: `COST_DB_PATH`)
  - Code (eBKP-H)
  - Bezeichnung
  - Kennwert
  - reference (Einheit)
- Lebensdauer-Daten für Bauteile (Umgebungsvariable: `AMORTIZATION_PERIODS_PATH`)
  - eBKP-H Code
  - Description
  - Years
  - model-based?

#### 📤 data/output/

Generierte Ergebnisdaten:

- `nhmzh_data.duckdb` - DuckDB Datenbank mit allen Daten:

  - Referenzdaten (KBOB, Lebensdauer, Kosten)
  - Projektdaten (IFC-Elemente, Materialien)
  - Verarbeitungsergebnisse
  - Fehlerprotokolle und Historie

- Exportierte Daten (optional):

  - `kbob_materials.json` - KBOB Materialdaten
  - `life_expectancy.json` - Lebensdauer-Daten
  - `material_mappings.json` - Material-Mappings
  - Pro Projekt:
    - `project_{id}/project.json` - Projektinformationen
    - `project_{id}/ifc_elements.json` - IFC-Elemente
    - `project_{id}/element_materials.json` - Materialzuweisungen
    - `project_{id}/processing_results.json` - Berechnungsergebnisse
    - `project_{id}/processing_errors.json` - Fehlerprotokolle
    - `project_{id}/processing_history.json` - Verarbeitungshistorie

- MinIO Export (optional):
  - `/lca/{project_id}/{filename}_{timestamp}.parquet` - LCA-Berechnungsergebnisse
  - `/cost/{project_id}/{filename}_{timestamp}.parquet` - Kostenberechnungsergebnisse

### 📦 [modules/](modules/)

Spezifische Module zur Ausführung von Berechnungen:

- [`lca_processor.py`](modules/lca_processor.py): Modul für Lebenszyklusbewertung
- [`cost_processor.py`](modules/cost_processor.py): Modul für die Kostenberechnung
- [`base_processor.py`](modules/base_processor.py): Basismodul, von dem andere erben
- [`README.md`](modules/README.md): Detaillierte Dokumentation der Module

### 🛠️ [scripts/](scripts/)

Enthält Skripte für Datenmanagement und Verarbeitung:

- [`duckDB_import_export.py`](scripts/duckDB_import_export.py): Verwaltung der DuckDB-Datenbank und Referenzdaten
  - Laden von KBOB, Lebensdauer und Kostendaten
  - Import/Export von Projektdaten
  - Datenbank-Backup und -Wiederherstellung
- [`run_processors.py`](scripts/run_processors.py): Hauptskript für LCA- und Kostenberechnungen
  - Verarbeitung von IFC-Elementen
  - Berechnung von Umweltindikatoren und Kosten
  - Export nach DuckDB und optional MinIO
- [`dataset_gen.py`](scripts/dataset_gen.py): Generierung von Testdatensätzen
- [`profiler.py`](scripts/profiler.py): Leistungsanalyse der Module
- [`generate_summary.py`](scripts/generate_summary.py): Erstellung von Zusammenfassungsberichten

### ⚙️ [utils/](utils/)

Hilfsfunktionen zur Unterstützung der Module:

- [`shared_utils.py`](utils/shared_utils.py): Allgemeine Hilfsfunktionen
  - Datei-I/O Operationen
  - Datenvalidierung
  - Fehlerbehandlung

## Module

> Für eine detaillierte Beschreibung der Module, siehe die [README.md im modules Verzeichnis](modules/README.md).

### [`LCAProcessor`](modules/lca_processor.py)

Berechnet die Ökobilanz (LCA) für Bauteile und Bauteilschichten:

- Verarbeitung von IFC-Elementen und Materialien
- Integration mit KBOB-Daten und Lebensdauer-Informationen
- Berechnung von CO2-Äquivalenten, Primärenergie und UBP
- Speicherung in DuckDB und optionaler Export als Parquet

### [`CostProcessor`](modules/cost_processor.py)

Berechnet die prognostizierten Kosten für Bauprojekte:

- Verarbeitung von IFC-Elementen und eBKP-H Codes
- Integration mit Kostenkennwerten
- Mengenermittlung und Kostenberechnung
- Speicherung in DuckDB und optionaler Export als Parquet

### [`BaseProcessor`](modules/base_processor.py)

Abstrakte Basisklasse für die Prozessoren:

- Gemeinsame Datenbankfunktionalität
- Standardisierte Fehlerbehandlung
- MinIO-Integration für Parquet-Export
- Transaktionsmanagement

## Benutzung

### 💻 Lokale Ausführung

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

## MinIO Integration

Die MinIO-Integration ist optional und wird für den Export der DuckDB-Ergebnisse im Parquet-Format verwendet. Diese Ergebnisse werden direkt vom PowerBI-Dashboard verarbeitet.

```python
minio_config = {
    "endpoint": "play.min.io:9000",
    "access_key": "your_access_key",
    "secret_key": "your_secret_key",
    "secure": True,
    "bucket_name": "your-bucket-name"
}
```

### 📥 Verwendung mit Docker

MinIO-Konfiguration als Umgebungsvariablen setzen:

```bash
docker run --rm \
  -e MINIO_ENDPOINT="play.min.io:9000" \
  -e MINIO_ACCESS_KEY="your_access_key" \
  -e MINIO_SECRET_KEY="your_secret_key" \
  -e MINIO_BUCKET="your-bucket-name" \
  -v ${PWD}/data:/app/data nhmzh-modules control_file.xlsx
```

Die Berechnungsergebnisse werden in der DuckDB-Datenbank gespeichert und können optional als Parquet-Dateien nach MinIO exportiert werden. Die Parquet-Dateien sind optimiert für die Weiterverarbeitung im PowerBI-Dashboard.

## Datenbank

Das Projekt verwendet DuckDB als eingebettete Datenbank für die effiziente Verwaltung aller Daten. Die Implementierung bietet folgende Hauptfunktionen:

### 📊 Datenmodell

#### Referenzdaten

- **KBOB Materialien**: Versionierte Materialdaten mit Umweltindikatoren
- **Lebensdauer**: eBKP-H basierte Amortisationsperioden
- **Kostenkennwerte**: Versionierte Kostendaten pro eBKP-H Code

#### Projektdaten

- **Projekte**: Verwaltung von Projektmetadaten und Status
- **IFC-Elemente**: Detaillierte Bauteilinformationen
- **Materialzuweisungen**: Verknüpfung von IFC-Elementen mit Materialien
- **Verarbeitungsergebnisse**: LCA- und Kostenberechnungen
- **Fehlerprotokolle**: Detaillierte Fehlererfassung
- **Verarbeitungshistorie**: Tracking von Berechnungsprozessen

### 🔄 Datenbank-Management

Die Verwaltung erfolgt über das Skript `duckdb_import_export.py`, das folgende Hauptfunktionen bietet:

```bash
# Laden aller Referenzdaten
python scripts/duckDB_import_export.py load-all --version "2024-v1"

# Spezifische Daten laden
python scripts/duckDB_import_export.py load-kbob kbob_data.csv "2024-v1"
python scripts/duckDB_import_export.py load-life amortization_periods.csv
python scripts/duckDB_import_export.py load-mappings material_mappings.json

# Daten exportieren/importieren
python scripts/duckDB_import_export.py export output_dir/
python scripts/duckDB_import_export.py import input_dir/
```

### 🔄 Integration

- **MinIO-Export**: Optional als Parquet-Dateien
- **PowerBI-Anbindung**: Optimierte Datenstruktur für Analysen
- **Modulare Architektur**: Einfache Erweiterbarkeit
