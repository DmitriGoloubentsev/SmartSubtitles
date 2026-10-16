# Learner audio: tools and synthesis setup

Read [LANGUAGE_LEARNER.md](LANGUAGE_LEARNER.md) for the editorial and audio-quality gates. These commands synthesize candidates, not a finished movie.

## Reference runtime

The established runtime is [audio.cpp](https://github.com/0xShug0/audio.cpp), reference commit `6796068942c4ae6f55299371983b3d05ef8389ee`, with the [OmniVoice F16 package](https://huggingface.co/audio-cpp/audio.cpp-gguf). These are external dependencies with their own licenses; no source or weights are redistributed here.

On a host with CMake, a C++ toolchain and compatible CUDA SDK:

```bash
git clone https://github.com/0xShug0/audio.cpp .tools/audio.cpp
git -C .tools/audio.cpp checkout 6796068942c4ae6f55299371983b3d05ef8389ee
git -C .tools/audio.cpp submodule update --init --recursive
cmake -S .tools/audio.cpp -B .tools/audio.cpp/build/local-cuda \
 -DCMAKE_BUILD_TYPE=Release -DAUDIOCPP_MODEL_SET=custom \
 -DAUDIOCPP_MODELS=omnivoice -DENGINE_ENABLE_CUDA=ON -DGGML_CUDA=ON
cmake --build .tools/audio.cpp/build/local-cuda --target audiocpp_cli -j 4
```

If CUDA is not discovered, pass `-DCMAKE_CUDA_COMPILER=/actual/cuda/bin/nvcc` at configuration. Inspect that revision's build instructions for host-specific dependencies. Do not assume a build on this machine proves a clean build on another host.

Download the model explicitly:

```bash
.venv/bin/python - <<'PY'
from huggingface_hub import hf_hub_download
print(hf_hub_download(repo_id='audio-cpp/audio.cpp-gguf',
 filename='OmniVoice-GGUF/omnivoice-f16.gguf',
 local_dir='.cache/audio-cpp-models'))
PY
sha256sum .cache/audio-cpp-models/OmniVoice-GGUF/omnivoice-f16.gguf
```

The historical package recorded etag `f8e398d32f4a7dd6e0519bd17ffeb603d120e6dd9713bde63b8c7d7bb2b91938` and size 1,639,548,768 bytes. Its downloader recorded revision `main`, not an immutable commit; do not claim that is a reproducible model revision. Record the newly resolved Hugging Face revision and file SHA-256 in your run; if bytes differ, rerun evaluation rather than silently treating it as the same model.

## Reference preparation and target requests

Use audio recorded/provided with appropriate rights. Establish actor identity and actual words from the source audio. Build a clean base reference A and a phrase reference D in 48 kHz mono, with their exact transcripts. Method E concatenates normalized A, 180 ms silence, normalized D; normalize components toward RMS 0.08 with maximum gain 10 and peak cap 0.95, applying approximately 5 ms edge fades. Keep complete words and actual pauses. Save source timestamps, gain, PCM hashes and reference transcript in matching A→D order.

Set `RUN` to a new work directory; prepare `requests.json` as an array of request objects (see the main workflow's synthetic request example), with absolute `voice_ref` paths. Use the actual chosen language selector and language-appropriate target text. Start with seeds 43–46 and speeds 0.90/0.95; preserve every candidate and its parameters.

```bash
export RUN='/absolute/path/new-run'
export HF_HOME="$PWD/.cache/huggingface"
export TORCH_HOME="$PWD/.cache/torch"
.tools/audio.cpp/build/local-cuda/bin/audiocpp_cli \
 --task clon --family omnivoice \
 --model .cache/audio-cpp-models/OmniVoice-GGUF/omnivoice-f16.gguf \
 --backend cuda --mode offline --threads 6 \
 --request-sequence "$RUN/requests.json" \
 --out-dir "$RUN/batch" --out-format float32 --metrics --log
```

## Components the processing agent must wire together

- Independent ASR: faster-whisper large-v3, target language explicitly specified, beam 5, no expected-text prompt, VAD off for insertion checks. The included smart ASR tools are English-specific; implement the target pass separately and retain words/timestamps/settings.
- Speech separation: reference primary BandIt v2 speech/music/effects model; HTDemucs vocals is a fallback requiring particular care for speech leakage and lost background. Pin repository/model revisions and follow their installation instructions in a separate environment. Save speech and residual bed and verify their sum against the source.
- Alignment: `torchaudio.pipelines.MMS_FA` with `uroman` where appropriate. Align actual transcribed words; verify the chosen tool supports the target language before using target word spans. Short clips can misalign. Inspect boundaries against longer context and waveform energy.
- Identity diagnostic: SpeechBrain ECAPA on isolated generated voice versus clean same-actor references. It is a ranking aid, not an accent or identity guarantee.
- Mixing: NumPy/SciPy/SoundFile plus FFmpeg, operating on sequentially decoded PCM with explicit channel layouts. Preserve music/effects, original audio outside approved windows, endings and opening soundtrack.
- Delivery: construct source-dependent FFmpeg maps, keeping all original tracks and appending learner tracks/captions. The included `smart_subtitles_delivery.py` preserves audio; it does **not** add learner audio. Implement the learner mux/verification stage described in the main workflow.

Do not copy another title's hardcoded stream indices, crop boundaries or actor references. Save the implemented pipeline with exact dependencies and configuration under the run's `pipeline/` folder. The workflow describes the accepted method; this repository does not claim to contain a one-command reproduction of every historical media experiment.
