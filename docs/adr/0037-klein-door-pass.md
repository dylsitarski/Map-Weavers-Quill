# ADR-0037: A separate, zoomed door pass for FLUX.2 klein rooms

Status: Implemented; GPU trial pending. Changes how doors reach the model in the klein
`sketch` strategy (ADR-0032, ADR-0033, ADR-0036). SDXL, the `plan` strategy and the mock
provider are unchanged.

## Context

Owner trial of ADR-0036 (2026-10-08): the reference-free repaint fixed placeholder floors
(the storeroom became dark wood) and walls held, but doors remained the weak point. Across
the trials, doors drawn as brown bands in the room sketch were kept as flat strips,
repainted away (the bedroom's door vanished in pass 2), never turned into a door (the
storeroom's diagonal door), or invented elsewhere (an extra door on the storeroom's top
wall). In the 1024-pixel room image a 3-ft door is about 77 × 13 pixels, and nothing ties
"draw a door" to that spot except a coloured band the model may copy, ignore or paint over.
The owner asked for a direct, non-visible way to say where doors go.

## Decision

- **Room passes draw solid walls.** With the door pass on (default), the sketch draws
  doorways as wall (`room_sketch(..., doors=False)`), and both room prompts ask for solid
  walls with no doors or openings (`flux2-klein-room-sketch-walls-v1`,
  `flux2-klein-room-repaint-walls-v1`).
- **Then one door edit per door.** For each visible door of the room (not secret, not a
  window, any state), Quill computes its strip from geometry: the opening along its wall,
  across the wall band plus 4 working pixels each side (`door_strips`). It crops a 256-pixel
  square of the finished working image around the strip (512 for doors longer than
  192 pixels), upscales it to 512 × 512, paints a brown placeholder on the strip, and sends
  a masked edit (`quill.door`): the strip mask, grown 8 pixels, pins everything else; the
  placeholder is re-noised to the last 6 of an 8-step klein schedule (sigma ≈ 0.97) and
  repainted with no reference image, so there is nothing to copy. The mask is the
  "selection" and the placeholder the hint; the prompt (`flux2-klein-door-v1`) only says
  what a closed wooden door set in a wall looks like from above. The result is scaled back
  and pasted into the working image inside the strip only, before the usual exact clipping
  to the room. Each door uses seed `room seed + 1 + index`.
- All doors are drawn closed for now (open, closed and locked alike), as the owner chose
  after the open-door symbol failed. Secret doors stay plain wall.
- `MWQ_IMAGE_COMFY_FLUX2_DOOR_PASS=0` restores door bands in the sketch and door wording in
  the prompts. Workflow `comfy-flux2-klein-door-v1`; generation records add `doorPass`
  (template, prompt, crop and seed per door, door workflow details). The room's own
  `comfyui` provenance and unclipped pass images are recorded before the door edits.
- The provider hook `_uploads` now receives the request, so a family can upload
  differently per request kind.

## Consequences

- Door position and size are exact by construction; only the door's look is generated.
- Each door adds one ComfyUI job at 512 × 512 with 6 steps: estimated 1–2 seconds plus
  overhead, not measured. A room with three doors may approach the 30-second soft limit.
- A door between two rooms is painted twice, once with each room, each clipped to its own
  side of the wall.
- The door may not match the wall perfectly, and the model may still draw something other
  than a door in the strip; the placeholder colour biases it toward wood.
- Open doors (a leaf swung into the room) are not drawn yet.

## Verification

`tests/test_layout_guidance.py`: door-free sketches and strip geometry (length along the
wall, wall thickness plus padding across it, centred on the opening, secret doors
excluded). `tests/test_flux2.py`: the door graph (no reference latent, masked latent from
the placeholder, 8-step schedule split at step 2), offline refusal of malformed door
requests, configuration parsing, the solid-wall and door prompts, and the queued room job:
solid-wall templates, a door upload with the placeholder under the inverted-alpha strip,
`doorPass` provenance, and the door's colour appearing exactly at the door's wall position
in the saved room layer and nowhere nearby.
