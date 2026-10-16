# Smart subtitles for a series

Use [MOVIES.md](MOVIES.md) for all extraction, full-track and every-entry ASR, manual review, caption formatting, packaging and verification commands. Apply them to **every episode**, with the series rules below. English remains the default audio; smart English subtitles become the default subtitles. This mode does not generate replacement voices.

## Before processing

Inventory actual episode order, source files, stream layouts and hashes. Read the existing series ledger, season guide, previous-season recaps and unresolved plot threads. Do not infer order from filesystem sorting alone or reuse another episode's stream indices.

Set a separate work directory for each episode, for example:

```bash
export MEDIA_DIR='/absolute/path/Show/Season-01'
export EP=S01E01
export SOURCE='/absolute/path/Show/Season-01/episode-01.mkv'
export WORK="$MEDIA_DIR/smart-subtitles/episodes/$EP"
export OUTPUT="$MEDIA_DIR/$EP.smart-English.mkv"
mkdir -p "$WORK"
```

Then follow the movie workflow with that episode's actual audio/subtitle indices. Process GPU jobs sequentially when VRAM is limited. Preserve completion records per episode; one successful ASR job or reviewed episode does not cover the rest of a season.

## Repetition across episodes

Maintain `smart-subtitles/series-ledger.json` keyed by canonical person, place, expression or cultural reference:

- First episode in which an item occurs: at most **three introduction cards**.
- Each subsequent episode: at most **one reminder card**.
- These series caps apply to common names too, superseding the standalone movie common-name cap of one.
- Count displayed cards, not repetitions within a turn. Three is a ceiling, not a quota.
- Aliases, surnames and inflections share one identity. Record first occurrence even if no card was needed.
- A genuinely difficult later utterance may receive plain audibility text, without another definition; document the exception separately.
- Include names only when spoken. Do not caption appearances as name reminders.

See [examples/series-ledger.json](../examples/series-ledger.json) for the data shape. Update counts from actual approved captions. Before the next episode, read both the ledger and recent narrative context. Persist the ledger across seasons rather than resetting introduction counts without an explicit editorial reason.

## Agent review and season memory

For every episode the agent must read complete source subtitles, complete full-track ASR and every entry comparison, then manually author the entire smart track and review records. Online research supports contextual definitions and cast identification; save citations. Scripts must not infer plot or select captions.

Author `season-guide.md` at the season root with:

1. A spoiler-labelled season overview and concise recap to read before the next season.
2. Per-episode digest and a more detailed timestamped timeline.
3. Characters, actor identities, aliases and relationships. Separate facts shown on screen from character claims and agent inference.
4. Terminology, local knowledge and links to the persistent ledger.
5. Actual video stills at important moments, labelled with episode/time. Inspect silent actions, written messages and finale reveals.
6. A relationship mind map, authored in Graphviz DOT and rendered to SVG. Label relationships and uncertainty, rather than implying every link is romantic or factual.
7. Unresolved questions and changes to carry into new episodes/seasons.
8. ASR coverage, review provenance, uncertainties and links to verification.

Use original concise plot prose. Do not paste full dialogue or reproduce web summaries. Keep playback subtitles free of later spoilers; clearly mark guide spoilers. Preserve previous-season recaps when extending the series memory.

Render with:

```bash
.venv/bin/python tools/render_guide.py "$MEDIA_DIR/season-guide.md"
```

All guide illustrations are embedded into the HTML, including the relationship map. Keep source images and Markdown for future regeneration. Links to media and separate audit files still require those files to be present.

## Durable layout and final gate

```text
Season-01/
  S01E01.smart-English.mkv
  S01E02.smart-English.mkv
  season-guide.md
  season-guide.html
  smart-subtitles/
    index.html
    series-ledger.json
    quality-report.json
    retained-media.json
    manifest.json
    episodes/S01E01/
      source-info.json
      source.srt
      full-asr.json
      full-asr-complete.json
      entry-asr/
      entry-review.json
      authored-events.json
      smart.srt
      smart.ass
      editorial-notes.md
      delivery-config.json
      final-verification.json
    images/
    pipeline/
```

Create a season index with relative playback and evidence links. Summarize per-episode coverage and failures in the quality report. `retained-media.json` identifies current final files and original stream mappings so future checks can extract original English from final MKVs. Save tools/configs and environment versions in `pipeline/`.

Before cleanup: fully verify **each** final MKV using the movie workflow, check the complete episode inventory, original stream preservation, subtitles, guide images/links, ledger caps and manifest hashes. Keep failures explicit. Numbered learner experiment archives are not required for this compact smart-subtitle mode.

Retain all complete ASR/review evidence and final media. Delete redundant text/JSONL copies only when equivalent complete JSON is safely retained; the entry tool cannot resume from a removed JSONL journal, so future re-audits may need a fresh directory. Remove temporary PCM/crops only after validation. Delete original MKVs only with explicit title-specific authorization and a successful final gate; default is to retain them. Record exact removed paths and verified replacement hashes. Never delete another show's artifacts.

## Incoming episodes and reruns

Read this guide and ledger first. Repeat complete ASR and manual review for incoming episodes, append their digest/timeline, update canonical term state and regenerate the same HTML. On a rerun, preserve original streams and replace the existing smart track using the actual retained stream inventory. Reuse evidence only when input hashes and settings match. A new proficiency profile needs a new editorial review. Reusing approved captions reproduces choices; rerunning ASR and a new agent does not guarantee identical captions.
