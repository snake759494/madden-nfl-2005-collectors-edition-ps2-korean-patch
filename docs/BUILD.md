# 재빌드 방법

필요한 것: Python 3.10+ (numpy, Pillow, unicorn), xdelta3. 개발용 디스어셈블러 `tools/mdis.py`는 capstone을 씁니다.

## 준비

도구는 저장소를 `work`라는 폴더로 두고, 그 상위 폴더에 원본 ISO와 글꼴이 있다고 가정합니다.

```
<작업 폴더>/
  Madden NFL 2005 (USA) (Collector's Edition).iso   해시가 README 표와 일치하는 원본
  NanumSquareNeo-cBd.ttf, NanumSquareNeo-dEb.ttf   나눔스퀘어 네오
  work/                                           이 저장소
    fonts/Galmuri11-Bold.ttf                      갈무리11 Bold
    tools/ translation/ ...
```

글꼴 파일은 저장소에 없으므로 따로 받으세요(`docs/FONT_CREDITS.md`).

## 빌드

```
python work/tools/build.py
```

결과:
- `Madden NFL 2005 (USA) (Collector's Edition) (Korean).iso`
- `SLUS-21025_<한글판 CRC>.pnach`, `SLUS-21025_93CFD46C.pnach` (와이드 패치)
- `work/missing.txt`: 번역이 없는 화면 문자열 목록

xdelta는 다음 옵션으로 만듭니다(압축·2차 압축·경로 헤더 없음).

```
xdelta3 -e -0 -S none -A -s "Madden NFL 2005 (USA) (Collector's Edition).iso" "Madden NFL 2005 (USA) (Collector's Edition) (Korean).iso" Madden_NFL_2005_CE_PS2_KO_v1.0.xdelta
```

환경 변수:
- `MAXH`: 메뉴용 한글 글자 최대 높이(기본 11). 늘리면 경기 중 화면이나 타이틀 화면 글자가 사라질 수 있습니다.
- `OUT`: 결과 ISO 경로
- `ONLY`: 쉼표로 구분한 파일 이름 일부. 해당 파일만 고친 시험용 ISO를 만듭니다. 한글을 보려면 `SLUS`와 `UIS_FONT,FONTS`를 함께 넣어야 합니다.

## 번역 수정

`translation/*.tsv`는 한 줄에 `영문<TAB>한글`입니다. `#`으로 시작하는 줄은 주석이고, `\n`·`\t`는 줄바꿈·탭입니다.

| 파일 | 내용 |
| --- | --- |
| `ui_*.tsv` | UIS 화면 문자열(메뉴, 도움말, 경기 HUD 라벨) |
| `elf_*.tsv` | 실행파일 문자열. `elf_08_online.tsv`는 온라인 모듈(`tools/gen_online_tsv.py`로 생성) |
| `elf_99_short.tsv` | 자리가 모자랄 때 쓰는 짧은 번역 |
| `apt_*.tsv` | 온라인 플래시 메뉴 |
| `db_*.tsv` | 데이터베이스: 이름(`name_*`), 팀·도시·경기장(`team`), 작전명(`play`), 퀴즈(`trivia`), 스카우트 평가(`scout`), 기타 문구(`text`) |
| `story_*.tsv` | 프랜차이즈 신문 기사·헤드라인·사진 설명·이메일 |

- 같은 영문은 모든 화면·표에서 같은 한글로 바뀝니다.
- 한 단어짜리 영문은 실행파일·플래시에서 내부 이름일 수 있어, `ui_*.tsv`에만 있으면 실행파일에는 넣지 않습니다. 실행파일에 넣으려면 `elf_*.tsv`에 적으세요.
- 한글 1자는 2바이트입니다. 고정 칸(데이터베이스 필드, 실행파일 문자열, 일부 화면 라벨)은 원문 바이트 수를 넘을 수 없습니다. 넘친 데이터베이스 번역은 빌드 후 `work/db_long.txt`에 나옵니다.
- 새 원문 목록은 `tools/extract_src.py`(데이터베이스), `tools/elfscan.py`(실행파일), `tools/aptscan.py`(플래시)로 뽑습니다.

## 와이드 패치

`tools/build.py`가 빌드할 때마다 `tools/widescreen.py`로 한글판·원본용 pnach를 만들어 ISO 옆에 씁니다. 릴리즈할 때는 이 파일을 `patches/`에 복사해 xdelta와 함께 첨부합니다.

## 검증

`tools/emu.ps1`(PCSX2 백그라운드 실행·창 캡처·키 입력)과 `tools/tour.ps1`(키 입력·대기·캡처 순서 실행)을 썼습니다. PCSX2 경로는 `emu.ps1` 안에서 직접 고쳐 쓰세요.

빠른 경기 코인 토스까지 가는 순서: 부팅 후 40초 대기 → `0D 4B 0D 4B 4B 4B 4B`(Start, X …) → 약 90초 대기.
