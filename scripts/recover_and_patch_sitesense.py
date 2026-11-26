from pathlib import Path
from datetime import datetime
import shutil
import re

ROOT = Path.cwd()
if not (ROOT / "_integration_backups").is_dir():
    raise SystemExit("Run this script from the SITESENSE project root.")

frontend_candidates = list((ROOT / "_integration_staging").glob("**/frontend"))
FRONTEND = next((p for p in frontend_candidates if (p / "src/App.tsx").is_file()
                and (p / "src/components/chat/ChatPage.tsx").is_file()
                and (p / "src/components/upload/UploadPage.tsx").is_file()), None)
if FRONTEND is None:
    raise SystemExit("Could not locate the staged frontend.")

old_backup = ROOT / "_integration_backups" / "build_fix_auto_20261124_172742"
if not old_backup.is_dir():
    raise SystemExit(f"Expected original backup not found: {old_backup}")

targets = {
    "App.tsx": FRONTEND / "src/App.tsx",
    "ChatPage.tsx": FRONTEND / "src/components/chat/ChatPage.tsx",
    "UploadPage.tsx": FRONTEND / "src/components/upload/UploadPage.tsx",
}
restore_sources = {
    "App.tsx": old_backup / "App.tsx",
    "ChatPage.tsx": old_backup / "ChatPage.tsx",
    "UploadPage.tsx": old_backup / "UploadPage.tsx",
}
for name, src in restore_sources.items():
    if not src.is_file():
        raise SystemExit(f"Original backup missing: {src}")

# Save the current state before restoring the known-good originals.
current_backup = ROOT / "_integration_backups" / ("build_fix_recovery_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
current_backup.mkdir(parents=True, exist_ok=False)
for name, path in targets.items():
    shutil.copy2(path, current_backup / name)

# Restore originals from the backup made immediately before the first patch.
for name, path in targets.items():
    shutil.copy2(restore_sources[name], path)

def read(name):
    return targets[name].read_text(encoding="utf-8")

def write(name, value):
    targets[name].write_text(value, encoding="utf-8", newline="")

def remove_named_import(text, module, remove_names):
    # Anchored import match: cannot consume or overwrite neighboring imports.
    pattern = re.compile(
        r"(?m)^import\s*\{(?P<body>[^}]*)\}\s*from\s*(['\"])" +
        re.escape(module) + r"\2\s*;?[ \t]*$",
    )
    m = pattern.search(text)
    if not m:
        print(f"NOTE: import from {module} not found; left unchanged.")
        return text
    entries = [x.strip() for x in m.group("body").split(",") if x.strip()]
    kept = [x for x in entries if x not in remove_names and x.split(" as ")[-1].strip() not in remove_names]
    if len(kept) == len(entries):
        return text
    replacement = "// harsh changes starts\n"
    if kept:
        replacement += "import { " + ", ".join(kept) + " } from " + m.group(2) + module + m.group(2) + ";"
    replacement += "\n// harsh changes end"
    return text[:m.start()] + replacement + text[m.end():]

# App.tsx: remove the unused TaskUpload import, and remove callback only from UploadPage.
s = read("App.tsx")
s, _ = re.subn(r"(?m)^[ \t]*import[^\n]*\bTaskUpload\b[^\n]*\n", "", s, count=1)
s, n = re.subn(
    r"(?s)(if\s*\(activePage\s*===\s*'Upload'\)\s*\{\s*return\s*\(\s*.*?)(\s*onSubmitTaskPhotos=\{handleSubmitTaskPhotos\}\s*)",
    lambda m: m.group(1) + "\n          // harsh changes starts\n          // UploadPage does not handle task-photo submissions.\n          // harsh changes end\n",
    s, count=1
)
if not n:
    print("NOTE: UploadPage callback prop was not found; left App JSX otherwise unchanged.")
write("App.tsx", s)

# ChatPage: remove only the unused icon, preserving all other imports.
s = remove_named_import(read("ChatPage.tsx"), "lucide-react", {"ImagePlus"})
write("ChatPage.tsx", s)

# UploadPage: remove unused icons and unused import without touching adjacent imports.
s = read("UploadPage.tsx")
s = remove_named_import(
    s, "lucide-react",
    {"BarChart3", "Calendar", "Clock", "HelpCircle", "Layers", "MapPin", "ShieldCheck", "Trash2", "Video"}
)
s, _ = re.subn(
    r"(?m)^import\s*\{\s*sitePerformance\s*\}\s*from\s*(['\"])[^'\"]+\1\s*;?[ \t]*\n",
    "", s, count=1
)
# Remove unused UploadPage prop declaration and destructuring only.
s, _ = re.subn(
    r"(?ms)^[ \t]*onSubmitTaskPhotos\?\s*:\s*\(\s*task\s*:\s*InspectionRecord\s*,\s*files\s*:\s*File\[\]\s*,\s*onProgress\s*:\s*\(progress\s*:\s*number\)\s*=>\s*void\s*\)\s*=>\s*Promise<boolean>\s*;?[ \t]*\n",
    "", s, count=1
)
s, _ = re.subn(r"(?m)^[ \t]*onSubmitTaskPhotos,\s*\n", "", s, count=1)
s, _ = re.subn(r"(?m)^[ \t]*const \[filterDateRange, setFilterDateRange\] = useState<string>\('all'\)\s*\n", "", s, count=1)
s, _ = re.subn(
    r"uploadedAt:\s*insp\.submittedAt\s*\|\|\s*insp\.scheduledDate\s*\|\|\s*'2026-11-24',",
    "// harsh changes starts\n            uploadedAt: insp.submittedAt || insp.scheduledAt || insp.createdAt,\n            // harsh changes end",
    s, count=1
)
s, _ = re.subn(r"(?m)^[ \t]*let reportResult = null\s*\n", "", s, count=1)
s, _ = re.subn(r"\breportResult\s*=\s*await generateReportApi\(", "await generateReportApi(", s, count=1)
s, _ = re.subn(r"(?m)^[ \t]*const dummyFilename = .*?\n", "", s, count=1)
write("UploadPage.tsx", s)

print("Recovery and narrow patch completed.")
print("Frontend:", FRONTEND)
print("Current modified-state backup:", current_backup)
print("Original source restored from:", old_backup)
print("Now run npm run build inside the frontend folder.")
