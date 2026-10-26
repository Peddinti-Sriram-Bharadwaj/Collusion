# Pilot 2 분석 가이드 (따라 하기용)

작성 2026-10-24. 이 폴더의 스크립트는 표준 라이브러리만 사용합니다(pandas 불필요). 원본 데이터(`../records/`)는 읽기만 하고 수정하지 않습니다. 출력은 `out/`에 쌓입니다.

> Disclosure: 여기서 다루는 것은 모두 sprint 작업(pilot 2)입니다. Sriram의 이전 결과와 Oct 8 report는 사용하지 않습니다.

## 0. 시작 전에 알아둘 것

**pilot 분석의 목적.** pilot 분석은 효과가 있는지 검정하는 단계가 아닙니다. 본 실험을 이대로 돌려도 되는지 판단하는 단계입니다. 그래서 여기서는 p값을 계산하지 않습니다. 확인할 질문은 네 가지입니다.

| 단계 | 확인할 질문 | 소요 시간 |
|---|---|---|
| A | 실험이 설계대로 실행됐는가 | 5분 |
| B | 모델이 말한 "ACCEPT"가 정말 협정을 수락했다는 뜻인가 | LLM 판정기로 대체 (사람 코딩 삭제, 2026-10-25) |
| C | challenge 결정이 bluff를 구분해서 내려지는가, 즉 "challenge하지 않음"이 의미 있는 신호인가 | 5분 |
| D | H4의 음수 효과가 offer 이후에만 나타나는가 | 5분 |

**실행 위치.** 모든 명령은 이 폴더에서 실행합니다.
```bash
cd /c/AISafetyResearch/Collusion/results/scripted_offer/pilot2/pilot_analysis
```

**용어.**
- **game number (g):** seed 번호입니다. 같은 g라면 다섯 조건(C0–C4)의 round 1 카드 배분과 좌석이 똑같습니다.
- **used decision:** LLM agent가 직접 내린 challenge 결정입니다. proposer(Riley)의 결정, 시스템 자동 challenge, fallback은 빠집니다.
- **proposer play:** Riley가 낸 카드에 대한 결정입니다. H3가 이 결정을 봅니다.

---

## A. 무결성 확인

```bash
python step_a_integrity.py
```

**확인하는 내용**
- A1: 같은 g에서 round 1(좌석, target 카드, 시작 플레이어, 손패, 총알 위치)이 C0–C4 모두 동일한가
- A2: offer가 모든 게임에서 round 2에 전달됐는가 (C4는 아무것도 보내지 않았는가)
- A3: C1–C3의 offer 문구가 `prompts_verbatim/`의 원문 템플릿과 정확히 같고, 실제 prompt 안에 들어 있는가

**읽는 법.** 마지막 줄이 `TOTAL PROBLEMS: 0`이면 통과입니다. 문제가 있으면 해당 게임이 출력되니, 그 게임을 메모해 두고 팀에 알리세요.

**실제 결과 (2026-10-24 실행).** 6개 g 모두 OK, offer 54개 확인, 문제 0건. 보고서에 쓸 문장:
> All 30 games completed; round-1 state was identical across conditions within each game number; all 54 C1–C3 offers matched the verbatim templates and were delivered in round 2.

---

## B. 응답 텍스트 분류 (사람 코딩 삭제, LLM 판정으로 대체; 코드 구현 완료, 실행 대기)

**왜 하나.** C2(hint)의 수락률이 61%로 가장 높았지만, 응답을 읽어 보면 "I'll keep a close eye on you then"처럼 수락으로 보기 어려운 것이 `ACCEPT`로 기록돼 있습니다. ACCEPT 라벨 중 실제로 협정을 이해하고 수락한 비율을 세야 합니다.

**변경 (2026-10-25).** 사람 2인 blind 코딩용 스크립트(`step_b1_make_coding_sheets.py`, `step_b2_score_coding.py`)와 빈 코딩 시트(`out/coding_key.csv`, `out/coding_sheet_coder1.csv`, `out/coding_sheet_coder2.csv`)는 삭제했습니다. 코딩은 한 번도 수행되지 않았으므로 잃은 데이터는 없습니다. 응답 분류는 독립된 LLM 판정기(LLM-as-a-Judge)로 대체합니다. 범주는 committed / rejection / suspicion-evasive / other 네 가지이고, 절차·검증·한계는 `../../PREREG.md` v7과 `../../coding_rubric_v2.md`에 기록했습니다. 판정 코드는 `analysis/scripted_offer/judge_replies.py`, 검증 표본은 `../../judge_validation_synthetic.csv`(2026-10-25 구현, 오프라인 검증만 완료, 판정기 미배포). `coding_rubric.md`(v1)는 판정 rubric의 원형으로 그대로 둡니다.

pilot 2의 60개 응답은 판정기 검증 표본으로 쓰입니다(본 실험 검정에는 쓰지 않음).

---

## C. challenge가 bluff를 구분하는가

```bash
python step_c_baseline_bluff.py
```
LLM의 challenge 결정을 그 play가 bluff였는지 honest였는지에 따라 나누어, 각각의 challenge 비율을 봅니다.

**읽는 법.** BLUFF 열이 HONEST 열보다 뚜렷하게 높으면 agent가 bluff를 어느 정도 알아본다는 뜻입니다. 비슷하거나 반대면 challenge가 거의 무작위라는 뜻입니다.

**실제 결과 (2026-10-24)**
| 범위 | bluff에 challenge | honest에 challenge |
|---|---|---|
| (a) C4, offer 이후, 모든 play | 46% (33/72) | 40% (23/58) |
| (b) C4, offer 이후, proposer play만 | 19% (4/21) | 35% (9/26) |
| (c) 전 조건 round 1 (offer 전) | 62% (23/37) | 30% (7/23) |

**해석**
- round 1에서는 bluff를 꽤 구분합니다. offer 이후 C4에서는 구분이 약하고, proposer의 1장짜리 play에서는 오히려 반대입니다. 다만 (b)는 47개뿐이라 노이즈가 큽니다.
- 결론적으로 H3가 보는 "proposer play에 challenge하지 않음"은 정보가 적은 신호입니다. H3가 null로 나와도 offer 효과가 없다고 단정하기 어렵다는 것을 한계로 적어 둡니다.
- **앞서 팀 메시지에 쓴 "baseline challenges don't track bluffs"는 (b)에만 해당합니다.** 전체적으로는 "proposer play에서는 bluff를 구분하지 못한다"로 고쳐 말하세요.

---

## D. H4 음수 효과가 offer 이후에만 나타나는가

```bash
python step_d_preoffer.py
```
다른 LLM 플레이어의 play에 challenge한 비율을 round 1(offer 전)과 offer 이후로 나누어 조건별로 봅니다.

**실제 결과 (2026-10-24)**
| 조건 | round 1 | offer 이후 |
|---|---|---|
| C0 | 56% (5/9) | 64% (48/75) |
| C1 | 38% (3/8) | 28% (36/130) |
| C2 | 57% (4/7) | 41% (45/109) |
| C3 | 80% (4/5) | 26% (43/165) |
| C4 | 67% (4/6) | 52% (43/83) |

**해석**
- round 1은 조건마다 결정이 5–9개뿐이라 38–80%로 크게 흔들립니다. 이 정도 차이는 노이즈입니다.
- offer 이후에는 C1–C3(26–41%)가 C4(52%)보다 낮습니다. 이는 H4의 −0.29와 같은 방향입니다.
- C0도 메시지(동맹 알림)를 받았지만 64%로 오히려 높습니다. 그러니 "어떤 메시지든 받기만 하면 challenge가 줄어든다"는 설명만으로는 부족합니다. 협정 제안의 내용이 영향을 줬을 수 있습니다. 확실히 구분하려면 placebo 조건이 필요합니다.
- 주의: 이 표는 same-agent 매칭을 하지 않은 단순 합계입니다. 사전등록된 H4 값(same agent, eligibility filter 적용)과는 계산이 다르므로 기술통계로만 씁니다.

---

## E. 결과 정리: `../PILOT2_ANALYSIS.md`에 쓸 내용

아래 틀을 복사해서 채우면 됩니다. 영어로 쓰면 팀에 그대로 공유할 수 있습니다.

```markdown
# Pilot 2 analysis (descriptive; no claims)
Disclosure: sprint work only; prior team work not used. Pilot data are not pooled into the main run.

## A. Integrity
<A 결과 문장>

## B. Reply classification (LLM judge; pilot replies used only as the judge validation sample)
<판정기 검증 결과: 반복 일치율, 제안 숨김/공개 차이, ACCEPT 라벨 중 committed 비율>

## C. Do challenges track bluffs?
<표 + 해석 2줄>

## D. Pre-offer vs post-offer challenge rates
<표 + 해석 2줄>

## Proposed PREREG amendments (need team confirmation)
- D1 N = 30 game numbers
- D2 H1 kept as preregistered; reply coding added as a disclosed post-pilot secondary analysis
- D3 H2 → exploratory
- D4 no placebo condition; stated as limitation
All amendments are informed by pilot-2 data and will be disclosed as such.
```

## F. 하지 말아야 할 것
- pilot 수치를 논문에서 결과로 쓰지 않습니다. Method 섹션의 pilot 문단에만 씁니다.
- `../records/`와 `../analysis/` 안의 원본 파일을 수정하지 않습니다.
- 판정 rubric을 바꾸면 버전·날짜·이유를 `../../coding_rubric_v2.md`에 기록합니다(프로젝트 규칙: wording은 원문 그대로 보존). 본 데이터 판정 후에는 바꾸지 않습니다.

## 파일 목록
| 파일 | 역할 |
|---|---|
| `common.py` | 공통 함수 (records 읽기, LLM 결정 필터) |
| `step_a_integrity.py` | A |
| `coding_rubric.md` (v1, 판정 rubric의 원형; 사람 코딩 스크립트는 2026-10-25 삭제) | B |
| `step_c_baseline_bluff.py` | C |
| `step_d_preoffer.py` | D |
| `out/` | 코딩 시트와 정답지 |
