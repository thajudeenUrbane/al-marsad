# Blender renders

Blender here is a build-time asset factory, not a source and not part of the site. A script reads
the files the site itself draws from (`expeditions/dist/data/badr.json` and `stars.json`) and
renders images from them. The data stays the source of truth; nothing in Blender is edited by hand,
and nothing on the site needs Blender to run.

The pilot is the Badr expedition.

## What it makes

`blender/out/` holds:

| File | What it is |
|---|---|
| `badr-eve.jpg` | 1920x1080 exhibition still: the valley of Badr at 21:39 local solar time on the eve of the tabular candidate day, under the Moon and stars as computed, with the moonlight's shadows. Labels and a provenance stamp are drawn in. |
| `badr-relief.png` | 960x960 grey relief of the same ground, north up, lit from the north-west. A texture for later use; the site does not use it yet. It has no stamp, so its provenance is in the manifest. |
| `badr.manifest.json` | The inputs fingerprint, the Blender version, the frame drawn, each file's sha256 and what each provenance class covers in it, and the credits. |

## No pixel without provenance

The stamp on the still names every class in the colours the site uses:

- **attested**: the date the text gives, quoted (Ibn Hishām), with its page marked provisional. The
  still draws the tabular candidate day and says so; it does not correct the text.
- **computed**: the Moon, the stars, the moonlight and shadows (astronomy-engine, HYG v4.1); the
  ground from present-day elevation, heights 2.5 times; the directions to Madinah and Makkah.
- **located**: Badr, a proposed gazetteer point (al-Thurayya).
- **schematic**: the labels, the stamp, and the Moon drawn 2 times its size.

No people are shown: no figures, tents or wells, only the ground, the sky and labels. The still
follows the site's 3D view (`expeditions/app/world.js`): the same units, eye, ground colours, fog
and star sizes. Only the look direction differs, so the Moon is in frame.

## Making the renders

On a Mac with Blender 5.2, from the repository root:

```bash
/Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python-exit-code 1 -P blender/badr_eve.py
```

It takes about two minutes and writes the three files above; commit them together. Add
`-- --preview DIR` to write half-size test renders to `DIR`, with no manifest.

The image metadata carries the stamp note (the title and the inputs fingerprint) and, in the
relief, Cycles' sample count and render times. Blender's other stamp fields, which would leave a
file path or host name in the file, are turned off.

## Staying current

`blender/inputs.py` fingerprints the parts of the data a render draws (the ground, the gazetteer
points, the computed sky, the stars) and the render scripts. `blender/check_fresh.py` is plain
Python, with no Blender, and runs in `scripts/check_all.sh`, so CI does too. It fails when:

- the data a render draws has changed;
- a render script has changed; or
- an output is not the file the render wrote.

It then prints the command to re-render. A change to a claim the images do not show leaves them
fresh.
