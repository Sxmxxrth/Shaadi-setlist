# ShaadiSetlist Dataset Guide

The dataset should be the source of truth. The model should curate, explain, and structure playlists, but the song knowledge should mostly come from maintained data.

## Current Required Fields

Each song should include:

- `song`: Song title
- `event`: Comma-separated wedding moments where this song fits
- `mood`: Comma-separated mood tags
- `genre`: Comma-separated genre or cultural style tags
- `energy`: Number from 1 to 10

## Recommended New Fields

Add these gradually as the app grows:

- `artist`: Singer, composer, or main artist
- `movie_or_album`: Source film or album
- `year`: Release year
- `language`: Hindi, Punjabi, Gujarati, Telugu, Tamil, Bengali, etc.
- `region`: Punjabi, Gujarati, Marathi, South Indian, Bengali, Rajasthani, etc.
- `era`: 90s, 2000s, 2010s, latest
- `moment`: Bride entry, groom entry, couple dance, family dance, baraat, dinner, afterparty, bidaai
- `crowd`: Family, Gen-Z, elders, mixed
- `bpm`: Approximate tempo
- `danceability`: Number from 1 to 10
- `avoid_for`: Contexts where this song is awkward or inappropriate
- `notes`: Short curator note

## Mashup Fields

For real mashup generation later, add:

- `bpm`: Approximate tempo
- `key`: Musical key, if known
- `intro_seconds`: Useful intro length
- `hook_start`: Timestamp where the strongest hook begins
- `hook_end`: Timestamp where the hook ends
- `best_transition_point`: Timestamp or section name for DJ transitions
- `drop_type`: Dhol drop, bass drop, chorus drop, vocal hook, instrumental
- `has_dhol`: true or false
- `compatible_with`: Song titles or style tags this mixes well with
- `audio_file`: Local path to the licensed/private audio file, if available

## RAG Fields

The local RAG index reads these fields when searching the dataset:

- `song`
- `event`
- `mood`
- `genre`
- `region`
- `language`
- `crowd`
- `moment`
- `notes`

Good metadata makes retrieval better. Prefer clear, searchable words like
`groom squad`, `bride entry`, `family dance`, `peak procession`, or
`classy cocktail` in `moment` and `notes`.

## Fine-tuning Later

Do not fine-tune on `dataset.json` alone. For useful fine-tuning, first collect
examples that include:

- user request
- retrieved songs
- ideal final playlist
- reasoning and transition tips
- whether the result was accepted or edited

## Tag Rules

Use consistent lowercase tags where possible:

- Events: `mehendi`, `haldi`, `sangeet`, `wedding`, `baraat`, `reception`, `bidaai`, `cocktail`, `garba`
- Moods: `high energy`, `hype`, `romantic`, `emotional`, `fun`, `classy`, `traditional`, `spiritual`
- Crowds: `family`, `gen-z`, `elders`, `mixed`

## Expansion Priority

Start with weak areas first:

1. Haldi: add 25-40 more songs
2. Garba/Gujarati: add 30-50 songs
3. Baraat: add 30-50 songs
4. Bidaai: add 20-30 songs, but keep quality high
5. Regional sets: Punjabi, Gujarati, Marathi, South Indian, Bengali

## Quality Bar

Only add a song if you can answer:

- Which event does it truly fit?
- Is the mood accurate?
- Would people actually dance, sing, or emotionally connect to it?
- Is it safe for a family wedding crowd?
- Does it add coverage, or is it a duplicate of songs already present?
