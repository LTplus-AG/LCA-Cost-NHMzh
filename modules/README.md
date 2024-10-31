# NHMzh Module Kosten & LCA

> **Hinweis**: Für eine Übersicht des gesamten Projekts, siehe die [Haupt-README.md](../README.md).

### `BaseProcessor`

ist eine abstrakte Basisklasse, die die gemeinsame Struktur für alle Module bereitstellt. Enthält insb.:

- Initialisierung mit Eingabedateipfad, Inputdaten-Dateipfad und Ausgabedateipfad
- `run()`-Methode zur Steuerung des Prozessablaufs
- Abstrakte Methoden zur Datenvalidierung und -verarbeitung in den Modulen
- Methoden zum Laden von Daten und Speichern der Ergebnisse
- Verwendung von `load_data()` und `save_data_to_json()` aus `utils.shared_utils`

### `LCAProcessor`

Berechnet der Ökobilanz (LCA) für Bauteile und Bauteilschichten.

- **Initialisierung und Datenverarbeitung**:

  - Lädt Elementdaten, KBOB-Daten (Umweltindikatoren) und Lebensdauerinformationen.
  - Führt Datenvalidierung durch: Spaltenprüfung und Wertevalidierung.

- **Lebensdauer**:

  - Methode zur Ermittlung der Lebensdauer basierend auf eBKP-H-Codes.
  - Enthält Teilübereinstimmungen und protokolliert Warnungen für fehlende oder nicht zugeordnete Codes.

- **Berechnungen**:

  - Berechnet ökologische Auswirkungen durch Multiplikation von Menge und Indikator für:
    - CO₂-eq resp. Treibhausgasemissionen (Gesamt und pro Jahr, d.h. in kg CO₂-eq resp. kg CO₂-eq / m² \* a)
    - Primärenergieverbrauch in kWh (Gesamt und pro Jahr)
    - UBP (Umweltbelastungspunkte, Gesamt und pro Jahr)

- **Ergebnisgenerierung**:

  - Erstellt detaillierte Ergebnisse für gültige und fehlerhafte Daten.
  - Gruppiert Bauteile nach GUID, behandelt Fälle mit gemeinsamen GUIDs.
  - Erzeugt strukturierte Ergebnisliste mit Bauteiledetails und Fehlerinformationen.

- **Fehlerbehandlung und Protokollierung**:

  - Fehlerprüfung und -validierung, protokolliert Warnungen für fehlende Daten, nicht zugeordnete Codes und Berechnungsprobleme.

### `CostProcessor`

Berechnet die prognostizierten Kosten für Bauprojekte.

- **Initialisierung und Datenverarbeitung**:

  - Lädt Elementdaten und Kostenkennwerte.
  - Führt Datenvalidierung durch: Spaltenprüfung und Wertevalidierung.
  - Konvertiert 'eBKP-H' und 'Code' Spalten in String-Format und entfernt Leerzeichen.
  - Setzt 'Code' als Index für die Kostenkennwerte zur effizienten Verknüpfung.

- **Datenzusammenführung**:

  - Verbindet Element- und Kostenkennwerte basierend auf 'eBKP-H' Codes.
  - Identifiziert und protokolliert fehlende Kostenkennwerte.

- **Mengenermittlung**:

  - Bestimmt die relevante Menge (Fläche, Länge) basierend auf der Referenzeinheit in den Kostenkennwerten.
  - Behandelt unbekannte Einheitstypen und markiert entsprechende Datensätze als fehlerhaft.

- **Kostenberechnung**:

  - Berechnet Gesamtkosten durch Multiplikation von Menge und Einheitspreis für gültige Datensätze.

- **Ergebnisgenerierung**:

  - Erstellt detaillierte Ergebnisse für gültige und fehlerhafte Daten.
  - Gruppiert Bauteile nach GUID, behandelt Fälle mit gemeinsamen GUIDs.
  - Erzeugt strukturierte Ergebnisliste mit Bauteiledetails und Fehlerinformationen.

- **Fehlerbehandlung und Protokollierung**:

  - Implementiert Fehlerprüfung für Mengen und fehlende Kostenkennwerte.
  - Protokolliert Warnungen für fehlende Kostenkennwerte und unbekannte Einheitstypen.
