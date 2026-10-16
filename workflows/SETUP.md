# Setup and tool boundaries

Run commands from the SmartSubtitles repository root. Use Python 3.11+, FFmpeg/ffprobe with libass and libx264, and Graphviz `dot` for relationship diagrams. These are system dependencies; inspect available tools before installing anything. GPU transcription was used with a 16 GB NVIDIA card. Serialize GPU-heavy ASR, separation and TTS stages.

```bash
python3 --version
ffmpeg -version
ffprobe -version
dot -V
nvidia-smi
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -c 'import faster_whisper, ctranslate2; print(faster_whisper.__version__, ctranslate2.__version__, ctranslate2.get_supported_compute_types("cuda"))'
```

`requirements.txt` pins the direct smart-workflow dependencies to the reference environment. `requirements-asr-reference.txt` is its historical full ASR environment export, for diagnosis rather than a universal installation guarantee. CUDA/cuDNN runtime compatibility depends on your host; a CUDA SDK alone does not supply every library CTranslate2 needs. Do not change working system libraries blindly. A clean installation on a new host has not been validated by including these pins.

Download a fixed ASR snapshot and use its returned absolute path:

```bash
.venv/bin/python - <<'PY'
from huggingface_hub import snapshot_download
print(snapshot_download('Systran/faster-whisper-large-v3',
 revision='edaa852ec7e145841d8ffdb056a99866b5f0a478', cache_dir='.cache/models'))
PY
export ASR_MODEL='/absolute/path/printed/above'
export ASR_DEVICE=cuda
export ASR_COMPUTE_TYPE=int8_float16
```

For CPU, explicitly set `ASR_DEVICE=cpu` and `ASR_COMPUTE_TYPE=int8` and record the change. The supplied ASR tools recognize English; target-language validation for learner audio needs the target language specified in its own ASR pass. They accept `ASR_MODEL`, `ASR_DEVICE` and `ASR_COMPUTE_TYPE` environment variables. Without `ASR_MODEL`, `large-v3` is an unpinned alias. Record model revision and library versions, not just its friendly name.

## Included utilities

| Tool in `tools/` | Use |
| --- | --- |
| `smart_subtitles_asr.py AUDIO OUTPUT` | Full English audio → incremental JSON with word timestamps; VAD on |
| `smart_subtitles_entry_asr.py AUDIO SRT DIR --padding 0.2` | Every source cue → independent ASR, comparison and coverage; VAD off |
| `smart_subtitles_context.py CONFIG` | Agent-selected disputed cues, ±3 seconds of context |
| `smart_subtitles_delivery.py CONFIG mux` | Preserve original streams, add approved ASS, set English/smart defaults |
| `smart_subtitles_delivery.py CONFIG verify` | Compare preserved payloads/captions, check defaults and fully decode |
| `smart_subtitles_delivery_smoke.py` | Two-second synthetic initial delivery and rerun verification |
| `embed_guide_images.py HTML` | Embed local image sources as data URLs; no caption/content decisions |
| `render_guide.py MARKDOWN` | Render offline HTML next to Markdown and embed its illustrations |

Run the mechanical packaging smoke test:

```bash
.venv/bin/python tools/smart_subtitles_delivery_smoke.py
```

It uses a fresh temporary directory and FFmpeg, without ASR, real media or GPU. It does not validate speech quality or your final movie.

## Learner audio extras

See [LANGUAGE_LEARNER.md](LANGUAGE_LEARNER.md). Smart subtitles do not require TTS, voice cloning, separation or Torch. Learner audio additionally requires audio.cpp/OmniVoice, a separator, alignment, audio mixing and optionally speaker embeddings. Keep those dependencies in a separate environment so their Torch/CUDA requirements do not break transcription.

The package contains the editorial workflow and reference settings for learner audio, not a generic end-to-end dubbing application. An independent agent must implement/adapt the per-source audio processing with the documented gates, and save that implementation with each run. Model weights, original actor recordings and episode-specific processing scripts are intentionally excluded.
