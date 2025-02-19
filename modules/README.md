# NHMzh Module Kosten & LCA

> [!NOTE]
> Für eine Übersicht des gesamten Projekts, siehe die [Haupt-README.md](../README.md).

## 📦 Module

### 🔧 BaseProcessor

Abstrakte Basisklasse für die Modulstruktur. Stellt grundlegende Funktionen wie Dateiverarbeitung, Prozesssteuerung und Validierung bereit.

- Einheitliche Initialisierung mit Ein-/Ausgabepfaden
- Zentrale Prozesssteuerung via `run()`-Methode
- Framework für Datenvalidierung und -verarbeitung
- Integrierte Utilities aus `shared_utils`

<details>
<summary><b>🔍 Implementierungsdetails</b></summary>

#### ✨ Kernfunktionalitäten

- **Initialisierung**
  - Eingabedateipfad für Hauptdaten
  - Inputdaten-Dateipfad für Referenzdaten
  - Ausgabedateipfad für Ergebnisse
- **Prozesssteuerung**
  - `run()`-Methode für standardisierten Ablauf
  - Abstrakte Methoden für modulspezifische Validierung
  - Abstrakte Methoden für modulspezifische Verarbeitung
- **Datenverwaltung**
  - Methoden zum strukturierten Laden von Daten
  - Methoden zum standardisierten Speichern der Ergebnisse
  - Integration von `utils.shared_utils` Funktionen
  </details>

### 📊 LCAProcessor

Berechnet Ökobilanzen für Bauteile und Materialien basierend auf IFC-Elementen und KBOB-Daten.

<details>
<summary><b>🔍 Implementierungsdetails</b></summary>

#### 🔄 Datenstruktur & Verarbeitung

1. **Eingabedaten**

   - **IFC-Elemente**
     ```json
     {
       "elements": [
         {
           "id": "1hBFsAS3qHxv8nM6rdhbEd",
           "ifc_class": "IfcSlab",
           "properties": {
             "ebkp": "C2"
           },
           "materials": ["Beton"],
           "material_volumes": {
             "Beton": {
               "fraction": 1.0,
               "volume": 3.684,
               "density": 2300.0
             }
           }
         }
       ]
     }
     ```
   - **KBOB-Daten**
     - UUID-Nummer
     - Treibhausgasemissionen [kg CO2-eq]
     - Primärenergie nicht erneuerbar [kWh oil-eq]
     - UBP (Total)
     - BAUMATERIALIEN (Name)

2. **Datenvorbereitung**
   - Validierung der Eingabestruktur
   - KBOB-Daten Aufbereitung
   - Material-Mapping Validierung
   - Lebensdauer-Zuordnung via eBKP-H

#### 🧮 Berechnungsprozess

1. **Materialdaten-Verarbeitung**

   - Material-zu-KBOB Mapping
   - Volumen- und Dichtevalidierung
   - Lebensdauer-Bestimmung (Default: 60 Jahre)

2. **Umweltindikatoren**

   ```python
   # Für jedes Material:
   co2_eq = volume * density * kbob_row["indicator_co2eq"]
   penre = volume * density * kbob_row["indicator_penre"]
   ubp = volume * density * kbob_row["indicator_ubp"]

   # Pro Jahr:
   indicator_per_year = indicator / life_expectancy
   ```

3. **Ergebnisaufbereitung**
   ```json
   {
     "guid": "1hBFsAS3qHxv8nM6rdhbEd",
     "components": [
       {
         "guid": "1hBFsAS3qHxv8nM6rdhbEd",
         "material": "Beton",
         "mat_kbob": "E13EE05E-FD34-4FB5-A178-0FC4164A96F2",
         "kbob_material_name": "Hochbaubeton (ohne Bewehrung)",
         "volume": 3.684,
         "density": 2300.0,
         "amortization": 50,
         "ebkp_h": "C2",
         "gwp_absolute": 1234.567,
         "gwp_relative": 24.691,
         "penr_absolute": 2345.678,
         "penr_relative": 46.914,
         "ubp_absolute": 345678,
         "ubp_relative": 6914,
         "failed": false
       }
     ],
     "shared_guid": false
   }
   ```

#### ⚠️ Fehlerbehandlung

1. **Validierungsfehler**

   - Fehlende Pflichtfelder
   - Ungültige Datentypen
   - Fehlende KBOB-Referenzen

2. **Berechnungsfehler**

   - Ungültige Volumina oder Dichten
   - Fehlende Material-Mappings
   - Nicht gefundene KBOB-IDs

3. **Fehlerprotokollierung**
   - Detaillierte Fehlermeldungen pro Komponente
   - Markierung fehlgeschlagener Berechnungen
   - Fortsetzung der Verarbeitung trotz Teilfehlern

#### 🔍 Qualitätssicherung

- Einheitliche Rundung (3 Dezimalstellen für Metriken)
- Standardisierte Fehlerprotokolle
- Validierung aller Eingabewerte
- Konsistente Einheitenverwendung
</details>

### 💰 CostProcessor

Ermittelt Projektkosten basierend auf Bauteil-Kennwerten. Bietet automatische Mengenermittlung und umfassende Kostenanalyse mit Fehlerhandling.

- Integration von Element- und Kostendaten
- Automatische Einheiten-/Mengenermittlung
- eBKP-H-basierte Kostenzuordnung
- Strukturierte Ergebnisaufbereitung
- Robustes Fehlerhandling

<details>
<summary><b>🔍 Implementierungsdetails</b></summary>

#### 🔄 Initialisierung und Datenverarbeitung

- **Datenladen**
  - Elementdaten aus Hauptdatei
  - Kostenkennwerte aus Referenzdaten
- **Datenaufbereitung**
  - String-Konvertierung (eBKP-H, Code)
  - Leerzeichenbereinigung
  - Optimierte Indexierung der Kostenkennwerte

#### 🔗 Datenzusammenführung

- **Verknüpfung**
  - Element-/Kostendaten via eBKP-H
  - Identifikation fehlender Kennwerte
  - Protokollierung von Zuordnungsproblemen

#### 📐 Mengenermittlung

- **Berechnung**
  - Flächenermittlung
  - Längenermittlung
  - Einheitenprüfung und -konvertierung
- **Validierung**
  - Prüfung der Referenzeinheiten
  - Behandlung unbekannter Einheiten
  - Fehlermarkierung bei Problemen

#### 🧮 Kostenberechnung

- **Kalkulation**
  - Menge × Einheitspreis
  - Nur für validierte Datensätze
  - Berücksichtigung von Einheitenkonversionen

#### 📋 Ergebnisse

- **Aufbereitung**
  - Detaillierte Kostenaufstellung
  - GUID-basierte Gruppierung
  - Fehlerinformationen

#### ⚠️ Fehlerhandling

- **Prüfung**
  - Mengenvalidierung
  - Kostenkennwert-Check
  - Einheitenkompatibilität
- **Protokollierung**
  - Fehlende/ungültige Kennwerte
  - Einheitenprobleme
  - Berechnungsfehler
  </details>

## 🗄️ MinIO Integration

Die Module nutzen DuckDB für die Datenverwaltung und den Export von Berechnungsergebnissen im Parquet-Format nach MinIO. Diese Funktionalität ist optional und ermöglicht die direkte Integration mit dem PowerBI-Dashboard.

### MinioManager

Verwaltet den Export der DuckDB-Ergebnisse als Parquet-Dateien nach MinIO.

<details>
<summary><b>🔍 Implementierungsdetails</b></summary>

#### ✨ Kernfunktionalitäten

- **Initialisierung**
  - Verbindungsaufbau mit MinIO-Server
  - Bucket-Verwaltung
  - Konfigurationsvalidierung
- **Dateioperationen**
  - Konvertierung der Ergebnisse in Parquet-Format
  - Upload der Parquet-Dateien
  - Automatische Bucket-Erstellung
- **Fehlerbehandlung**
  - Verbindungsfehler-Handling
  - Retry-Mechanismen
  - Ausführliche Logging

#### 🔧 Konfiguration

```python
minio_config = {
    "endpoint": "minio.server:9000",
    "access_key": "access_key",
    "secret_key": "secret_key",
    "secure": True,
    "bucket_name": "your-bucket-name"
}
```

#### 📁 Dateistruktur in MinIO

Die Daten werden nach Typ und Projekt organisiert:

- `/lca/{project_id}/{filename}_{timestamp}.parquet` - LCA-Berechnungsergebnisse
- `/cost/{project_id}/{filename}_{timestamp}.parquet` - Kostenberechnungsergebnisse

Jede Datei enthält einen Zeitstempel für Versionierung und Nachverfolgbarkeit.

#### 🔄 Verwendung

```python
# Initialisierung
processor = LCAProcessor(
    input_file_path="input.json",
    data_file_path="kbob.csv",
    output_file="results.json",  # Lokale JSON-Kopie
    life_expectancy_file_path="life_expectancy.csv",
    material_mappings_file="mappings.json",
    minio_config=minio_config  # Optional für Parquet-Export nach MinIO
)

# Ergebnisse werden in DuckDB gespeichert und nach MinIO exportiert
processor.run()
```

#### ⚠️ Fehlerbehandlung

- Ergebnisse bleiben in DuckDB bei MinIO-Fehlern
- Detaillierte Fehlerprotokolle
- Automatische Wiederverbindungsversuche

#### 🔐 Sicherheit

- TLS-Verschlüsselung für Datenübertragung
- Zugriffsschlüssel-basierte Authentifizierung
- Bucket-Policy-Unterstützung
</details>

### Verwendung in Prozessoren

Alle Prozessoren (LCA, Cost) nutzen DuckDB für die Datenverwaltung und unterstützen den optionalen Export nach MinIO:

1. **Datenverarbeitung**

   - Speicherung aller Ergebnisse in DuckDB
   - Effiziente SQL-basierte Berechnungen
   - Integrierte Datenvalidierung

2. **Export und Dashboard-Integration**
   - Direkter Export von DuckDB nach Parquet
   - Optimierte Tabellenstruktur für PowerBI
   - Inkrementelle Aktualisierungen

## 🗄️ Datenbank-Integration

### 📊 LCA-Cost-Database

Zentrale DuckDB-Implementierung für alle Referenz- und Projektdaten. Die Datenbank bietet eine robuste und effiziente Datenverwaltung mit folgenden Hauptkomponenten:

<details>
<summary><b>🔍 Implementierungsdetails</b></summary>

#### 📋 Datenmodell

1. **Referenzdaten-Tabellen**

   ```sql
   -- KBOB Materialien mit Versionierung
   CREATE TABLE kbob_materials (
       uuid TEXT NOT NULL,
       name TEXT NOT NULL,
       indicator_co2eq REAL NOT NULL,
       indicator_penre REAL NOT NULL,
       indicator_ubp REAL NOT NULL,
       density REAL,
       version TEXT NOT NULL,
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
       PRIMARY KEY (uuid, version)
   );

   -- KBOB Versionen
   CREATE TABLE kbob_versions (
       version TEXT PRIMARY KEY,
       is_active BOOLEAN DEFAULT false,
       release_date DATE NOT NULL,
       description TEXT,
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   );

   -- Lebensdauer-Daten
   CREATE TABLE life_expectancy (
       ebkp_code TEXT NOT NULL,
       description TEXT NOT NULL,
       years INTEGER NOT NULL,
       model_based BOOLEAN DEFAULT true,
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
       PRIMARY KEY (ebkp_code, description)
   );

   -- Kostenkennwerte
   CREATE TABLE cost_reference (
       ebkp_code TEXT NOT NULL,
       description TEXT NOT NULL,
       unit TEXT NOT NULL,
       cost_per_unit REAL NOT NULL,
       version TEXT NOT NULL,
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
       PRIMARY KEY (ebkp_code, version)
   );
   ```

2. **Projektdaten-Tabellen**

   ```sql
   -- Projekte
   CREATE TABLE projects (
       project_id VARCHAR PRIMARY KEY,
       name VARCHAR NOT NULL,
       life_expectancy INTEGER DEFAULT 60,
       kbob_version VARCHAR NOT NULL,
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
       updated_at TIMESTAMP,
       status VARCHAR CHECK(status IN ('active', 'processing', 'completed', 'failed'))
   );

   -- IFC-Elemente
   CREATE TABLE ifc_elements (
       id VARCHAR PRIMARY KEY,
       ifc_class VARCHAR NOT NULL,
       object_type VARCHAR,
       load_bearing BOOLEAN,
       is_external BOOLEAN,
       ebkp VARCHAR,
       volume_net DOUBLE,
       volume_gross DOUBLE,
       area_net DOUBLE,
       area_gross DOUBLE,
       length DOUBLE,
       width DOUBLE,
       height DOUBLE,
       project_id VARCHAR NOT NULL,
       timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   );

   -- Material-Zuweisungen
   CREATE TABLE ifc_element_materials (
       id BIGINT PRIMARY KEY DEFAULT nextval('material_id_seq'),
       element_id VARCHAR,
       material_name VARCHAR NOT NULL,
       fraction DOUBLE,
       volume DOUBLE,
       width DOUBLE,
       density DOUBLE,
       UNIQUE(element_id, material_name),
       FOREIGN KEY(element_id) REFERENCES ifc_elements(id)
   );

   -- Material-Mappings
   CREATE TABLE material_mappings (
       ifc_material VARCHAR NOT NULL,
       kbob_material VARCHAR,
       kbob_id VARCHAR,
       kbob_version VARCHAR NOT NULL,
       type VARCHAR,
       is_modelled BOOLEAN DEFAULT true,
       ebkp VARCHAR,
       quantity DOUBLE,
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
       UNIQUE(ifc_material, kbob_id, kbob_version)
   );

   -- Verarbeitungsergebnisse
   CREATE TABLE processing_results (
       id BIGINT PRIMARY KEY DEFAULT nextval('processing_result_id_seq'),
       element_id VARCHAR,
       material_name VARCHAR NOT NULL,
       kbob_uuid VARCHAR NOT NULL,
       kbob_version VARCHAR NOT NULL,
       volume DOUBLE,
       density DOUBLE,
       gwp_absolute DOUBLE,
       gwp_relative DOUBLE,
       penr_absolute DOUBLE,
       penr_relative DOUBLE,
       ubp_absolute DOUBLE,
       ubp_relative DOUBLE,
       amortization INTEGER,
       ebkp_h VARCHAR,
       failed BOOLEAN DEFAULT false,
       error TEXT,
       project_id VARCHAR NOT NULL,
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
       FOREIGN KEY(element_id) REFERENCES ifc_elements(id)
   );

   -- Fehlerprotokolle
   CREATE TABLE processing_errors (
       id BIGINT PRIMARY KEY DEFAULT nextval('processing_error_id_seq'),
       project_id VARCHAR NOT NULL,
       element_id VARCHAR,
       material_name VARCHAR,
       error_type VARCHAR,
       error_message TEXT,
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   );

   -- Verarbeitungshistorie
   CREATE TABLE processing_history (
       id BIGINT PRIMARY KEY DEFAULT nextval('processing_history_id_seq'),
       project_id VARCHAR NOT NULL,
       total_elements INTEGER,
       processed_elements INTEGER,
       failed_elements INTEGER,
       processing_time DOUBLE,
       kbob_version VARCHAR NOT NULL,
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   );
   ```

#### 🔄 Hauptfunktionen

1. **Referenzdaten-Management**

   - Import und Versionierung von KBOB-Daten
   - Verwaltung von Lebensdauer-Daten
   - Kostenkennwert-Management mit Versionierung
   - Material-Mapping-Verwaltung

2. **Projekt-Management**

   - Projekt-Initialisierung und Status-Tracking
   - IFC-Element-Verwaltung
   - Material-Zuweisungen
   - Ergebnis-Speicherung und -Verwaltung

3. **Transaktionsmanagement**

   - Atomare Operationen für Datenkonsistenz
   - Automatisches Rollback bei Fehlern
   - Versionskontrolle für Referenzdaten

4. **Performance-Optimierung**

   - Automatische Indizierung wichtiger Felder
   - Optimierte Abfragen für häufige Operationen
   - Effiziente Batch-Verarbeitung
   - Integrierte Fehlerbehandlung

5. **Export-Funktionen**
   - JSON-Export für Datensicherung
   - Parquet-Export für MinIO/PowerBI
   - Strukturierte Fehlerprotokolle
   - Verarbeitungshistorie

</details>
