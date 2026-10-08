# 보금이 방 디자인, 2026-10-08

Built-in image generation produced three new project assets. Existing character and wearable art is unchanged.

- `dist/bogeumi-room-v2.png`: cream plaster/clay wall, rounded arched window, warm oak floor, upper-left daylight; empty center for the pet.
- `dist/bogeumi-furniture-v2.png`: 15 transparent furniture/decor sprites with one consistent rounded matte clay style and light direction. Connected-component bounds fit each entire object without modifying image pixels.
- `dist/bogeumi-rugs-v2.png`: three transparent braided wool rugs, sky blue / milk pink / sage mint.

Prompt specifications: straight-on orthographic cozy dollhouse room with cream/ivory/pale blue/warm oak colors, softly rounded handmade clay textures, wall occupying about 60%, floor about 40%, no UI/text/character; furniture atlas in 5 columns × 3 rows ordered plant/bookshelf/floor lamp/sofa/bear clock, tulips/cat plush/star garland/desk/cushion, piggy bank/watering can/teacup/house painting/basket, all separated and fully visible with transparent gutters; rugs in three equal cells, shallow oval 3:1 front elevated perspective, same soft materials and upper-left lighting.

Furniture uses realistic relative scale: sofa and desk larger than small floor decorations, lamp taller than a plant, clock small on wall, vase/cup in front of the desk when equipped. Matte furniture colors, floor shadows, wall decor, floor texture and rug fibers share the same room palette. Existing purchases, equipment and room color choices remain available.

Validation: JavaScript syntax; browser visual QA for current equipment, all 15 furniture items, 280/530/850px rooms, mint/pink/night themes; 320 existing idle/smile silhouettes still fit. No production user preferences were changed during verification.


## Baby stage and toy-room revision

References: [Tamagotchi growth](https://tamagotchi-official.com/gb/series/paradise/howto/), [Pocket Love](https://hyperbeard.com/game/pocketlove/). References informed distinct growth silhouettes and a coherent furnished home; no characters or copyrighted art were copied.

Built-in imagegen outputs copied into the project:
- `dist/bogeumi-baby-idle.png`: 40 complete infant outfit combinations, diaper and peach/ivory pacifier integrated into every character.
- `dist/bogeumi-baby-smile.png`: corresponding 40 complete happy expressions.
- `dist/bogeumi-room-v3.png`: rounded matte clay room, simplified blond wood floor, diffuse lighting and a blank right wall for equipped decorations.

Prompt set: edit the existing 5-column/8-row atlas into a visibly newborn cream house mascot with tiny arms/feet, chubby cheeks, peach/ivory pacifier and diaper, preserve the headwear/bodywear/glasses ordering and transparent gutters; edit only eyes/cheeks into happy crescents for the paired smiling atlas; generate a front-view 5:4 matte clay room with ivory wall upper60%, blond wood floor lower40%, rounded arch window on the left, diffuse upper-left light, no character/furniture/rug/UI; remove the unused fixed wall frame while preserving the room architecture.

Character edge compositing now rejects cyan contamination outside silhouettes and slightly contracts alpha; it is independent of roof color recoloring. This avoids erasing green hats and supports all four stages and five palettes. A keyboard-visible focus outline is retained. Sofa is 53% room width behind the character; other furniture uses back-wall, tabletop and front-floor depth. Baby room sprite width30%; toddler36%; intern39%; adult42%. Stage2 label is now 꼬마 보금이. Growth thresholds and saved ownership are unchanged.

Validation: 320 idle/smile silhouettes inside fitted bounds; four stages/five palettes including beret+bag; all15 furniture and280/530/850px layouts, smiles, console logs; JavaScript syntax. Test views do not alter production pet state.

## Unified room/furniture revision (v4)

Built-in imagegen mode; generated source pixels retained unchanged. Final asset paths:
- dist/bogeumi-furniture-v4.png
- dist/bogeumi-room-v4.png
- dist/bogeumi-rugs-v4.png

Prompt set: regenerate15 objects in5x3 order plant/books/lamp/sofa/clock, flowers/cat/stars/desk/pillow, piggy/watering/tea/painting/basket. Smooth rounded molded clay toy material matching Bogeumi, front orthographic camera with a slight elevated view, diffuse upper-left light, cream/oak/sage/dusty blue/blush palette, no real fabric/wood grain, transparent gutters and complete separated silhouettes. Generate an empty5:4 ivory toy room with arch window left, wall60%/floor40%, broad plain blond planks and no furniture. Generate3 transparent shallow oval smooth blue/pink/mint rugs without braided fibers. Discarded first edit attempt retained only at generation source, not used in app.

Audit and corrections:
- plant: round vinyl-like leaves, side-floor anchor ahead of lamp.
- bookshelf: smooth toy books, back-right wall/floor anchor.
- lamp: rectangular alpha viewport preserves tall silhouette,19%room width, about33%room height; previously square viewport made actual shade/stem miniature.
- sofa: smooth blue material,56%width, behind pet, no realistic fabric weave.
- clock: clean round toy bear, wall above sofa.
- flowers: rounded simplified tulips; on tabletop when desk equipped, left-floor vase otherwise.
- cat: smooth cream plush, left foreground.
- stars: molded toy star mobile, high wall, outside clock.
- desk: low rounded table in right foreground; vase/cup bases share its surface.
- pillow: smooth blush toy cushion, right floor.
- piggy: small round blush toy, left-front floor.
- watering can: smooth sage flower can, closer left floor and away from room label/central rug.
- tea: ivory/blue clay cup, on table when present, floor tray otherwise.
- painting: same beige molded frame/picture style, right wall.
- basket: smooth simplified weave/blanket, larger right-side floor anchor with bottom breathing room.
- rugs: smooth low-relief ovals, consistent scale/light/material.

Rendering reads connected alpha bounds without pixel editing. Every furniture span has its own rectangular aspect ratio; atlas background axes are fitted independently, so narrow/tall objects remain proportional. CSS adds small shared contact shadows; wall, floor and table items receive appropriate depth/contact treatment. The same art and rectangular bounds are reused in shop/inventory. Character, purchases, rewards and equipment data unchanged.

Validation: all15 item previews visually checked (including corrected wide sofa/table ratio), full15-item arrangement and280/530/850px room sizes,320 character silhouette bounds preserved. Garland moved fully inside room after boundary check. Lamp scale/floor contact and front-floor spacing verified. No production care/purchase/equipment actions made.
# Coordinated room palettes (2026-10-08)

Four free saved themes: Sky Cream (#9ebbd1), Mint Garden (#91b9aa), Rose Milk (#c995a5), Lavender Dream (#a59ac4). Character color remains independently selectable. Existing furniture ownership and placement are preserved; the theme coordinates its artwork automatically.

Generated files: `dist/bogeumi-theme-{sky,mint,rose,lavender}-furniture.png`, `dist/bogeumi-theme-{mint,rose,lavender}-room.png`, `dist/bogeumi-theme-rugs.png`. Sky uses the existing warm cream room and blue rug. Every furniture sheet contains the same 15 objects in five columns and three rows. Alpha bounds and sprite aspect ratios are measured per generated variant; no recoloring filter is applied.

Prompt set: edit the existing room/furniture reference, preserve the exact camera, composition, object silhouettes and soft clay mascot style, recolor every item into the theme accent plus warm ivory and pale neutral wood, remove competing rainbow accents, use muted sage only for plants, preserve transparent background for furniture. Room variants retain the arched window and wall/floor proportions. Rug sheet has three isolated oval rugs, mint/rose/lavender, matching the furniture fabric, transparent background.


## Furniture scale and placement (2026-10-08)

Placement mode: pointer drag/touch, accessible furniture selector and arrow keys, save/cancel/default reset. Account-scoped server storage retains positions through unequip and re-equip. Wall ornaments stay on the wall; floor props remain within the floor band. Object aspect ratios remain unchanged.

Scale hierarchy: sofa 56% room width; standing lamp 23%; bookshelf 20%; low table 30%; small watering can 7.5%; piggy bank 5.5%; teacup 5%. Shop/inventory previews use corresponding relative sizes rather than giving every object the same height. Real furniture proportions informed the stylized scale: [IKEA two-seat sofa guide, widths 164–180 cm](https://www.ikea.com/kr/ko/files/pdf/28/e3/28e34c3c/landskrona_buying_guide_a4.pdf). Gameplay room uses readable, approximate proportions rather than architectural measurements.


## Natural motion — 2026-10-08
Generated eight transparent original PNG atlases: `dist/bogeumi-blink-half-{0..3}.png` and `dist/bogeumi-blink-closed-{0..3}.png`. Each contains the existing 40 accessory combinations. All five colors reuse the same whole-character frames through the existing color filters. Pixels are preserved; CSS crop bounds align center, height and feet to the idle frame.

Closed-frame prompt: Preserve the exact 5-column by 8-row atlas, canvas, placement, silhouette, accessories, lighting, mouth and baby pacifier. Change only both eyes of every character to gently fully closed natural resting eyelids, including eyes behind glasses. Transparent background, no crop, text or new objects.

Half-frame prompt: Preserve the exact atlas and every accessory, mouth and pacifier. Change only every pair of eyes to half closed, upper flesh-colored eyelid lowered halfway over the pupil, including glasses rows. Preserve transparency and frame ordering.

Blink playback: half 55 ms, closed 90 ms, half 55 ms, idle; random 4–8.5 second intervals after image decoding. Interrupted by petting, room activities, furniture editing or hidden document. Reduced-motion preference skips blink and body movement. Breathing is a small 4.6 second pulse, with subtle directional lean during 18 second room wandering. Movement phase survives page rerender; petting reacts immediately and settles gently.

Validation: JavaScript syntax passed. Browser QA displayed all four stages in all five colors with combined headset, scarf and glasses, verified half/closed frames and body motion names; no browser console errors.


## Single-texture motion correction — 2026-10-08
Replaced whole-image expression swaps with a WebGL mesh using the original idle atlas. Generated expression sheets are no longer used in the room. `dist/pet-motion.js` clips one original outfit texture and deforms only measured eye/mouth/hand/foot regions. `dist/pet-rig.json` stores 160 outfit-specific eye and mouth anchors derived from original pixels. No new image generation or color grading was used for this correction.

Eyes close continuously in 225 ms; the same source pixels and palette filter remain throughout. The mouth rests partly closed, smoothly opens during petting, and the baby retains its pacifier with gentle sucking motion. Hands move subtly, feet alternate according to actual room travel speed; petting relaxes eyes and lifts hands. Sleep closes eyes. The renderer pauses when hidden, runs at 30 fps, honors reduced motion, cleans up old GPU resources after rerenders and retains the original static character if WebGL is unavailable.

Validation: syntax checks passed; browser rendered all 20 stage/color pairs with combined accessories without errors. Blink, happy response and movement uniforms were inspected in the local fixture.


## Generated whole-outfit motion — 2026-10-08

Supersedes the mesh and repainted eye approaches above. Built-in Imagegen produced 24 transparent PNG atlases: `dist/bogeumi-pose-{idle,half,blink,walkA,walkB,happy}-{0,1,2,3}.png`. Each contains 40 full accessory combinations, for 960 painted poses. All five character colors reuse these exact frames with the existing consistent color filters; equipment is drawn together with the body, never attached as a separate moving overlay. Generated alpha and pixels are preserved unchanged.

Prompt set: edit the matching original stage atlas, preserve all 40 costumes, order, canvas, blue roof, cream skin, clay material and lighting. Idle: open eyes and small closed relaxed mouth, baby preserves pacifier. Half/blink: half lowered eyelids or two relaxed closed eyelid lines, round glasses remain round and all body/accessories unchanged. WalkA/B: opposite actual stepping feet and hands; bag strap stays on shoulder, scarf and keychain follow the step, headwear and glasses stay fixed. Happy: curved smiling eyes, small delighted smile and hands lifted toward cheeks, pacifier retained. No distortions, new accessories, text or background.

`dist/pet-poses.json` aligns the same window landmark at fixed canvas scale across every pose. `dist/pet-motion.js` preloads all six stage atlases and plays idle, half/closed/half blink, alternating opposite footsteps during room travel, and happy reaction on petting. No mesh, eye painting, breathing scale or accessory warp remains. Room movement phase and all gameplay/equipment state are preserved. Reduced-motion users receive static idle plus explicit interaction reactions.


## Generated motion revision, 2026-10-08

The flight player displays a single opaque whole-costume bitmap at a time. Removed the expression crossfade that ghosted eyes and duplicated limbs. No mesh deformation, face overlays or stretching is used. Positional room travel remains continuous; actual hand, foot, mouth and directional pose changes come from generated images.

Built-in Imagegen edit mode; transparent originals copied without pixel modifications to `dist/bogeumi-motion-v3-{pose}-{stage}.png`. Eleven poses for four growth stages, each with the same 40 head/body/glasses combinations. The five existing palettes apply identically to every whole-costume frame.

Prompt set: `PET_MOTION_PROMPTS.json`. Canonical neutral poses preserve the complete roof, chimney, materials, colors, costume ordering and rigid eyewear. Flight poses 0–7 make small progressive hand/foot/mouth changes and turns toward each travel direction. Half/closed eyelids and happy petting expressions are drawn into the complete character. Baby retains its pacifier. Every prompt explicitly requires exactly two hands and two feet, repositioning original hands rather than adding new ones. The first baby flight draft with duplicated hands was discarded.

Analytical alpha-component bounds and the painted window landmark align frames without modifying generated pixels. Bounds checks protect full roofs and prevent neighboring atlas cells appearing in the character frame. QA covers both directional cycles, crisp blinking, petting, costume changes, four stages and five colors.

Baby anatomy repair: the original right/left peak flying poses were regenerated with a normal torso reference. The extra central under-chin sphere was removed; two original side hands and two feet remain. Both repaired peak poses are retained in playback. No motion frames are skipped or replaced with another pose.
