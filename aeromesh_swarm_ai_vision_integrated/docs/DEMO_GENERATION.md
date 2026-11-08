# Demonstration Generation Guide (Updated)

## Two Options for Creating Demonstration Materials

### Option 1: PNG Snapshots (Recommended - No FFmpeg Required)

**Advantages:**
- ✅ Works on all platforms without additional software
- ✅ High-quality images (200 DPI)
- ✅ Easy to include in presentations/documents
- ✅ Fast generation (< 2 minutes)

**Command:**
```bash
python generate_demo_snapshots.py 3
```

**Output:**
- Creates folder: `scenario_3_snapshots/`
- Contains 6-8 PNG images showing mission progression
- Perfect for inclusion in technical reports and presentations

**Snapshot Times:**
- t=0s (Initial deployment)
- t=30s (Task allocation)
- t=60s (First surveys)
- t=120s (Mid-mission)
- t=180s (Critical events)
- Mission completion

---

### Option 2: Video Recording (Requires FFmpeg)

**Only use if you have FFmpeg installed**

If you want MP4 video output, install FFmpeg first:

**Windows:**
```bash
# Download from https://ffmpeg.org/download.html
# Or use chocolatey:
choco install ffmpeg
```

**Linux/macOS:**
```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg
```

Then run:
```bash
python run_simulation.py --scenario 3 --record
```

---

## For Your Submission

**Use PNG Snapshots** - they are:
- ✅ Easier to generate
- ✅ Higher quality for documents
- ✅ Work on all systems
- ✅ Can be combined into a PDF presentation

You can create a simple demonstration document by:
1. Generating snapshots for your best scenario (e.g., Scenario 3)
2. Arranging them in a PowerPoint/PDF with captions
3. Submitting as part of your demonstration materials

---

## Quick Demo Generation

```bash
# Generate snapshots for all 4 scenarios
python generate_demo_snapshots.py 1
python generate_demo_snapshots.py 2
python generate_demo_snapshots.py 3
python generate_demo_snapshots.py 4
```

This creates 4 folders with timestamped snapshots showing:
- Initial UAV deployment
- Task allocation and survey operations
- Communication mesh links
- Self-healing and fault recovery (Scenario 3)
- Battery management and handoffs (Scenario 4)
