# ADR-0033: Fixed-scale room window, room-first prompts and floor-plan door symbols

Status: Implemented; first trial done (2026-10-08, below). Changes the room working transform of ADR-0028
(for both ComfyUI families), the klein sketch and prompts of ADR-0032, and the style
inheritance of ADR-0021/ADR-0022 (Environment is no longer used).

Update 2026-10-08: after the first trial, the sketch draws every non-secret door closed
(a brown band of wall thickness filling the opening; `room-sketch-v3`), and the klein
prompt no longer lists doors (`flux2-klein-room-sketch-v3`, `flux2-klein-room-plan-v4`).
Items 2 and 3 below are superseded on those points.

Update 2026-10-08: klein rooms add a second, description-only pass (ADR-0034). Rooms under
10 ft now get a smaller window, at least 20 ft (ADR-0034).

## Context

The owner's second klein trial (2026-10-06, `sketch` reference, debugging bundle of the
test cottage map) showed:

- **Scale varied per room.** The working transform padded each room's own crop to a
  square and resized it to 1024 px, so a 10-ft room was drawn at about 64 px/ft and the
  36-ft main room at about 26 px/ft. Small rooms got miniature furniture (three small
  beds in one bedroom) and thick sketch walls, because walls were drawn at map raster
  size and then enlarged 8×.
- **Edge smear.** Non-square crops were padded by repeating edge pixels, producing
  streaks the model treated as content.
- **Doors** were not always honoured: gaps and brown bars are not standard plan symbols,
  and the prompt never said where the doors were.
- **Prompts.** The klein prompt began with a long instruction and put the room
  description after it; the off-white sketch floor was read as the floor colour unless
  the owner described the floor; "in the same art style as the surrounding map" pulled
  every room toward the same look (a cluttered storeroom and a whimsical bedroom both
  came out alike). The map's Environment ("Mystical fantasy forest") was inherited into
  every room prompt, including interiors.
- **Seeds**: 28 of 37 generations used seed 0, the panel default.
- **Backgrounds** had no physical scale (the cottage was drawn in perspective and
  oversized), and the background prompt asked for "readable floor surfaces".
- **History**: every accepted generation stayed in the project even after its artwork was
  replaced, so regenerating rooms walks toward the 128-record save limit.

The owner considers the dark wall tops desirable (a top-down cross-section cue) provided
they are small and consistently sized.

## Decision

1. **Fixed physical working window** (`room-window-v1`, `RoomWindow` in
   `sdxl_authoring.py`). Rooms are edited in a square window of 8 grid cells (40 ft on
   the 5-ft grid; 320 px at 960 × 640) centred on the room and clamped inside the map,
   holding real map context, resized to 1024 × 1024. Every room therefore has the same
   working scale (25.6 px/ft, 128 px per grid square). A room wider than the window
   minus its 20-unit margins grows the window to fit (smaller working scale, reported in
   the prompt). Only a window larger than the map's short side extends past the map;
   that padding repeats edge colours and is outside the mask, so it is protected. The
   generation's `crop` parameter is now the window's part of the map, and
   `roomTransform` records the window. Applies to SDXL and klein; mock is unchanged.
2. **Sketch drawn in working space** (klein, `room-sketch-v2`). The sketch sent to the
   model is drawn directly at 1024 × 1024 from native geometry, so wall bands have the
   project's wall thickness at the fixed scale (5 units = 0.5 ft ≈ 13 px, about half of
   it inside the room). A map-size copy is stored as the generation's guide input for
   provenance. Doors use floor-plan symbols: a closed or locked door is a brown leaf
   across its opening; an open door is a leaf swung 90° into the room from its hinge
   with a thin quarter-circle swing arc; secret doors and windows remain wall.
3. **Room-first klein prompts** (`flux2-klein-room-sketch-v2`, `flux2-klein-room-plan-v3`):
   the user's description unchanged; a default floor line ("a textured floor material
   that suits this room … never a plain off-white surface") when the description does
   not mention a floor; a door list derived from geometry ("Doors: a closed door in the
   right wall; an open door swung into the room in the top wall."; sides are image
   sides, top = +y); render style and palette; then the shortened edit instruction,
   which asks to match the map's rendering technique, lighting and level of detail but
   give the room its own furnishings, materials and colours; then scale. The scale
   sentence states the window size and pixels per grid square. The SDXL wall-line
   sentence is no longer sent to klein. SDXL room prompts keep their structure
   (`sdxl-room-layout-v2`, the new scale sentence).
4. **Environment is no longer used.** `MapStyle.environment` and a room's `environment`
   override stay valid in saved projects (no schema change, so existing maps still open)
   but are never sent to a provider and are not shown as fields. The map panel shows an
   old value with a button to clear it. Setting belongs in the background and room
   prompts. Room style inheritance covers render style and palette only.
5. **Backgrounds** (`sdxl-overhead-v3`): the prompt states the fixed map's physical size
   and pixels per 5-ft square, and drops "readable floor surfaces". Room prompts keep it.
6. **Random seeds by default.** Each generation uses a new random seed unless **Lock
   seed** is checked; typing a seed locks it. The preview still shows its seed, and
   recovery reuses the recovered job's seed.
7. **Generation history is pruned on accept.** Accepting artwork keeps only generation
   records whose output is still shown by an artwork layer; records for replaced or
   removed artwork are dropped. Undo restores the earlier scene with its records. The
   128-record limit now counts only shown records.

## Consequences

- Scale is consistent for rooms up to about 36 ft across. Larger rooms still fit but at
  a smaller scale; the prompt states it. The context is upscaled 3.2× (previously up to
  8× for small rooms), so it is softer than the final 8 px/ft art, which is unchanged.
- Small rooms occupy a smaller part of the 1024 image (a 10-ft room is 256 px wide);
  more of the image is protected context. Generation time is unchanged (same 1024 size).
- Records pruned from history are gone once saved; debugging bundles show the
  generations behind the current artwork.
- Old generation records keep their old `roomTransform` metadata; nothing reads it back.
- Whether klein follows floor-plan door symbols, keeps wall tops thin, and produces
  distinct room styles are trial questions.

## Verification

Offline tests: fixed window size and clamping for rooms anywhere on the map, exact
return to the raster crop, growth for large rooms and protected padding only past the
map (`test_sdxl_authoring.py`); equal working scale across rooms, sketch wall width at
the fixed scale, closed-leaf and open-leaf door symbols, door list sides and states
(`test_layout_guidance.py`); room-first klein prompt with floor default, door list and
style labels, and the queued klein room job (`test_flux2.py`); the SDXL editor flow with
the window (`test_comfy_editor.py`); Environment ignored for rooms and backgrounds
(`test_room_images.py`, `test_backgrounds.py`); background scale text; record pruning
(`artwork-layers.test.ts`); random and locked seeds and the removed Environment field
(browser tests).

First owner trial (2026-10-08, klein distilled, cottage map): furniture scale matched
better across rooms and wall tops were thin and even; about 12 seconds per room. But the
open-door symbol was rendered badly and partly left in the image; door-like objects were
drawn lying on the floor, most likely prompted by the written door list; floors drifted
toward the off-white placeholder even when described; furniture stayed along the walls
with an empty centre; and distinctive room descriptions (cluttered, whimsical) still did
not show. Response: doors are drawn closed and the door list is removed (update above).
Floors, empty centres and weak room character remain open.
