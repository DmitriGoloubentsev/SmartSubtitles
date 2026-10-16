# Smart subtitles for a movie or standalone video

Goal: retain the original English viewing experience while providing occasional listening and cultural help. Default proficiency is C1, configurable. English audio and the new smart subtitle track become the defaults; all original streams remain available.

## 1. Editorial policy

The agent authors the complete caption file after reading **all** source subtitles, full-track ASR and every-entry ASR. Scripts never select captions or generate their text. A proficiency change requires a new editorial pass, not relabelling a track.

- Omit clear, ordinary dialogue, basic greetings and fillers. No density quota.
- Remove sound descriptions, speaker labels, music labels and background song lyrics. Inspect complete song blocks; uppercase alone is not an SDH test.
- For reduced speech, difficult accents, overlap or hard-to-hear delivery, show the smallest useful span. A basic word can still deserve a caption if this delivery is unclear.
- ASR mismatches flag review, not automatic inclusion. Check timing, homophones, contractions, hallucinations, subtitle mistakes and longer context. Successful ASR also does not prove human audibility.
- Explain unfamiliar slang, rare expressions and cultural/local references with a very short English definition in square brackets. Research the meaning in context and record URLs. Do not add spoilers or confuse a story location with a filming location.
- Show each canonical unfamiliar term/reference at most three times. Spoken common names: once; difficult/unusual names: up to three times. Aliases and inflections share a counter. Do not show a name merely because its character appears.
- After a cap, genuinely unclear speech can receive plain audibility text without another definition; record that exception.
- Prefer 1–2 lines, 2–4 seconds (up to 5 when needed), around 18 characters/second. Keep speech timing, readable pause extensions and nonoverlapping cards. Manually resolve dense passages.

## 2. Inspect source and gather complete evidence

Follow [SETUP.md](SETUP.md). Replace the example paths and indices after probing. Never assume the first soundtrack is English.

```bash
export SOURCE='/absolute/path/movie.mkv'
export MEDIA_DIR='/absolute/path/delivery'
export WORK="$MEDIA_DIR/smart-subtitles/movie"
export OUTPUT="$MEDIA_DIR/movie.smart-English.mkv"
mkdir -p "$WORK"
ffprobe -v error -show_streams -show_format -show_chapters -of json "$SOURCE" > "$WORK/source-info.json"
sha256sum "$SOURCE" > "$WORK/source.sha256"
# Set these from the actual inventory and check their content:
export AUDIO_INDEX=1
export SUBTITLE_INDEX=2
ffmpeg -nostdin -v error -n -i "$SOURCE" -map "0:$SUBTITLE_INDEX" "$WORK/source.srt"
ffmpeg -nostdin -v error -n -i "$SOURCE" -map "0:$AUDIO_INDEX" -ac 1 -ar 16000 -c:a pcm_s16le "$WORK/english.wav"
```

Bitmap subtitles require OCR and manual correction. If no subtitles exist, use full ASR to establish a complete timed transcript, manually correct it, and audit its intervals. Record that provenance rather than claiming it is supplied source subtitles. Delivery audio is always the original stream, not this analysis WAV.

Run sequentially, checking each exit status; in a shell wrapper use `set -e`:

```bash
OMP_NUM_THREADS=6 .venv/bin/python tools/smart_subtitles_asr.py \
 "$WORK/english.wav" "$WORK/full-asr.json" > "$WORK/full-asr.log" 2>&1
# Create only after the previous command has succeeded:
printf '{"complete":true}\n' > "$WORK/full-asr-complete.json"
OMP_NUM_THREADS=6 .venv/bin/python tools/smart_subtitles_entry_asr.py \
 "$WORK/english.wav" "$WORK/source.srt" "$WORK/entry-asr" \
 --padding 0.2 > "$WORK/entry-asr.log" 2>&1
```

Full JSON is written incrementally: its existence does not establish completion. Save settings and model/source/audio hashes beside it. Verify every-entry coverage: all source IDs present exactly once, no missing IDs, source count equals result count. The resumable entry tool hashes its inputs/settings; changed inputs require a fresh output directory. Never inject expected subtitle words into ASR prompts.

Read every cue and every ASR result, including omitted cues and speech outside source subtitles. For disputed entries, author `context-config.json`:

```json
{"work_dir":"/absolute/path/delivery/smart-subtitles/movie","context_review_cues":[12,45]}
```

```bash
.venv/bin/python tools/smart_subtitles_context.py "$WORK/context-config.json"
```

Choose IDs manually. Inspect/listen to source scenes when needed. Same-model context recognition is additional evidence, not independent proof of audibility.

## 3. Save the agent's decisions and captions

Save:

- `smart.srt`: the entire approved caption track.
- `authored-events.json`: caption ID, start/end, literal text, source IDs, reason tags and canonical ledger keys.
- `entry-review.json`: one record per source cue, with source ID, reference, ASR, decision, caption IDs, reasons, uncertainty and `manual_review:true` after actual review.
- `editorial-notes.md`: sound/song omissions, unresolved readings, cap exceptions, research citations and visual evidence.
- `terms.json`: canonical names/terms, aliases, occurrences, meanings and actual displayed cards.

A schema illustration is in [examples/review-record.json](../examples/review-record.json). Do not auto-fill manual approval fields for unread cues.

Validate ordered IDs, start < end, bounds within source duration, no overlaps and readable duration. Format only approved text:

```bash
ffmpeg -nostdin -v error -n -i "$WORK/smart.srt" "$WORK/smart.ass"
```

Set an appropriate ASS header/style: reference presentation is 1920×1080, DejaVu Sans 46, white, outlined, bottom centre. Keep event wording/timing unchanged; inspect how it scales on the actual source. Preview an actual caption timestamp (120 is only an example):

```bash
ffmpeg -nostdin -v error -n -i "$SOURCE" \
 -vf "ass='$WORK/smart.ass'" -ss 120 -frames:v 1 "$WORK/caption-preview.jpg"
```

Use a filter-safe work path or escape FFmpeg filter special characters. Inspect representative early/late captions, definitions and dense scenes.

## 4. Package and verify

Create the configuration from actual paths. For a fresh source, omit `preserve_streams` to retain every original stream:

```bash
.venv/bin/python - <<'PY'
import json, os
from pathlib import Path
w=Path(os.environ['WORK'])
c=dict(source=os.environ['SOURCE'],output=os.environ['OUTPUT'],work_dir=str(w),
 approved_ass=str(w/'smart.ass'),level='C1',reviewed_level='C1',
 english_audio_stream=int(os.environ['AUDIO_INDEX']))
(w/'delivery-config.json').write_text(json.dumps(c,indent=2))
PY
.venv/bin/python tools/smart_subtitles_delivery.py "$WORK/delivery-config.json" mux
.venv/bin/python tools/smart_subtitles_delivery.py "$WORK/delivery-config.json" verify
```

Set both level fields to the genuinely reviewed level. The muxer refuses to overwrite its source or an existing output. It stream-copies originals, adds approved ASS and sets a single English audio default and a single smart subtitle default. Original music stays untouched.

Verification compares original A/V payload hashes, subtitle text/timing (or bitmap packet hashes), attachments, codec/layout, chapters, duration, language/title tags, default dispositions and exact added ASS events/style. It fully decodes all video/audio with FFmpeg `-xerror`. Success produces `final-verification.json` with source/output hashes; check the command succeeded on this exact output, not an old record. A failed decode remains a failure even if inherited from the source: document it and retain the original.

On reruns, inventory the retained final file and explicitly set `preserve_streams` to the original stream indices, replacing the old smart track instead of accumulating duplicates. Never copy example indices without inspection. Run to a new candidate path and verify before promotion.

## 5. Guide, portable HTML and retention

Manually author `movie-guide.md` at the media root: spoiler-labelled overview, detailed timeline, characters/cast, relationships, terminology, uncertainties and source references. Read the media and inspect silent plot beats; a web synopsis cannot replace that review. Use actual video stills, labelled with source time:

```bash
mkdir -p "$MEDIA_DIR/smart-subtitles/images"
ffmpeg -nostdin -v error -n -ss 120 -i "$SOURCE" -frames:v 1 -vf scale=960:-2 \
 "$MEDIA_DIR/smart-subtitles/images/movie-0120.jpg"
# After the agent writes relationships.dot:
dot -Tsvg "$MEDIA_DIR/smart-subtitles/images/relationships.dot" \
 -o "$MEDIA_DIR/smart-subtitles/images/relationships.svg"
.venv/bin/python tools/render_guide.py "$MEDIA_DIR/movie-guide.md"
```

Keep relative image links in Markdown. The renderer embeds images and the SVG map into HTML so a single-file upload displays them. Other links, such as evidence reports and movies, still require their files. Inspect HTML and verify illustrations decode correctly.

Retain final MKV, canonical guide Markdown/HTML, source subtitles, approved SRT/ASS, complete ASR evidence/settings, manual decisions, ledger, illustrated assets, tool/config snapshots and verification. Hash retained support files in a manifest (exclude the manifest itself). Save `retained-media.json` with current filenames, original stream indices and added smart track index for future reruns.

Temporary PCM/crops may be removed once evidence and final media are verified. Source deletion is **off by default**. If the user authorizes deletion for this title, inventory exact paths, verify all original tracks survived, complete the full decode and guide/link checks, ensure the verified replacement is durably saved, and record cleanup before deleting originals. Never generalize one title's authorization to another. Keep failed or unverified sources.
