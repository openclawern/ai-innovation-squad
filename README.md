# GovTech AI Innovation Squad — Take-Home Assessment

## Contents

```
.
├── section1-prospection-report/
│   └── prospection-report-openclaw.md    # Prospection report on OpenClaw / agent platforms
├── section2-exam-analyzer/
│   ├── main.py                           # FastAPI web application
│   ├── analyzer.py                       # Core analysis logic (PDF extraction + LLM)
│   ├── evaluate.py                       # Evaluation framework + demo results
│   ├── requirements.txt                  # Python dependencies
│   ├── templates/
│   │   ├── index.html                    # Upload UI
│   │   └── results.html                  # Results dashboard
│   └── README.md                         # Section 2 detailed README
└── README.md                             # This file
```

## Quick Start — Section 2

```bash
cd section2-exam-analyzer
pip install -r requirements.txt

# Optional: configure API key for live LLM analysis
echo "ANTHROPIC_API_KEY=your_key_here" > .env
# or
echo "OPENAI_API_KEY=your_key_here" > .env

# Start the app
python main.py
# → Open http://localhost:8000
```

Then upload any syllabus PDF + exam paper PDF to get an alignment and weightage analysis.

The tool runs in **demo mode** (no API key needed) for the O-Level History specimen paper.

## Running the Evaluation

```bash
cd section2-exam-analyzer
python evaluate.py --demo
```

See `section2-exam-analyzer/README.md` for full evaluation details.
