---
name: webtoon-character-design
description: "웹툰 캐릭터의 시각 설정과 이미지 생성용 일관성 토큰을 만드는 절차. 캐릭터 시트(외형·의상·색상·표정 레인지), 전체 아트 스타일 가이드, GPT Image 프롬프트에 그대로 붙일 고정 토큰 블록 작성을 다룬다. webtoon-character-designer 에이전트가 캐릭터 설정·스타일 가이드를 만들 때 사용한다."
---

# 웹툰 캐릭터 디자인 · 일관성 토큰

생성 AI는 같은 캐릭터도 프롬프트가 조금만 달라지면 다르게 그린다. 이를 막는 핵심 장치가 **일관성 토큰**이다. 토큰은 캐릭터마다 고정된 짧은 영문 묘사 블록으로, art-director가 모든 컷 프롬프트에 **그대로 복사**해 넣는다. 토큰이 길거나 매번 바뀌면 일관성이 깨지므로, 짧고 변하지 않게 유지한다.

## 1. 캐릭터 시트

`_workspace/02_character_sheets.md`에 캐릭터마다 쓴다.

```
## {캐릭터 이름}

- 역할: {writer의 서사 역할 요약}
- 나이대 / 체형 / 키 인상
- 얼굴: 얼굴형, 눈 모양·색, 눈썹, 코·입 인상, 특징(점·흉터·안경 등)
- 헤어: 색(HEX), 길이, 스타일
- 기본 의상: 상·하의, 신발, 색(HEX), 액세서리
- 상징색: {HEX} — 이 캐릭터를 떠올리게 하는 색
- 표정 레인지: 평소 / 기쁨 / 분노 / 불안 등 대표 표정 묘사

### 일관성 토큰 (영문, 고정)
`{character_token}`
예: "young woman, 20s, oval face, large almond dark-brown eyes, straight black bob haircut, slim build, navy trench coat over white shirt, silver stud earrings"
```

### 토큰 작성 규칙
- **영문, 쉼표로 구분, 15~30단어.** 너무 길면 모델이 일부를 무시한다.
- 변하지 않는 특징만 넣는다(얼굴·헤어·체형·시그니처 의상). 표정·포즈·카메라는 컷마다 다르므로 토큰에 넣지 않는다 — 그건 art-director가 컷별로 더한다.
- 색은 토큰 안에 색 이름으로 쓰고, HEX는 시트에 따로 적어 둔다(모델은 HEX보다 색 이름을 잘 따른다).
- 캐릭터가 의상을 바꾸는 설정이면 "기본 토큰 + 의상 변형 토큰"으로 나눠 적는다.

## 2. 스타일 가이드

`_workspace/02_style_guide.md`에 작품 전체 화풍을 쓴다. 이 토큰도 모든 컷 프롬프트 맨 앞에 붙는다.

```
## 아트 스타일 토큰 (영문, 고정)
`{style_token}`
예: "Korean webtoon style, clean cel-shaded coloring, soft gradient backgrounds, thin consistent linework, vertical scroll panel, cinematic lighting, muted warm palette"

## 세부 지침
- 선: 굵기·질감
- 채색: 셀/수채/그라데이션, 명암 강도
- 배경: 디테일 수준, 톤
- 분위기: 전체 무드
- 비율: 세로 스크롤 기준 기본 1024x1536
```

## 3. 일관성 원칙

- 토큰은 한번 확정하면 고정한다. 바꾸면 이미 생성한 컷과 어긋난다. 불가피하게 바꾸면 변경 사유·영향 범위를 시트에 적고 art-director에게 재생성을 알린다.
- 외형은 성격·역할을 드러내야 한다. 서사와 외형이 충돌하면 writer에게 조정을 요청한다.
- 참조 이미지가 주어지면 `_workspace/00_input/`에 두고, art-director가 생성 시 `--reference`로 쓸 수 있게 경로를 시트에 적는다.

## 4. 금지
- 토큰에 표정·포즈·배경·카메라를 넣지 않는다(컷마다 달라지는 요소).
- 토큰을 캐릭터마다 다른 형식으로 쓰지 않는다. 같은 구조를 유지해야 art-director가 기계적으로 조합한다.
