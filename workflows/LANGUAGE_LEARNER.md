# Language learner editions: English → a chosen target language

Goal: enjoy original English films/series while learning useful expressions in another language. Keep most English dialogue, original actors, music and effects. Replace selected short expressions with understandable target-language speech in a cloned version of the original speaker's voice, with bilingual learning cards.

Choose a target language **and region**, learner level (default A1–A2), explanation language (default English) and preferred density before selecting phrases. The reference workflow was evaluated with European-Portuguese wording and Russian diagnostic examples. Other languages need fresh pronunciation, translation, alignment and listening validation; multilingual model support is not a quality guarantee.

Use [SETUP.md](SETUP.md), then [LEARNER_TOOLS.md](LEARNER_TOOLS.md) for audio.cpp setup and a runnable synthesis example. Unlike the smart-subtitle workflow, this requires source-specific separation, alignment, mixing and delivery code written/adapted by the processing agent. These stages are specified below; no generic dubbing CLI is bundled. Keep that implementation and its dependencies with the run.

The accepted baseline is local **OmniVoice F16 through audio.cpp**, method **E = a clean actor base A + the isolated original phrase D**. Reference settings below are starting points, not universal optima. Use normal capitalization; uppercase target words harmed pronunciation in prior tests. Native regional pronunciation, actor identity and delivery need separate listening checks. ASR content accuracy alone proves none of those.

The Portuguese text in the request example is illustrative: replace the text, full language name, ASR language code and container language tags together. For regional Portuguese, use appropriate vocabulary/grammar and have the actual pronunciation assessed; the `Portuguese` selector alone does not enforce PT-PT.

## 1. Create a new run and inspect the source

Reserve an unused `artifacts/NNNN/` publication number. Work in a separate directory, such as `artifacts/<show>-<episode>-work/`, until validation passes. Do not overwrite published iterations.

Record in a run configuration:

- Source path, SHA-256, duration, frame rate, stream inventory, chapters and metadata.
- Explicit original English audio stream, channel layout, subtitle stream and timestamp offsets.
- Target language and regional wording preference, selection file, actor-library paths.
- Model path/hash, audio.cpp version/build, generation settings, ASR settings.
- Output paths, track titles/languages/dispositions, subtitle policy and review windows.

Inspect rather than assume stream indices:

```bash
ffprobe -v error -show_format -show_streams -show_chapters -of json "$SOURCE" > "$RUN/source-info.json"
```

Set `SOURCE` and `RUN` to the intended input and existing work directory first. Confirm the English track by listening/transcription; the first audio track may be Russian or Ukrainian.

Decode the selected English track **sequentially once** to 48 kHz float PCM, retaining its channel layout. Prefer sample-index crops from this full PCM for all later processing. Independently seeking into compressed audio can produce small differences that invalidate subtraction and alignment.

The reference production implementation used six channels and the center channel for dialogue analysis. Stereo, mono, and other surround layouts need adapted extraction, separation, and downmix logic. Do not assume a center channel exists.

## 2. Manually select useful expressions

Read the **whole subtitle transcript**, then inspect the actual audio around each candidate. Subtitles guide navigation; independent voice-to-text determines the actual spoken words. Never feed the expected subtitle text into the recognizer as a prompt for validation.

Prefer:

- Greetings, thanks, apologies, short replies, requests, help, feelings, family and everyday activities.
- Short standalone phrases, or meaningful clauses at the start/end of a turn.
- Slower speech, clean dialogue and genuine pauses that can accommodate target-language speech.
- Useful A1–A2 chunks, including very simple expressions; CEFR classification is an editorial approximation.

Avoid overlapping speakers, loud music, fast exchanges, obscure jokes, technical vocabulary, and delicate mid-word or mid-sentence splices. Identify the correct actor, including guests.

Aim for a learner expression roughly every **15–20 seconds where suitable**. Inspect local spacing, not just the average. Do not compensate for a gap with a dense cluster. Preserve themes and unsuitable scenes and explain substantial gaps. A useful reference run had a median spacing around 19 seconds, with longer gaps for the opening theme; this is not a strict grid.

Save the manual selection before synthesis. For each entry retain:

- Stable ID, source/subtitle reference, speaker and scene context.
- Actual English expression, target-language replacement and its exact English meaning.
- Source interval, intended replacement boundary and available following pause.
- Learner usefulness, selection rationale, and any manually nominated backup.
- Boundary/wording changes, exclusions and reasons.

Use [examples/learner-selection.json](../examples/learner-selection.json) as a starting schema. Keep an initial editorial selection and a final render selection; the latter must reflect every approved refinement and the actual rendered result.

Automatic tools may align and rank takes **inside manually chosen locations**. They must not silently select new scenes or backfill rejected locations. Retry, simplify the same expression, use a safe pause, or leave the original English and record the omission.

## 3. Transcribe, separate and align

Reference components (install/configure separately; not bundled):

| Purpose | Component |
| --- | --- |
| Independent speech recognition | faster-whisper, Whisper large-v3, a separate ASR environment |
| Primary speech separation | BandIt v2 speech/music/effects separation |
| Separation fallback | HTDemucs vocals |
| Forced word alignment | `torchaudio.pipelines.MMS_FA` and `uroman` |
| Speaker similarity diagnostic | SpeechBrain ECAPA, CPU, a local model cache |
| Media assembly | FFmpeg/ffprobe, NumPy/SciPy/SoundFile |

Whisper baseline: CUDA `int8_float16`, beam size 5, `condition_on_previous_text=False`, `vad_filter=False`; word timestamps for source analysis. Specify the relevant language, but supply no expected-text prompt.

For each selected region:

1. Extract enough context to distinguish preceding/following words and speakers.
2. Transcribe original English independently.
3. Separate dialogue and save both the isolated voice and residual bed.
4. Transcribe isolated voice and residual independently to check retained and removed speech.
5. Force-align the actual recognized words. Inspect uncertain boundaries against Whisper timings and longer context.
6. Save word spans, replacement interval, safe insertion limit and separation diagnostics.

The reference source gate accepts dialogue-to-residual ratio ≥6 dB, or ≥−3 dB when the target is recognized in isolated speech and absent from residual ASR. This is a screening heuristic, not proof that speech was completely removed. Listen for leakage and damage to the bed.

For six-channel sources, fallback separation processes FL/FR/FC/BL/BR and preserves LFE. HTDemucs may require mono duplication and resampling to 44.1 kHz, followed by conversion back to 48 kHz. Record which separator was used per region.

Do not globally replace forced alignment with Whisper word boundaries: either can absorb pauses or truncate quiet endings. Keep explicitly reviewed exceptions with reasons. Include the complete original expression, exclude adjacent speakers, and use longer context when a word appears to cross a clip boundary.

Prior processing exposed a short-clip alignment failure: source ASR omitted the following utterance, and forced alignment placed an apology against that later speech. Aligning a longer independently transcribed context corrected it. Check suspicious boundaries against waveform energy as well as both aligners, then recheck separation for the corrected interval.

Before subtraction, verify that each source crop matches the full sequential PCM. The current check uses correlation >0.999 and RMS error <`max(1e-5, 0.03 * source_RMS)`, with lag search ±480 samples at 48 kHz. If it fails, rebase and re-separate from the actual full PCM. Do not relax the gate to hide an extraction mismatch.

## 4. Build voice method E

**A** is a clean base reference for the correct actor. **D** is the isolated original phrase being replaced. **E** concatenates A, 180 ms of silence, then D, with the matching transcript in the same order.

- Use 48 kHz mono references.
- Normalize each component conservatively toward RMS 0.08, with peak cap 0.95 and maximum gain 10.
- Apply short approximately 5 ms edge fades.
- Save A provenance, D boundaries, component gains, composite WAV and exact reference transcript.
- Prefer clean A samples with compatible delivery. Build a speaker library across episodes when helpful, keeping actor identity and source provenance explicit.
- For guests, obtain a separate reference of that actor. Never borrow another actor's voice because the library lacks an entry.

Build a new actor library from the supplied media. The repository includes no actor recordings; save reference paths, source timestamps and exact transcripts in your run configuration.

OmniVoice conditions on reference audio/acoustic representation and text. It is not being controlled by a single averaged speaker vector. ECAPA embeddings are separate evaluation features; averaging them does not implement A+D conditioning.

A full-English reconstruction is a useful control. When D contains that same utterance, it is an optimistic source-conditioned test, not an independent generalization test.

## 5. Generate multiple local takes

Current paths:

```text
.tools/audio.cpp/build/local-cuda/bin/audiocpp_cli
.cache/audio-cpp-models/OmniVoice-GGUF/omnivoice-f16.gguf
```

Example request item in a request-sequence JSON array:

```json
{
  "id": "scene001__pt-43-s0.9",
  "text": "Precisas de ajuda?",
  "language": "Portuguese",
  "voice_ref": "/absolute/path/to/reference.wav",
  "options": {
    "reference_text": "Actual transcript of A followed by actual transcript of D.",
    "num_inference_steps": 32,
    "guidance_scale": 2.0,
    "seed": 43,
    "speed": 0.9
  }
}
```

Run from the repository, after preparing the request file and directories:

```bash
export HF_HOME="$PWD/.cache/huggingface"
export TORCH_HOME="$PWD/.cache/torch"
.tools/audio.cpp/build/local-cuda/bin/audiocpp_cli \
  --task clon --family omnivoice \
  --model .cache/audio-cpp-models/OmniVoice-GGUF/omnivoice-f16.gguf \
  --backend cuda --mode offline --threads 6 \
  --request-sequence "$RUN/requests.json" \
  --out-dir "$RUN/batch" --out-format float32 --metrics --log
```

Start with seeds **43, 44, 45, 46** × generation speeds **0.90, 0.95**: eight takes per expression. These are a working search space, not universally optimal values.

Use normal capitalization. **Do not uppercase target words to force pronunciation**; that harmed previous results. Use the model’s supported full language name. The Portuguese baseline uses `Portuguese` without an accent instruction. Choose region-appropriate wording, then evaluate pronunciation separately.

A 16 GB NVIDIA GPU is sufficient for the established local workflow when memory is managed. Check available VRAM and serialize heavy stages when necessary. Do not terminate unrelated GPU workloads. Locate the CUDA SDK on the actual host; do not assume a fixed installation path.

## 6. Rank, fit and mix

Evaluate each raw take for independent target-language ASR, complete endings, duration and speaker similarity. Use ECAPA similarity to help rank eligible takes, not as a sole acceptance criterion. Short and cross-language comparisons are noisy; untouched English must not dominate the similarity score.

Fit the best takes into the safe source interval:

- Prefer shorter wording or genuine pauses over accelerated target-language speech.
- Record generation speed separately from post-generation `atempo`.
- Current post-processing range is 0.75–1.0×; do not accelerate beyond 1.0×. Excessive slowing may also hurt intelligibility, so compare less-stretched takes.
- Preserve quiet final consonants. Pad approximately 400 ms before `atempo` to flush its analysis window and retain approximately 160 ms after speech where space permits.
- Place end fades after voiced content, not through the last syllable.

Subtract isolated original dialogue only within the approved window, using short approximately 12 ms internal fades. Retain the original bed and surrounding English. Add generated voice with conservative spatial balance. Reference six-channel mixing uses center plus limited FL/FR/BL/BR contributions, clamped to at most 0.3 relative to center; leave LFE intact.

The current loudness recipe starts from source-relative voice RMS gain 1.2 and an additional 3 dB boost, with per-expression adjustments subject to headroom. Treat these as starting settings: verify audibility, finite samples, unclipped peaks (approximately 0.97 ceiling) and natural scene balance.

Before PCM24 quantization, check sample identity outside all edited windows.

The reference six-channel stereo downmix is (verify actual channel order):

```text
left  = .375*FL + .265*FC + .265*BL + .095*LFE
right = .375*FR + .265*FC + .265*BR + .095*LFE
```

Use the same downmix for review videos and the delivered stereo track. Adapt coefficients and channel names for other layouts.

## 7. Optimize against the actual delivered track

This is candidate search, evaluation and refinement; no reinforcement-learning weight training is implemented.

1. Assemble the full candidate learner track and mux it.
2. Sequentially decode the actual default stereo track, then crop expressions by PCM sample index.
3. Independently transcribe every target-language insertion without expected-text prompting.
4. Compare recognized words with the intended text using documented normalization.
5. Diagnose failures using raw take, fitted take, residual bed, final mix and source boundaries.
6. Try eligible alternate takes, gentler stretching and modest gain changes in the exact final downmix/PCM24 context.
7. Freeze choices, rebuild, and recheck the **actual final file**.

Current probe choices include extra gains of 0, 1.5 and 3 dB above the baseline and playback-rate floors of 0.9 or 1.0. Prefer the least boost that passes while retaining good voice similarity and headroom.

Normalize punctuation/case and documented equivalents carefully. A Portuguese-specific checker may account for number forms, `por que`/`porque`, `pra`/`para`, and `tá`/`está`; it must not erase negation, gender or meaningful verb differences such as `estás`/`estão`. Do not weaken criteria merely to finish a run.

A raw-generation pass or a probe-crop pass does not establish a delivered-track pass. Seeking directly into a Matroska file can change tiny crop offsets; final checks use sequential decoding. Center-channel checks are useful diagnostics, but the default stereo track is the accepted delivery criterion. Separately validate any alternative track for which quality claims are made.

Keep failures and retries in the assessment. A default-stereo pass may still differ from a center-only diagnostic; report them separately. Content accuracy does not prove native accent, emotional delivery, or actor identity.

## 8. Create learner subtitles

Use persistent replacement cards. The default subtitle track is **“Learning phrases only”**; full English-plus-learner captions remain optional:

- Target-language text in yellow (`#ffff00`), with its English meaning underneath.
- No `PT:`, `PR:` or `EN:` prefixes.
- One meaningful expression per card; do not slash-merge unrelated turns.
- **Five seconds per learning card**, normally from the replacement onset.
- The English translation must match the target-language speech actually spoken, not the entire original subtitle cue.
- Keep surrounding English, including unreplaced portions of partially translated cues.

In full ASS subtitles, place learning cards above continuing English dialogue so the next line does not cut the card short or disappear. The current layout uses PlayRes 384×288, Arial 16, normal English MarginV 10 and learner MarginV 66; adapt and inspect frames for other presentation sizes.

For a full SRT fallback, split the timeline into nonoverlapping intervals containing all active text. Repeat the learning card while the continuing English changes, preserving its logical five-second display. Do not rely on overlapping SRT cues. Avoid overlapping learner cards by fixing selection spacing rather than merging expressions.

Provide full learner subtitles and replacements-only subtitles in ASS and SRT. Account for any final container timestamp shift in embedded and sidecar subtitles. Validate durations, translation text, yellow styling and representative rendered frames.

If only caption timing/style changes, remux with audio/video stream copy. Do not regenerate voices unnecessarily.

## 9. Package and verify the full MKV

Preserve original video, all original audio/subtitle streams, chapters and metadata. Append:

1. Default learner stereo, **FLAC 24-bit**.
2. Alternative learner surround, currently AC3 640 kb/s for the six-channel source.
3. Full learner ASS subtitles, available as an alternative.
4. **Default “Learning phrases only” ASS subtitles**, showing only replacement cards.

Derive mappings and output codec/disposition indices from the actual stream inventory. FFmpeg audio/subtitle output indices are per stream type, not global stream indices. Even consecutive episodes may have different numbers of original audio tracks. Hardcoded counts previously assigned the wrong codecs/track settings.

Use and verify appropriate interleaving. `-max_interleave_delta 0` was needed in this workflow to prevent learner audio packets arriving too late in file order, which made opening sound disappear during playback.

Check:

- Output codecs, channel layouts, track names, language tags, default dispositions and duration.
- Compressed payload hashes of retained original streams; original subtitle content, timing and relative offsets.
- A single consistent timestamp relationship across video, original tracks, learner tracks and captions; encoder priming can introduce a small shift, so measure rather than assume it.
- Opening/theme audio via sequential decoding of an untouched interval, compared with the original downmix.
- Learner audio packets arriving alongside early video packets, not merely existing somewhere in the file.
- Final-track ASR for every insertion, unclipped endings and unchanged audio outside edit windows.

Before publishing, fully decode the final video and every audio track, check the exit code and retain the log:

```bash
ffmpeg -nostdin -v error -xerror -threads 2 -i "$OUTPUT" \
 -map 0:v -map 0:a -f null - 2> "$RUN/final-decode.log"
```

A probe or short sample is insufficient. Save source/output hashes and original stream preservation checks with the final delivered-track ASR results. Keep originals by default; failed verification never authorizes source deletion.

## 10. Publish a reviewable iteration

Use the next unused four-digit `artifacts/NNNN/` folder. Include at least:

| Artifact | Purpose |
| --- | --- |
| `index.html` | Review entry point; prominent pronunciation comparison player |
| `original.mp4` | All reviewed source sections in order |
| `rendered.mp4` | Matching rendered sections, timeline/frame count aligned |
| `mixed.mp4` | Original section 1 → rendered section 1 → original section 2 → rendered section 2… |
| `pronunciation-comparison.mp4` | Comparison of current options; for a single option may reuse the mixed reel |
| `assessment.txt` | Method, changes, measurements, failures, uncertainty and listening notes |
| `sections.json` | Review/source timeline mapping |
| Metrics and reports | Content checks, similarity diagnostics, density, separation, startup and stream checks |
| Frozen selection and take map | Exact phrases, chosen requests, seeds, gains, rates and boundaries |
| Pipeline/configuration and raw diagnostics | Reproducibility and failure history |
| Manifest | SHA-256 and sizes of all published files except the manifest itself |
| Full MKV and subtitle sidecars | When full-episode output is requested |

For Russian experiments, `mixed-ru.mp4` means selected injections and `mixed-ru-full.mp4` means full translated expressions. For other languages use their own language codes; publish only comparisons actually generated.

Validate playable media, matching comparison timelines, relative HTML links, required files and exact manifest coverage with explicit run-specific validation before atomic publication. Update `artifacts/index.html` with newest first. Never mutate previously published artifacts; hardlink unchanged assets only if neither link will subsequently be modified.

## 11. Reruns and cache discipline

Persist the exact final selection and selected generation requests, not just an early draft. Retain reference PCM/transcripts, source and model hashes, software versions, seeds, generation speed, post-processing rate, gains, replacement windows, separation method and final delivery reports.

For semantic generation cache keys, hash decoded reference PCM plus sample rate, reference transcript, target text, model/settings and seed. WAV container metadata can change while samples remain identical. File-byte SHA-256 is still appropriate for artifact integrity, but it is a different purpose.

Invalidate only affected entries when audio, text, references, boundaries or parameters change. Ensure ASR results belong to the exact evaluated waveform; never reuse pre-retry ASR for new audio. Preserve superseded results for audit.

Allow one owner per output batch/log. Do not evaluate partially written WAV files. If interrupting an owned generation job, stop its audio.cpp child as well as its Python parent; a surviving child can continue writing stale outputs. Do not terminate unrelated processes.

Budget disk space for full multichannel float PCM, learner PCM, review clips and publication copies; one episode can require several gigabytes.

