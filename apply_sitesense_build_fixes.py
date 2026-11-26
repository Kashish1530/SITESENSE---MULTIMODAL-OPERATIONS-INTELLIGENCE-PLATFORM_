from pathlib import Path
import re
import shutil
from datetime import datetime

ROOT = Path(__file__).resolve().parent
# Locate the staged frontend from the project root rather than assuming
# that the script itself is inside the frontend directory.
candidates = list((ROOT / "_integration_staging").glob("**/frontend"))
FRONTEND = next(
    (
        candidate for candidate in candidates
        if (candidate / "src" / "App.tsx").is_file()
        and (candidate / "src" / "components" / "chat" / "ChatPage.tsx").is_file()
        and (candidate / "src" / "components" / "upload" / "UploadPage.tsx").is_file()
    ),
    None,
)
if FRONTEND is None:
    raise FileNotFoundError(
        "Could not locate the staged frontend under _integration_staging. "
        "Expected src/App.tsx, src/components/chat/ChatPage.tsx, and "
        "src/components/upload/UploadPage.tsx."
    )
FILES = {
    "App.tsx": FRONTEND / "src" / "App.tsx",
    "ChatPage.tsx": FRONTEND / "src" / "components" / "chat" / "ChatPage.tsx",
    "UploadPage.tsx": FRONTEND / "src" / "components" / "upload" / "UploadPage.tsx",
}
BACKUP = ROOT / "_integration_backups" / ("build_fix_auto_" + datetime.now().strftime("%Y%m%d_%H%M%S"))

def read(path):
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")
    return path.read_text(encoding="utf-8")

def write(path, text):
    path.write_text(text, encoding="utf-8", newline="")

def clean_named_import(source, module, names):
    pattern = re.compile(
        r"import\s*\{(?P<body>.*?)\}\s*from\s*(['\"])" + re.escape(module) + r"\2\s*;?",
        re.S
    )
    match = pattern.search(source)
    if not match:
        return source, False
    items = [x.strip() for x in match.group("body").split(",") if x.strip()]
    kept = [x for x in items if x.split(" as ")[-1].strip() not in names and x not in names]
    if len(kept) == len(items):
        return source, False
    replacement = "// harsh changes starts\n"
    if kept:
        replacement += "import { " + ", ".join(kept) + " } from " + match.group(2) + module + match.group(2) + "\n"
    replacement += "// harsh changes end"
    return source[:match.start()] + replacement + source[match.end():], True

originals = {name: read(path) for name, path in FILES.items()}
updated = dict(originals)

# App.tsx: remove unused TaskUpload import and only the UploadPage callback prop.
s = updated["App.tsx"]
s2, n = re.subn(r"(?m)^[ \t]*import[^\n]*\bTaskUpload\b[^\n]*\n", "", s, count=1)
if n:
    s = s2
s2, n = re.subn(
    r"(?s)(if\s*\(activePage\s*===\s*'Upload'\)\s*\{\s*return\s*\(\s*.*?)(\s*onSubmitTaskPhotos=\{handleSubmitTaskPhotos\}\s*)",
    lambda m: m.group(1) + "\n          // harsh changes starts\n          // UploadPage does not handle task-photo submissions.\n          // harsh changes end\n",
    s, count=1
)
if n:
    s = s2
updated["App.tsx"] = s

# ChatPage.tsx: remove the unused ImagePlus import specifier.
s, changed = clean_named_import(updated["ChatPage.tsx"], "lucide-react", {"ImagePlus"})
updated["ChatPage.tsx"] = s

# UploadPage.tsx: remove unused icon imports and unused mock data import.
s, changed = clean_named_import(
    updated["UploadPage.tsx"], "lucide-react",
    {"BarChart3", "Calendar", "Clock", "HelpCircle", "Layers", "MapPin", "ShieldCheck", "Trash2", "Video"}
)
s, _ = re.subn(r"(?m)^[ \t]*import\s*\{\s*sitePerformance\s*\}\s*from\s*['\"][^'\"]+['\"]\s*;?\s*\n", "", s)

# Remove unused callback from the Props type.
s, _ = re.subn(
    r"(?ms)^[ \t]*onSubmitTaskPhotos\?\s*:\s*\(\s*task\s*:\s*InspectionRecord\s*,\s*files\s*:\s*File\[\]\s*,\s*onProgress\s*:\s*\(progress\s*:\s*number\)\s*=>\s*void\s*\)\s*=>\s*Promise<boolean>\s*;?\s*\n",
    "",
    s
)

# Remove callback from UploadPage parameter destructuring.
s, _ = re.subn(r"(?m)^[ \t]*onSubmitTaskPhotos,\s*\n", "", s, count=1)

# Remove unused date filter state.
s, _ = re.subn(r"(?m)^[ \t]*const \[filterDateRange, setFilterDateRange\] = useState<string>\('all'\)\s*\n", "", s)

# Correct the inspection date field.
s, _ = re.subn(
    r"uploadedAt:\s*insp\.submittedAt\s*\|\|\s*insp\.scheduledDate\s*\|\|\s*'2026-11-24',",
    " // harsh changes starts\n            uploadedAt: insp.submittedAt || insp.scheduledAt || insp.createdAt,\n            // harsh changes end",
    s, count=1
)

# Remove unused report result variable while retaining the API call.
s, _ = re.subn(r"(?m)^[ \t]*let reportResult = null\s*\n", "", s, count=1)
s, _ = re.subn(r"\breportResult\s*=\s*await generateReportApi\(", "await generateReportApi(", s, count=1)
s, _ = re.subn(r"(?m)^[ \t]*const dummyFilename = .*?\n", "", s, count=1)

updated["UploadPage.tsx"] = s

# Guard against unexpected source drift: require meaningful expected transformations.
for name in FILES:
    if updated[name] == originals[name]:
        raise RuntimeError(f"No changes detected in {name}; source differs from the expected version. No files were modified.")

# Back up every target before writing any changes.
BACKUP.mkdir(parents=True, exist_ok=False)
for name, path in FILES.items():
    shutil.copy2(path, BACKUP / name)

for name, path in FILES.items():
    write(path, updated[name])

print(f"Frontend located: {FRONTEND}")
print("Patch applied. Backups:")
print(BACKUP)
print("\nModified files:")
for name in FILES:
    print(f" - {name}")
print("\nNext command: npm run build")
