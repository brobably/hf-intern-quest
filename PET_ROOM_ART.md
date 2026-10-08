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
