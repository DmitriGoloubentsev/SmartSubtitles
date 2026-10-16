# Package validation

Validated on 2026-10-16:

- All bundled Python files parse successfully.
- All example JSON files parse successfully.
- Relative documentation links resolve inside this folder.
- Synthetic SVG illustration renders into standalone HTML and decodes byte-for-byte.
- Synthetic two-second MKV: original-stream preservation, smart subtitle defaults, full decode and rerun replacing the smart track pass with Python 3.11.
- Upload contents contain only Markdown, Python, JSON, requirements text and `.gitignore`; no local home paths or media assets.

The system `python3` here is 3.10 and cannot run `hashlib.file_digest`; use the documented Python 3.11+ environment. Fresh dependency installation, fresh audio.cpp compilation, ASR inference and end-to-end learner dubbing were not rerun as part of preparing this documentation package. No media-processing result is claimed by these packaging checks.
