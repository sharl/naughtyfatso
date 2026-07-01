# Naughty Fatso

![Naughty Fatso](Assets/icon.png)

Naughty Fatso is silently gobbling up your memory, sigh

## Configurations

~\.config\NaughtyFatso\config.json
~\.config\NaughtyFatso\list.txt

## Run

```powershell
git clone https://github.com/sharl/naughtyfatso.git
cd naughtyfatso
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python naughtyfatso.py
```

## Build

```powershell
pip install pyinstaller
pyinstaller "naughtyfatso.py" "--onefile" "--noconsole" "--icon=Assets/sample.ico" "--exclude-module=PIL.ImageCms" "--exclude-module=PIL.ImageFilter" "--exclude-module=PIL.ImageMath" "--exclude-module=PIL.ImageMorph" "--exclude-module=PIL.ImageTk" "--exclude-module=PIL._avif" "--exclude-module=PIL._imagingcms" "--exclude-module=PIL._imagingft" "--exclude-module=PIL._imagingmath" "--exclude-module=PIL._imagingmath" "--exclude-module=PIL._imagingtk" "--exclude-module=PIL._webp" "--exclude-module=_bz2" "--exclude-module=_decimal" "--exclude-module=_lzma" "--exclude-module=_queue" "--add-data=Assets/version.txt;Assets" "--add-data=Assets/sample.ico;Assets"
```
