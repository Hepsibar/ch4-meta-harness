---
name: webtoon-art-prompting
description: "웹툰 컷의 GPT Image(OpenAI) 프롬프트를 작성하고 번들 스크립트로 이미지를 생성하는 절차. 콘티 컷 명세와 캐릭터 일관성 토큰을 정해진 순서로 조합해 프롬프트를 만들고, scripts/gen_image.py로 컷 이미지를 뽑고, 캐릭터 참조 이미지로 일관성을 높이는 방법을 다룬다. webtoon-art-director 에이전트가 작화 프롬프트 작성·이미지 생성 작업을 할 때 사용한다."
---

# 웹툰 작화 프롬프트 · GPT Image 생성

연출가의 컷 명세와 캐릭터 디자이너의 일관성 토큰을 합쳐 컷마다 이미지 프롬프트를 만들고, OpenAI GPT Image API로 실제 이미지를 생성한다. 일관성의 핵심은 **토큰을 그대로 쓰고, 프롬프트 구성 순서를 고정하는 것**이다. 순서가 흔들리면 모델이 강조점을 다르게 해석해 화풍이 컷마다 달라진다.

## 1. 프롬프트 구성 순서(고정)

컷마다 아래 순서로 조합한다. 앞쪽일수록 모델이 강하게 반영한다.

```
1. 스타일 토큰      ← 02_style_guide.md의 style_token을 그대로
2. 캐릭터 토큰      ← 등장 캐릭터의 character_token을 그대로(여러 명이면 나열)
3. 장면/동작        ← 이 컷에서 인물이 무엇을 하는가(표정·포즈)
4. 구도/카메라      ← 콘티의 샷·앵글·인물 위치
5. 배경/조명        ← 콘티의 배경·분위기
6. 포맷 지정        ← "vertical webtoon panel, no text, no speech bubbles"
7. 금지어(negative) ← 피할 요소(텍스트·워터마크·여분 인물 등)
```

**예시(cut_012):**
```
Korean webtoon style, clean cel-shaded coloring, soft gradient backgrounds, thin consistent linework, cinematic lighting, muted warm palette, young woman, 20s, oval face, large almond dark-brown eyes, straight black bob haircut, slim build, navy trench coat over white shirt, standing by a window looking back over her shoulder, anxious expression, bust shot, slight low angle, subject on left, sunset backlight through the window, vertical webtoon panel, no text, no speech bubbles, no watermark, single character
```

## 2. 핵심 원칙

- **토큰은 요약·변형하지 않고 그대로 붙인다.** character-designer가 맞춰 둔 일관성이 토큰에 들어 있다. 바꾸면 캐릭터가 달라진다. 토큰 수정이 필요하면 character-designer에게 요청한다.
- **말풍선·텍스트는 이미지에 넣지 않는다.** 대사는 조립 단계에서 얹는다. 프롬프트에 항상 `no text, no speech bubbles`를 넣는다. 생성 모델의 글자는 깨지기 때문이다.
- **표정·포즈·카메라는 컷마다 더한다.** 이건 토큰이 아니라 이 컷 고유 정보다(순서 3~5).
- **등장인물 수를 명시한다.** `single character` / `two characters`를 넣어 여분 인물 생성을 막는다.

## 3. 이미지 생성 — scripts/gen_image.py

프롬프트 로직을 매번 새로 짜지 말고 번들 스크립트를 `Bash`로 호출한다. 생성 전 반드시 `--dry-run`으로 요청을 검증한다.

```bash
# 0) 요청 검증(API 호출 없음)
python .claude/skills/webtoon-art-prompting/scripts/gen_image.py \
  --prompt-file _workspace/04_prompts/cut_012.txt \
  --out _workspace/04_images/cut_012.png --dry-run

# 1) 실제 생성 (프로젝트 루트의 .env에서 OPENAI_API_KEY를 자동으로 읽는다.
#    셸 환경 변수가 있으면 그 값이 .env보다 우선한다.)
python .claude/skills/webtoon-art-prompting/scripts/gen_image.py \
  --prompt-file _workspace/04_prompts/cut_012.txt \
  --out _workspace/04_images/cut_012.png --size 1024x1536

# 2) 캐릭터 일관성 강화 — 캐릭터 시트 이미지를 참조로
python .claude/skills/webtoon-art-prompting/scripts/gen_image.py \
  --prompt-file _workspace/04_prompts/cut_012.txt \
  --out _workspace/04_images/cut_012.png \
  --reference _workspace/00_input/char_jiwon_ref.png
```

- 기본 모델은 `gpt-image-1`이다. 계정이 다른 이미지 모델 id를 제공하면 `--model <id>` 또는 환경 변수 `WEBTOON_IMAGE_MODEL`로 지정한다.
- 세로 스크롤 기본 비율은 `1024x1536`. 가로가 필요한 컷만 `1536x1024`.
- `--reference`는 같은 캐릭터가 나오는 컷에서 외형을 고정하는 데 쓴다(캐릭터 시트 이미지나 먼저 확정한 컷을 넘긴다). 여러 번 지정할 수 있다.
- 프롬프트는 `_workspace/04_prompts/cut_NNN.txt`에 한 컷씩 저장하고, 최종 목록은 `_workspace/04_art_prompts.md`에 모은다.

## 4. 생성 절차

1. 콘티(`03_director_storyboard.md`)의 컷을 순서대로 읽는다.
2. 컷마다 위 순서로 프롬프트를 만들어 `_workspace/04_prompts/cut_NNN.txt`에 쓰고, `_workspace/04_art_prompts.md`에도 기록한다.
3. `--dry-run`으로 몇 개를 검증한다.
4. 컷마다 `gen_image.py`를 호출해 `_workspace/04_images/cut_NNN.png`를 만든다. 주요 캐릭터 컷은 `--reference`로 일관성을 높인다.
5. 생성 실패·누락 컷 목록을 리더에게 보고한다.

## 5. 오류 대응
- `OPENAI_API_KEY` 없음 → 생성을 멈추고 리더에게 보고한다. 프롬프트 파일은 키 없이도 모두 완성해 둔다.
- API 오류·사용량 한도 → 다시 시도하지 않는다. 실패 컷과 원인을 보고한다. 반복 호출은 남은 한도만 쓴다.
- 특정 컷 반복 실패 → 프롬프트를 단순화(토큰+핵심 동작만)해 한 번 더 시도하고, 그래도 실패하면 미생성으로 남기고 보고한다.

## 6. 금지
- 토큰을 바꾸거나 줄이지 않는다.
- 프롬프트에 대사·텍스트를 넣지 않는다.
- `--dry-run` 없이 대량 생성하지 않는다.
