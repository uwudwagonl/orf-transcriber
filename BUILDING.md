# Bauen

Es gibt zwei Wege zur fertigen MSI: lokal auf Windows, oder via GitHub
Actions (was du auch von Linux/Mac aus auslösen kannst — keine Windows-
Maschine nötig).

---

## Variante A — GitHub Actions (empfohlen)

Du brauchst nur dieses Repo auf GitHub.

1. Repo pushen.
2. Tag setzen und pushen:
   ```bash
   git tag v0.1.0
   git push origin v0.1.0
   ```
3. Der Workflow `Release MSI` baut auf einem Windows-Runner und hängt
   die fertige MSI an ein GitHub-Release.
4. Mama klickt auf den MSI-Link unter „Releases".

Du kannst den Workflow auch von Hand auslösen
(„Actions → Release MSI → Run workflow"), z. B. um eine Test-MSI ohne
Tag zu bauen — die landet dann unter „Artifacts" beim Run.

---

## Variante B — Lokal auf Windows

### Vorbereitung (einmalig)

1. Python 3.11+ installieren — https://python.org
   (Haken bei „Add Python to PATH" setzen).
2. .NET SDK installieren — https://dotnet.microsoft.com/download
3. WiX 5 installieren:
   ```powershell
   dotnet tool install --global wix --version 5.0.2
   wix extension add --global WixToolset.UI.wixext/5.0.2
   ```

### Build

```powershell
git clone <repo> orf-transcriber
cd orf-transcriber
pwsh build/scripts/build.ps1
```

Das Skript:
1. Legt ein virtuelles Python-Env unter `build/.venv` an.
2. Installiert die Build-Anforderungen.
3. Lädt `orfondl.exe` und FFmpeg in `build/vendor/`.
4. Ruft PyInstaller auf → `build/dist/OrfTranscriber/`.
5. Ruft WiX auf → `build/dist/OrfTranscriber-0.1.0.msi`.

### Schnelles Testen ohne MSI

```powershell
pwsh build/scripts/dev.ps1        # GUI direkt aus dem Quellcode starten
pwsh build/scripts/build.ps1 -SkipMsi   # nur PyInstaller-Output bauen
```

### Version setzen

```powershell
pwsh build/scripts/build.ps1 -Version 0.2.0
```

---

## Aufbau, kurz erklärt

- **PyInstaller** packt Python + alle Bibliotheken (`faster-whisper`,
  `ctranslate2`, `tokenizers`, `python-docx`, …) in einen Ordner mit
  einer `OrfTranscriber.exe`.
- Die nativen Tools `orfondl.exe`, `ffmpeg.exe`, `ffprobe.exe` werden
  daneben in einem Unterordner `bin/` mitgepackt — `paths.py` findet
  sie zur Laufzeit auch im PyInstaller-Bundle.
- **WiX 5** verpackt diesen Ordner in eine MSI mit Startmenü-Eintrag,
  Add/Remove-Programs-Eintrag und Upgrade-Logik (über `UpgradeCode`).

## Häufige Fehler

| Fehler | Ursache / Lösung |
|---|---|
| `wix : command not found` | `dotnet tool install --global wix` und neue Shell |
| `WixToolset.UI.wixext` fehlt | `wix extension add --global WixToolset.UI.wixext/5.0.2` |
| `orfondl-Programm nicht gefunden` zur Laufzeit | `build/vendor/orfondl.exe` fehlte beim PyInstaller-Lauf — neu bauen |
| MSI installiert, aber Modell-Download bricht ab | Firewall blockiert `huggingface.co` — manuell freischalten |
| App startet nicht (Windows SmartScreen) | „Weitere Informationen" → „Trotzdem ausführen" — die MSI ist nicht code-signiert |
