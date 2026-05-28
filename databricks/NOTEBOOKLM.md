# NotebookLM Infographic Generation

How to generate infographics from the databricks folder content using the `notebooklm-py` CLI.

---

## Setup

The CLI lives in the Toyota project and requires Python 3.11:

```bash
cd /Users/dimitargrigorov/Documents/Toyota/notebooklm-py
.venv311/bin/pip install -e . -q
```

Authentication is stored at `~/.notebooklm/storage_state.json` (52 cookies).  
Login once via browser: `notebooklm login`

---

## Notebook Used

| Field | Value |
|-------|-------|
| ID | `8ea13ced-d2c8-4f31-8944-75eab4794996` |
| Title | Databricks on Azure — Infographic |
| Source | `ARCHITECTURE.md` + `SELF_EVOLUTION.md` + `README.md` |

---

## Add Source (first time only)

Combine the databricks docs into one file and upload as a text source:

```bash
cat ARCHITECTURE.md SELF_EVOLUTION.md README.md > /tmp/databricks_content.md

notebooklm source add /tmp/databricks_content.md \
  --notebook 8ea13ced-d2c8-4f31-8944-75eab4794996 \
  --title "Databricks on Azure Architecture"
```

---

## Generate Infographic

```bash
notebooklm generate infographic "YOUR DESCRIPTION HERE" \
  --notebook 8ea13ced-d2c8-4f31-8944-75eab4794996 \
  --orientation [portrait|landscape|square] \
  --detail [concise|standard|detailed] \
  --style [professional|bento-grid|scientific|sketch-note|editorial|bricks|clay|anime|kawaii|instructional] \
  --wait
```

### Style options tried

| Style | Description |
|-------|-------------|
| `professional` | Clean, corporate look |
| `bento-grid` | Futuristic dark theme with neon glow effects |

### Orientation options

| Option | Best for |
|--------|----------|
| `portrait` | Tall, scrollable detail |
| `landscape` | Wide architectural diagrams |
| `square` | Social/presentation use |

---

## Download

```bash
# From the databricks/ folder
cd /Users/dimitargrigorov/soccer/databricks

notebooklm download infographic OUTPUT_FILENAME.png \
  --notebook 8ea13ced-d2c8-4f31-8944-75eab4794996 \
  --latest \
  --force
```

---

## Infographics Generated

| File | Orientation | Style | Description |
|------|-------------|-------|-------------|
| `databricks_azure_infographic.png` | Portrait | Professional | Initial architecture overview |
| `databricks_azure_landscape.png` | Landscape | Professional | Architecture with Databricks icon |
| `databricks_azure_icons.png` | Landscape | Professional | Both Azure + Databricks icons |
| `databricks_azure_futuristic.png` | Landscape | Bento-grid | Dark cyberpunk, neon glow, circuit patterns |

---

## Full Example (end-to-end)

```bash
NLMDIR=/Users/dimitargrigorov/Documents/Toyota/notebooklm-py
NB=8ea13ced-d2c8-4f31-8944-75eab4794996

# Generate
$NLMDIR/.venv311/bin/notebooklm generate infographic \
  "Futuristic dark theme showing Databricks on Azure with neon glow, Azure icons, Databricks red spark icon, architecture flow and self-evolution pipeline" \
  --notebook $NB \
  --orientation landscape \
  --detail detailed \
  --style bento-grid \
  --wait

# Download
cd /Users/dimitargrigorov/soccer/databricks
$NLMDIR/.venv311/bin/notebooklm download infographic my_infographic.png \
  --notebook $NB --latest --force
```

---

## Tips

- The `--wait` flag blocks until generation is complete (~30–60 seconds).
- Without `--wait` you get a task ID back and can poll with `notebooklm artifact poll`.
- The description drives the content — be specific about icons, colors, layout sections.
- `bento-grid` style produces the best dark/futuristic results.
- Re-run `pip install -e .` if you get `ModuleNotFoundError: No module named 'notebooklm'` — the venv loses the editable install between sessions.
