# ORF Transcriber

Eine kleine Windows-Anwendung, die ein Video von **ORF ON** (`on.orf.at`)
herunterlädt und automatisch ein **Word-Transkript** mit Zeitmarken
erstellt — barrierearm bedienbar, lokal, ohne Cloud.

## Was es kann

- Video von `on.orf.at` per [orfondl](https://github.com/badlogic/orfondl)
  herunterladen.
- Audio offline mit [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
  (Modell `large-v3-turbo`, deutsch) transkribieren.
- Eine Word-Datei mit Titel, Metadaten, Fließtext-Transkript,
  Zeitmarken-Transkript und einem maschinenlesbaren Footer
  speichern – ideal zum Vorlesen, Lesen oder für eine KI-Zusammenfassung.

## Installation für Endnutzer

1. MSI von der [Release-Seite](../../releases) herunterladen
   (`OrfTranscriber-x.y.z.msi`).
2. Doppelklick → installieren.
3. Im Startmenü „ORF Transcriber" suchen und starten.
4. Beim ersten Transkribieren wird einmalig das Sprachmodell
   (~1.5 GB) automatisch heruntergeladen.

Es wird **nichts** im Internet hochgeladen — Transkription läuft komplett
lokal.

## Bedienung

1. Link von ORF ON kopieren (z. B. `https://on.orf.at/video/14256123/...`).
2. Im Programm einfügen oder „Aus Zwischenablage" klicken.
3. „Herunterladen und transkribieren" anklicken.
4. Warten — der Verlauf zeigt was gerade passiert.
5. Am Ende öffnet das Programm den Speicherort
   (Standard: `Dokumente\ORF Transkripte`).

Über „Einstellungen" lässt sich die Modellgröße, die Sprache und ob die
heruntergeladene Videodatei behalten werden soll, ändern.

## Projektstruktur

```
src/orf_transcriber/   – Python-Quellcode (Tkinter-GUI + Pipeline)
build/orf-transcriber.spec  – PyInstaller-Spec
build/installer/Package.wxs – WiX-5-Installer-Definition
build/scripts/         – Build-Skripte (PowerShell)
.github/workflows/     – CI + Release-Builds
```

Bauen siehe [BUILDING.md](BUILDING.md).

## Lizenz / Komponenten

Eigener Code: MIT.

Verwendet:
- [orfondl](https://github.com/badlogic/orfondl) (MIT)
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (MIT)
- [python-docx](https://github.com/python-openxml/python-docx) (MIT)
- [FFmpeg](https://ffmpeg.org/) (LGPL/GPL — gyan.dev essentials build)

ORF ON ist Eigentum des ORF. Bitte das Urheberrecht beachten und Inhalte
nur für den persönlichen Gebrauch verwenden.
