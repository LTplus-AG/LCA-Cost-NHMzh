# NHMzh Scripts

> [!NOTE]
> Für eine Übersicht des gesamten Projekts, siehe die [Haupt-README.md](../README.md).

## 🛠️ Skript-Sammlung

### ⚡ `run_processors.py`
Hauptskript für LCA- und Kostenberechnungen. Verarbeitet Eingabedaten und generiert kombinierte Analyseergebnisse.
* Zentrale Steuerung der Berechnungsmodule
* Integrierte Datenverarbeitung
* Ergebniskombination und -speicherung
* Robuste Fehlerbehandlung

<details>
<summary><b>🔍 Implementierungsdetails</b></summary>

#### 📋 Hauptfunktionen
- Lädt und validiert Eingabedaten
- Steuert LCAProcessor und CostProcessor
- Kombiniert Einzelergebnisse
- Speichert Gesamtergebnisse

#### 🔧 Verwendung
```bash
python run_processors.py <Pfad_zur_Eingabedatei>
```

#### ⚙️ Prozessablauf
1. Datenvalidierung
2. LCA-Berechnung
3. Kostenberechnung
4. Ergebnisintegration
</details>

### 📊 `dataset_gen.py`
Generator für realistische Testdatensätze. Erstellt umfangreiche Daten für Leistungs- und Skalierungstests.
* Generierung realistischer Testszenarien
* Anpassbare Datensatzgrößen
* Strukturierte CSV-Ausgabe
* Integrierte Validierung

<details>
<summary><b>🔍 Implementierungsdetails</b></summary>

#### 📋 Hauptfunktionen
- Generiert realistische Testdaten
- Validiert Datenstruktur
- Speichert als CSV

#### 🔧 Verwendung
```bash
python dataset_gen.py
```

#### 📝 Generierte Daten
- Bauteilinformationen
- KBOB-Referenzdaten
- Kostenkennwerte
</details>

### 📈 `profiler.py`
Leistungsanalyse-Tool für Module. Erstellt detaillierte Performance-Profile und Optimierungsvorschläge.
* CPU/Memory Profiling
* Zeitliche Analyse
* Bottleneck-Identifikation
* Performance-Reporting

<details>
<summary><b>🔍 Implementierungsdetails</b></summary>

#### 📋 Hauptfunktionen
- Performance-Profiling
- Detaillierte Berichtgenerierung
- Speicherung der Profiling-Daten

#### 🔧 Verwendung
```bash
python profiler.py <Pfad_zur_Eingabedatei>
```

#### 📊 Analysebereiche
- Ausführungszeiten
- Speichernutzung
- CPU-Auslastung
</details>

### 📑 `generate_summary.py`
Generator für übersichtliche Ergebnisberichte. Bereitet Berechnungsergebnisse leicht verständlich auf.
* Aggregierte Übersichten
* Statistische Auswertungen
* Formatierte Ausgabe
* Dateiexport

<details>
<summary><b>🔍 Implementierungsdetails</b></summary>

#### 📋 Hauptfunktionen
- Liest Ergebnisdaten
- Berechnet Statistiken
- Generiert Berichte

#### 🔧 Verwendung
```bash
python generate_summary.py
```

#### 📊 Berichtsinhalte
- Gesamtübersicht
- Detailanalysen
- Fehlerstatistiken
</details>

## 🔄 Workflow

### Empfohlene Ausführungsreihenfolge

1. **Testdaten (optional)**
   ```bash
   python dataset_gen.py
   ```

2. **Hauptberechnung**
   ```bash
   python run_processors.py input.xlsx
   ```

3. **Performance-Analyse (optional)**
   ```bash
   python profiler.py input.xlsx
   ```

4. **Berichtgenerierung**
   ```bash
   python generate_summary.py
   ```

> [!TIP]
> Für optimale Ergebnisse wird empfohlen, die Skripte in der angegebenen Reihenfolge auszuführen.
