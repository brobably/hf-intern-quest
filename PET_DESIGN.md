# 보금이 키우기 — 초기 버전

HF의 주거행복 방향에서 착안한 인턴 홈페이지 오리지널 캐릭터. 공식 공사 마스코트가 아니다.

- 새싹집(0), 아기 보금이(32), 인턴 보금이(96), 든든한 보금이(192)의 네 단계.
- 밥 먹기, 쉬기, 방 청소, 함께 공부 각각 하루 1회 성장 8·코인 5. 반복 돌보기는 상태만 회복한다. 서버에서 날짜와 보상 검증.
- 첫날 2단계, 꾸준히 돌보면 3일째 3단계, 6일째 4단계. 성장과 코인은 활동 XP와 분리.
- 계정별 서버 저장. 상태는 시간에 따라 완만히 감소하며 최저 25. 죽음·퇴화·유료 결제 없음.
- 화분 12코인, 책장 18코인, 조명 24코인. 한 번 구매 후 자유롭게 배치/보관.
- 방은 반응형 HTML/CSS, 캐릭터는 투명 PNG 2x2 스프라이트. 움직임 줄이기 설정 지원.

## 자료
https://www.hf.go.kr/ko/sub05/sub05_02_03_01.do
https://tamagotchi-official.com/manual/toy/uni/manual_03/Uni_WEB_IS_EN.pdf

## 이미지
Built-in image_gen 사용. dist/bogeumi-stages.png에 원본 알파를 유지해 저장.
Prompt: Original exceptionally cute house-shaped intern companion, blue roof, cream body, blush cheeks, soft clay 3D toy style, four growth stages in equal 2x2 transparent atlas: smiling seed house, baby house, intern with blank ID lanyard and notebook, reliable mature house with blue cardigan and golden house key. One centered full-body sprite per quadrant with padding. No text, official logo, watermark, or room background.


## Natural outfits revision
Mode: built-in image generation, reference-based new sprite atlas.
Asset: dist/bogeumi-outfits.png. 4 columns = growth stages, 4 rows = glasses / ribbon / headphones / scarf. Each cell contains the complete clothed character; no SVG or emoji overlay.
Prompt: Create a transparent 4x4 game sprite atlas of the original cream house mascot with blue roof in matching soft 3D clay style. Columns show baby, toddler, intern with blank ID and notebook, grown house with cardigan and house key. Rows show fitted round navy glasses, soft pink bow physically attached to roof, compact padded headphones wrapped over roof, knitted peach scarf wrapped around neck. Coherent light, volumetric materials and contact shadows; no text or borders. Preserve recognizable original character.
Mouse interaction: click or drag over the character to stroke it. Happiness +3, 10-second server cooldown, no coins or growth awarded.
