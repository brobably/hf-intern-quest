# Persistent Bogeumi anatomy and animation requirements

## Approved architecture change, 2026-10-12

The user explicitly approved a 2D cutout rig instead of independently generated full motion frames. Use a fixed reviewed body and costume image, rigid accessory transforms, generated limb/face components and joint rotation. This supersedes the older frame-only requirement below. Never stretch/warp the entire body or switch differently shaded whole-body art during blinking or flight. Preserve exactly two side arms/hands and two hip feet. Palette and bag pixels must remain invariant during animation.

- Exactly two arms/hands total: one attached on each side of the body. Never two hands on one side, an extra central hand, a duplicate limb, or a cream lump beneath the face.
- Exactly two feet below the body. Baby-stage sprites retain the pacifier in every pose, including blink and smile.
- A shoulder bag is worn at the side on its strap. It does not add a holding hand. Both hands remain visibly connected to their respective body sides; no hand floating at the center.
- Glasses, headsets, hats, and roof outlines remain complete and rigid. Accessories must be worn naturally and follow the generated body pose.
- Generate actual intermediate motion images. Do not use warped bitmaps or fading overlapping full-body images as substitutes.
- Inspect every generated atlas, especially bag rows and combined bag + eyewear + headwear. Check all stages and palettes in the browser before deployment.
- Repair defective source poses and keep them in the intended sequence; do not silently skip or alias defective poses to another pose.
- Treat a repeated defect as a source-art or renderer regression and review both. Keep these requirements for later tasks.

- Latest user wording: remove the original arms/hands first, then redraw one arm and one hand connected at each side. Both arms must remain visible in every pose; do not hide one entirely behind a bag. Never add a bag-grabbing hand.
- Body proportion rule: two legs emerge below their respective hips, spaced around 30% and 70% of torso width. Never place both legs in the torso center. Side bag stays outside the leg/hand silhouette and must not obscure either limb. Check perceived anatomy as well as limb count.

## Accessory perspective during movement

Generate the body and worn accessories together for each motion. Headwear follows the roof angle, glasses follow the face perspective without bending, and a shoulder bag and strap follow the torso rotation. Never animate a detached accessory layer independently of the wearer. Room furniture stays anchored in the room; character flight must not rotate stationary furniture. Use small pose-specific sheets when a large sheet loses outfit consistency. Inspect exactly two side hands and two hip feet in every accepted pose.
