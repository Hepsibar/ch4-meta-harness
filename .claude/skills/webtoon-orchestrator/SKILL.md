---
name: webtoon-orchestrator
description: "웹툰 제작 파이프라인(기획→시나리오→캐릭터→콘티→작화→검수)을 조율한다. 사용자가 '웹툰 만들어줘', '웹툰 제작', '에피소드/화 만들기', '웹툰 기획해줘', 'N화 그려줘'라고 요청하면 사용한다. 또한 웹툰 결과 수정, 특정 화·장면·컷만 다시, 대사 수정, 캐릭터 외형 변경, 컷 재생성, 작화 다시, 업데이트, 보완, 이전 결과 개선 같은 후속 작업에도 사용한다."
---

# 웹툰 제작 오케스트레이터

## 실행 모드: 지속형 에이전트 협업(모드 B)

웹툰 제작은 창작이며, 기획·시나리오·캐릭터·콘티·작화가 서로 맞물려 반복 수정된다. 각 전문가가 이전 대화 맥락을 유지해야 "주인공 성격만 바꿔", "3화 마지막 컷만 다시"처럼 범위를 좁힌 후속 요청을 처리할 수 있다. 따라서 이름 붙인 지속형 에이전트로 조율한다. 검수자만 단발 호출한다.

v1처럼 명시적인 팀 객체를 만들지 않는다. 이름 붙여 실행한 에이전트는 자동으로 하나의 협업 그룹에 속한다. TeamCreate/TeamDelete는 쓰지 않는다.

## 에이전트 구성

| 이름 | subagent_type | 역할 | 스킬 | 산출물 |
|------|--------------|------|------|--------|
| writer | webtoon-writer | 기획·시나리오·대사 | webtoon-writing | `01_writer_bible.md`, `01_writer_scenario.md` |
| char | webtoon-character-designer | 캐릭터·스타일 토큰 | webtoon-character-design | `02_character_sheets.md`, `02_style_guide.md` |
| director | webtoon-director | 콘티·연출 | webtoon-directing | `03_director_storyboard.md` |
| artist | webtoon-art-director | 작화 프롬프트·이미지 | webtoon-art-prompting | `04_art_prompts.md`, `04_images/cut_NNN.png` |
| (검수) | webtoon-reviewer | 검수 | webtoon-review | `05_review_report.md` |

검수자는 단발 호출이라 이름을 고정하지 않는다(모드 C).

## 작업 절차

### 0단계: 기존 작업 확인(후속 요청 처리)

1. `_workspace/`가 있는지 확인한다.
   - 없으면 → 처음부터 실행(1단계로).
   - 있고 일부만 고쳐 달라는 요청(특정 화·장면·컷·대사·캐릭터)이면 → 해당 단계/에이전트만 다시 실행한다. 이전 산출물 경로를 에이전트 프롬프트에 넣어 읽고 반영하게 한다.
   - 있고 새 에피소드·새 작품을 요청하면 → 기존 `_workspace/`를 `_workspace_{타임스탬프}/`로 옮기고 새로 실행한다.
2. 후속 요청은 담당 에이전트만 깨운다. 예: "대사 수정" → writer, "머리색 변경" → char + artist(해당 컷 재생성), "컷 구도만" → director + artist.

### 1단계: 준비

1. 사용자 입력을 분석한다: 신규 작품인가/기존 작품의 N화인가, 장르·타깃·분량, 화당 목표 컷 수, 참조 자료.
2. 불명확하면(장르·타깃·분량 미정) 이 지점에서 사용자에게 간단히 확인한다. 창작 방향은 되돌리기 비싸기 때문이다.
3. `_workspace/`와 `_workspace/00_input/`을 만들고 브리프·참조 이미지를 저장한다.
4. `OPENAI_API_KEY` 설정 여부를 확인한다. 없으면 작화 단계에서 프롬프트까지만 만들고 이미지 생성은 건너뛴다고 사용자에게 미리 알린다.

### 2단계: 에이전트 실행 및 작업 등록

1. 한 메시지에서 지속형 에이전트를 병렬로 실행한다(`name` 필수, SendMessage 대상이 된다).
   - Agent(name: "writer", subagent_type: "webtoon-writer", prompt: 역할 + 브리프 경로 + 산출 경로)
   - Agent(name: "char", subagent_type: "webtoon-character-designer", ...)
   - Agent(name: "director", subagent_type: "webtoon-director", ...)
   - Agent(name: "artist", subagent_type: "webtoon-art-director", ...)
   - 각 프롬프트에 "첫 보고로 실제 사용 가능한 도구 목록을 알려라"를 넣는다(특히 artist의 Bash).
2. 공유 작업 목록을 의존 관계와 함께 등록한다. 파이프라인이므로 순서가 핵심이다.
   - TaskCreate({title: "연재 바이블/시나리오", assignee: "writer"})
   - TaskCreate({title: "캐릭터·스타일 토큰", assignee: "char", depends_on: [바이블]})
   - TaskCreate({title: "콘티", assignee: "director", depends_on: [시나리오, 캐릭터]})
   - TaskCreate({title: "작화 프롬프트·이미지", assignee: "artist", depends_on: [콘티, 토큰]})
   > writer와 char는 초반에 함께 시작하되(서사 역할 ↔ 시각 설정을 주고받음), director는 둘이 끝난 뒤 시작한다.

### 3단계: 협업 조율(파이프라인 순서)

- **기획·시나리오·캐릭터(병행):** writer가 바이블/시나리오를 쓰는 동안 char는 서사 역할을 받아 캐릭터 토큰을 만든다. 서로 충돌하면(외형↔성격) 리더가 메시지를 중계한다. 예: SendMessage({to: "char"}, "writer의 `01_writer_bible.md` 주인공 역할을 반영해 토큰을 확정하라").
- **콘티:** 시나리오·캐릭터가 동결되면 SendMessage({to: "director"}, "`01_writer_scenario.md`와 `02_character_sheets.md`로 콘티를 작성하라").
- **작화:** 콘티가 동결되면 SendMessage({to: "artist"}, "`03_director_storyboard.md`와 토큰으로 프롬프트를 만들고 이미지를 생성하라. 생성 전 --dry-run으로 검증하라").
- 에이전트가 이전 맥락을 유지하므로 "아까 그 시나리오의 S2 대사만"처럼 좁혀 지시할 수 있다. 산출물은 항상 파일로 남긴다.

### 4단계: 단계 경계 산출물 동결

다음 단계가 읽을 파일이 뒤늦은 메시지로 바뀌면, 다음 단계는 바뀌기 전 내용을 읽고 작업하게 된다. 단계를 넘길 때마다 동결한다.

1. TaskList와 완료 알림으로 해당 단계 담당자가 완료를 보고했는지 확인한다.
2. SendMessage로 동결을 알린다. 예: "시나리오를 동결한다. 이후 수정은 기존 파일을 고치지 말고 `01_writer_scenario_v2.md`로 쓴 뒤 리더에게 알려라."
3. 해시를 기록한다: `shasum _workspace/01_writer_* > _workspace/freeze_story.sha`(`sha1sum`/`md5sum`도 가능).
4. 다음 단계 에이전트 프롬프트에 산출물 경로와 해시 파일 경로를 함께 넘긴다.

경계: 시나리오+캐릭터 → 콘티, 콘티 → 작화. 각 경계에서 같은 절차를 밟는다.

### 5단계: 검수

1. artist가 이미지 생성을 마치면(또는 프롬프트까지) 검수자를 단발 호출한다.
   - Agent(subagent_type: "webtoon-reviewer", prompt: "`_workspace/`의 모든 산출물을 교차 검수해 `05_review_report.md`를 작성하라")
2. 보고서의 FIX/REDO 지적을 담당 에이전트별로 분류한다.
3. SendMessage로 각 담당(writer/char/director/artist)에게 해당 지적만 전달해 수정하게 한다. 맥락을 유지하므로 컷 번호로 좁혀 지시한다.
4. 재검수는 수정이 끝난 뒤 검수자를 한 번 더 호출한다. **수정-재검수는 최대 2회로 제한한다.** 두 번 수정해도 통과하지 못하면 미해결 상태와 원인을 사용자에게 알린다. 전체 컷의 50% 이상이 REDO이면 토큰·브리프 재검토를 사용자에게 제안한다.

### 6단계: 최종 조립 및 보고

1. 최종 산출물을 만든다: 컷 순서대로 이미지와 대사를 배치한 에피소드 문서.
   - 기본 경로 `output/{작품}_{N}화/`에 `episode.md`(컷 번호 순으로 `![](images/cut_NNN.png)` + 해당 컷 대사/내레이션)와 `images/`를 둔다. 사용자가 경로를 지정하면 그 경로에 만든다.
   - 최종 조립 직전 `shasum -c _workspace/freeze_*.sha`로 동결 산출물이 바뀌지 않았는지 확인한다. 바뀌었으면 무엇이 바뀌었는지 보고 재조립 여부를 정한다.
2. `_workspace/`는 사후 검증을 위해 남긴다.
3. 사용자에게 요약 보고: 제작한 화, 컷 수, 생성/미생성 이미지 수, 미해결 지적. 팀 해체 절차는 없다(필요하면 TaskStop).

## 데이터 전달

| 방법 | 쓰는 곳 |
|------|---------|
| 파일(`_workspace/{phase}_{agent}_{artifact}`) | 모든 산출물. 컷 번호(cut_NNN)로 콘티-프롬프트-이미지를 대응시킨다 |
| SendMessage | 리더↔에이전트 지시·피드백 중계 |
| 공유 작업 목록(TaskCreate/Update) | 파이프라인 진행·의존 관계 |

## 오류 처리

| 상황 | 대응 |
|------|------|
| 에이전트 무응답·중지 | SendMessage로 상태 확인 후 재지시. 실패하면 같은 유형을 새 이름(예: writer2)으로 실행하고 산출물 경로를 넘긴다. |
| 사용량 한도·인증 만료·권한 거부 | 다시 시도하지 않는다(남은 한도만 소모). 부분 산출물을 열어 어디까지 됐는지 확인하고 누락을 `_workspace/`에 기록해 사용자에게 보고한다. 한도면 풀리는 시각도 알린다. 리더는 직접 확인한 사실만 채우고 에이전트의 판단은 추측하지 않는다. |
| `OPENAI_API_KEY` 없음 | artist가 프롬프트까지만 완성. 이미지 미생성으로 보고하고, 키 설정 후 재생성 가능함을 알린다. |
| 특정 컷 생성 반복 실패 | 프롬프트 단순화로 1회 재시도. 그래도 실패하면 미생성으로 남기고 보고한다. |
| 산출물 충돌(외형↔성격 등) | 삭제하지 않고 두 안을 함께 적어 사용자/담당에게 판단을 맡긴다. |
| 작업 상태 지연 반영 | TaskList 확인 후 TaskUpdate로 직접 갱신한다. |

## 테스트 시나리오

### 정상 흐름
1. 사용자가 "로맨스 판타지 1화 만들어줘(60컷 목표)"를 요청한다.
2. 2단계에서 writer/char/director/artist를 실행하고 작업 4건을 의존 관계와 함께 등록한다.
3. writer·char 병행 → 동결 → director 콘티 → 동결 → artist 프롬프트·이미지 생성 → 검수 1~2회.
4. 예상 결과: `output/{작품}_1화/episode.md`와 `images/cut_001.png~`가 생성되고, 미생성 컷이 보고된다.

### 오류 흐름
1. 작화 단계에서 `OPENAI_API_KEY`가 없다.
2. artist가 `04_art_prompts.md`를 완성하고 이미지는 생성하지 않는다.
3. 리더가 "이미지 미생성(키 없음), 프롬프트는 완성. 키 설정 후 artist에게 재생성 지시 가능"을 사용자에게 보고한다.
