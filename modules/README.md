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
   - **KBOB-Daten** (CSV)
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

Die Module funktionieren mit MinIO für Cloud-Storage. Diese Funktionalität wird durch den `MinioManager` bereitgestellt.

### MinioManager

Verwaltet die Interaktion mit MinIO-Storage für Ein- und Ausgabedaten.

<details>
<summary><b>🔍 Implementierungsdetails</b></summary>

#### ✨ Kernfunktionalitäten

- **Initialisierung**
  - Verbindungsaufbau mit MinIO-Server
  - Bucket-Verwaltung
  - Konfigurationsvalidierung
- **Dateioperationen**
  - Upload von Ergebnisdaten
  - Download von Eingabedaten
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

#### 📁 Dateistruktur

- `/input/` - Eingabedaten (KBOB, Kosten, etc.)
- `/output/` - Berechnungsergebnisse
- `/mappings/` - Materialmappings und Konfigurationen

#### 🔄 Verwendung

```python
# Initialisierung
processor = LCAProcessor(
    input_file_path="input.json",
    data_file_path="kbob.csv",
    output_file="results.json",
    life_expectancy_file_path="life_expectancy.csv",
    material_mappings_file="mappings.json",
    minio_config=minio_config
)

# Automatische MinIO-Integration
processor.run()  # Lädt/Speichert Daten von/zu MinIO
```

#### ⚠️ Fehlerbehandlung

- Automatische Wiederverbindungsversuche
- Fallback auf lokale Dateien bei MinIO-Fehlern
- Detaillierte Fehlerprotokolle

#### 🔐 Sicherheit

- TLS-Verschlüsselung für Datenübertragung
- Zugriffsschlüssel-basierte Authentifizierung
- Bucket-Policy-Unterstützung
</details>

### Verwendung in Prozessoren

Alle Prozessoren (LCA, Cost) unterstützen MinIO-Integration durch:

1. **Automatisches Laden**

   - Eingabedaten aus MinIO
   - Referenzdaten (KBOB, Kosten)
   - Mappings und Konfigurationen

2. **Automatisches Speichern**

   - Berechnungsergebnisse
   - Fehlerprotokolle
   - Zwischenergebnisse (optional)

3. **Konfigurationsoptionen**
   - Bucket-Struktur anpassbar
   - Versionierung aktivierbar
   - Caching-Strategien wählbar
