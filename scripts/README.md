# NHMzh Scripts

> [!NOTE]
> Für eine Übersicht des gesamten Projekts, siehe die [Haupt-README.md](../README.md).

## 🛠️ Skript-Sammlung

### 🗄️ `duckDB_import_export.py`

Verwaltungstool für die DuckDB-Datenbank. Bietet umfassende Funktionen für Import/Export und Datenverwaltung.

<details>
<summary><b>🔍 Implementierungsdetails</b></summary>

#### 📋 Hauptfunktionen

- **Referenzdaten laden**

  ```bash
  # Alle Referenzdaten laden
  python duckDB_import_export.py load-all --version "2024-v1"

  # KBOB-Daten laden
  python duckDB_import_export.py load-kbob KBOB.csv "2024-v1"

  # Lebensdauer-Daten laden
  python duckDB_import_export.py load-life amortization_periods.csv

  # Material-Mappings laden
  python duckDB_import_export.py load-mappings mappings.json
  ```

- **Daten exportieren/importieren**

  ```bash
  # Datenbank exportieren
  python duckDB_import_export.py export backup_dir

  # Datenbank importieren
  python duckDB_import_export.py import backup_dir
  ```

#### 🔧 Datenbank-Features

- Transaktionssicherheit
- Versionskontrolle für KBOB-Daten
- Automatische Indizierung
- Fehlerprotokollierung
- Batch-Verarbeitung

#### ⚠️ Fehlerbehandlung

- Datenvalidierung
- Transaktions-Rollback
- Detaillierte Fehlerprotokolle
- Automatische Bereinigung

</details>

### ⚡ `run_processors.py`

Hauptskript für LCA- und Kostenberechnungen. Verarbeitet IFC-Elemente und speichert Ergebnisse in DuckDB.

- Zentrale Steuerung der Berechnungsmodule
- Integrierte Datenverarbeitung
- Ergebniskombination und -speicherung
- Robuste Fehlerbehandlung

<details>
<summary><b>🔍 Implementierungsdetails</b></summary>

#### �� Hauptfunktionen

- Verarbeitung von IFC-Elementen
- Integration mit Referenzdaten
- Berechnung von Umweltindikatoren und Kosten
- Export nach DuckDB und optional MinIO

#### 🔧 Verwendung

```bash
python run_processors.py <Pfad_zur_Eingabedatei>
```

#### ⚙️ Prozessablauf

1. Laden der Eingabedaten
2. Initialisierung der DuckDB-Verbindung
3. LCA-Berechnung
4. Kostenberechnung
5. Speicherung in DuckDB
6. Optionaler Export als Parquet
</details>

### 📊 `dataset_gen.py`

Generator für Testdatensätze. Erstellt realistische Daten für Tests.

- Generierung realistischer Testszenarien
- Anpassbare Datensatzgrößen
- Strukturierte CSV-Ausgabe
- Integrierte Validierung

<details>
<summary><b>🔍 Implementierungsdetails</b></summary>

#### 📋 Hauptfunktionen

- Generierung von IFC-Elementen
- Erstellung von Materialdaten
- Validierung der Testdaten

#### 🔧 Verwendung

```bash
python dataset_gen.py
```

#### 📝 Generierte Daten

- IFC-Elemente
- Materialdaten
- eBKP-H Codes
</details>

### 📈 `profiler.py`

Leistungsanalyse-Tool für die Module.

- CPU/Memory Profiling
- Zeitliche Analyse
- Bottleneck-Identifikation
- Performance-Reporting

<details>
<summary><b>🔍 Implementierungsdetails</b></summary>

#### 📋 Hauptfunktionen

- Performance-Profiling
- Speicheranalyse
- Bottleneck-Identifikation

#### 🔧 Verwendung

```bash
python profiler.py <Pfad_zur_Eingabedatei>
```

#### 📊 Analysebereiche

- Ausführungszeiten
- Speichernutzung
- Datenbankoperationen
</details>

### 📑 `generate_summary.py`

Generator für Ergebnisberichte.

- Aggregierte Übersichten
- Statistische Auswertungen
- Formatierte Ausgabe
- Dateiexport

<details>
<summary><b>🔍 Implementierungsdetails</b></summary>

#### �� Hauptfunktionen

- Auslesen der DuckDB-Daten
- Statistische Auswertung
- Berichtgenerierung

#### 🔧 Verwendung

```bash
python generate_summary.py
```

#### �� Berichtsinhalte

- Projektübersicht
- LCA-Ergebnisse
- Kostenanalyse
- Fehlerstatistiken
</details>

## 🔄 Workflow

### Empfohlene Ausführungsreihenfolge

1. **Referenzdaten laden**

   ```bash
   python duckDB_import_export.py load-all --version "2024-v1"
   ```

2. **Hauptberechnung**

   ```bash
   python run_processors.py input.xlsx
   ```

3. **Berichtgenerierung**

   ```bash
   python generate_summary.py
   ```

> [!TIP]
> Die Skripte nutzen die DuckDB-Datenbank als zentralen Datenspeicher. Stellen Sie sicher, dass die Referenzdaten geladen sind, bevor Sie die Berechnungen starten.
