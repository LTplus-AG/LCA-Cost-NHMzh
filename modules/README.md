# NHMzh Module Kosten & LCA

> [!NOTE]
> Für eine Übersicht des gesamten Projekts, siehe die [Haupt-README.md](../README.md).

## 📦 Module

### 🔧 BaseProcessor
Abstrakte Basisklasse für die Modulstruktur. Stellt grundlegende Funktionen wie Dateiverarbeitung, Prozesssteuerung und Validierung bereit.
* Einheitliche Initialisierung mit Ein-/Ausgabepfaden
* Zentrale Prozesssteuerung via `run()`-Methode
* Framework für Datenvalidierung und -verarbeitung
* Integrierte Utilities aus `shared_utils`

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
Berechnet Ökobilanzen für Bauteile und Schichten mit CO₂-Äquivalenten, Energieverbrauch und UBP. Umfassende Lebensdaueranalyse und KBOB-Integration.
* KBOB-Umweltindikatoren Verarbeitung
* Lebensdaueranalyse via eBKP-H
* CO₂-eq, Primärenergie und UBP Berechnung
* Detaillierte Ergebnisaufbereitung
* Umfassendes Fehlerhandling

<details>
<summary><b>🔍 Implementierungsdetails</b></summary>

#### 🔄 Initialisierung und Datenverarbeitung
- **Datenladen**
  - Elementdaten aus Eingabedatei
  - KBOB-Daten mit Umweltindikatoren
  - Lebensdauerinformationen
- **Validierung**
  - Spaltenprüfung der Eingabedaten
  - Wertevalidierung aller Parameter

#### ⏳ Lebensdauer
- **Ermittlung**
  - Basierend auf eBKP-H-Codes
  - Berücksichtigung von Teilübereinstimmungen
  - Protokollierung nicht zugeordneter Codes

#### 🧮 Berechnungen
- **CO₂-Äquivalente**
  - Gesamtemissionen in kg CO₂-eq
  - Jährliche Emissionen
  - Flächenbezogen in kg CO₂-eq/m²*a
- **Energieverbrauch**
  - Primärenergie in kWh (gesamt)
  - Jährlicher Verbrauch
- **UBP-Berechnung**
  - Gesamte Umweltbelastungspunkte
  - Jährliche UBP-Werte

#### 📋 Ergebnisse
- **Strukturierung**
  - Detaillierte Ergebnisse je Bauteil
  - GUID-basierte Gruppierung
  - Fehlerinformationen

#### ⚠️ Fehlerhandling
- **Validierung**
  - Datenprüfung und -validierung
  - Warnungen für fehlende Daten
  - Protokollierung von Berechnungsproblemen
</details>

### 💰 CostProcessor
Ermittelt Projektkosten basierend auf Bauteil-Kennwerten. Bietet automatische Mengenermittlung und umfassende Kostenanalyse mit Fehlerhandling.
* Integration von Element- und Kostendaten
* Automatische Einheiten-/Mengenermittlung
* eBKP-H-basierte Kostenzuordnung
* Strukturierte Ergebnisaufbereitung
* Robustes Fehlerhandling

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
