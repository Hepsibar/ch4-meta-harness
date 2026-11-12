#!/usr/bin/env python3
"""웹툰 컷 이미지 생성 — OpenAI GPT Image API 호출.

표준 라이브러리만 사용한다(추가 설치 불필요). 캐릭터 참조 이미지를 넘기면
images/edits 엔드포인트로, 없으면 images/generations 엔드포인트로 생성한다.

사용 예:
  python gen_image.py --prompt-file cut_012.txt --out _workspace/04_images/cut_012.png
  python gen_image.py --prompt "..." --out out.png --size 1024x1536
  python gen_image.py --prompt-file cut_012.txt --out out.png --reference ref.png
  python gen_image.py --prompt "..." --out out.png --dry-run   # API 호출 없이 요청만 검증

환경 변수:
  OPENAI_API_KEY        필수(실제 생성 시). OpenAI API 키.
  WEBTOON_IMAGE_MODEL   선택. 기본 gpt-image-1. 계정이 제공하는 이미지 모델 id로 바꾼다.
"""
import argparse
import base64
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.request
import uuid

GEN_URL = "https://api.openai.com/v1/images/generations"
EDIT_URL = "https://api.openai.com/v1/images/edits"


def load_dotenv():
    """현재 디렉터리에서 위로 올라가며 .env를 찾아 환경 변수로 읽는다.

    이미 설정된 환경 변수는 덮어쓰지 않는다(셸에서 준 값이 우선).
    따옴표와 'export ' 접두사, # 주석을 처리한다. 추가 설치가 필요 없다.
    """
    d = os.getcwd()
    while True:
        path = os.path.join(d, ".env")
        if os.path.isfile(path):
            try:
                with open(path, encoding="utf-8") as fh:
                    for line in fh:
                        line = line.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        if line.startswith("export "):
                            line = line[len("export "):]
                        name, _, value = line.partition("=")
                        name = name.strip()
                        value = value.strip().strip('"').strip("'")
                        if name and name not in os.environ:
                            os.environ[name] = value
            except OSError:
                pass
            return
        parent = os.path.dirname(d)
        if parent == d:
            return
        d = parent


def build_multipart(fields, files):
    """멀티파트 요청 본문을 만든다. fields: [(name, value)], files: [(name, path)]."""
    boundary = "----webtoon" + uuid.uuid4().hex
    body = bytearray()
    for name, value in fields:
        body += ("--%s\r\n" % boundary).encode()
        body += ('Content-Disposition: form-data; name="%s"\r\n\r\n' % name).encode()
        body += ("%s\r\n" % value).encode()
    for name, path in files:
        fname = os.path.basename(path)
        ctype = mimetypes.guess_type(path)[0] or "application/octet-stream"
        with open(path, "rb") as fh:
            data = fh.read()
        body += ("--%s\r\n" % boundary).encode()
        body += ('Content-Disposition: form-data; name="%s"; filename="%s"\r\n'
                 % (name, fname)).encode()
        body += ("Content-Type: %s\r\n\r\n" % ctype).encode()
        body += data + b"\r\n"
    body += ("--%s--\r\n" % boundary).encode()
    return boundary, bytes(body)


def parse_args(argv):
    p = argparse.ArgumentParser(description="웹툰 컷 이미지 생성(GPT Image)")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--prompt", help="프롬프트 문자열")
    src.add_argument("--prompt-file", help="프롬프트가 담긴 텍스트 파일 경로")
    p.add_argument("--out", required=True, help="저장할 PNG 경로")
    p.add_argument("--size", default="1024x1536",
                   help="이미지 크기(기본 1024x1536 세로)")
    p.add_argument("--model",
                   default=os.environ.get("WEBTOON_IMAGE_MODEL", "gpt-image-1"),
                   help="이미지 모델 id(기본 gpt-image-1)")
    p.add_argument("--reference", action="append", default=[],
                   help="일관성 참조 이미지 경로. 여러 번 지정 가능")
    p.add_argument("--quality", default="high", help="품질(기본 high)")
    p.add_argument("--dry-run", action="store_true",
                   help="API를 호출하지 않고 요청 내용만 출력")
    return p.parse_args(argv)


def main(argv=None):
    load_dotenv()  # parse_args보다 먼저 호출해야 --model 기본값에 .env가 반영된다
    a = parse_args(sys.argv[1:] if argv is None else argv)

    prompt = a.prompt
    if a.prompt_file:
        try:
            with open(a.prompt_file, encoding="utf-8") as fh:
                prompt = fh.read().strip()
        except OSError as e:
            sys.exit("오류: 프롬프트 파일을 읽을 수 없다 — %s" % e)
    if not prompt:
        sys.exit("오류: 프롬프트가 비어 있다.")

    for ref in a.reference:
        if not os.path.isfile(ref):
            sys.exit("오류: 참조 이미지가 없다 — %s" % ref)

    use_edit = bool(a.reference)
    plan = {
        "endpoint": EDIT_URL if use_edit else GEN_URL,
        "model": a.model,
        "size": a.size,
        "quality": a.quality,
        "references": a.reference,
        "out": a.out,
        "prompt_chars": len(prompt),
        "prompt_preview": prompt[:160],
    }
    if a.dry_run:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0

    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        sys.exit("오류: OPENAI_API_KEY 환경 변수가 없다. 프롬프트는 완성됐으니 키 설정 후 다시 실행한다.")

    out_dir = os.path.dirname(os.path.abspath(a.out))
    os.makedirs(out_dir, exist_ok=True)

    try:
        if use_edit:
            fields = [("model", a.model), ("prompt", prompt),
                      ("size", a.size), ("quality", a.quality), ("n", "1")]
            files = [("image[]", ref) for ref in a.reference]
            boundary, body = build_multipart(fields, files)
            req = urllib.request.Request(EDIT_URL, data=body, method="POST")
            req.add_header("Content-Type",
                           "multipart/form-data; boundary=%s" % boundary)
        else:
            payload = {"model": a.model, "prompt": prompt,
                       "size": a.size, "quality": a.quality, "n": 1}
            req = urllib.request.Request(
                GEN_URL, data=json.dumps(payload).encode("utf-8"), method="POST")
            req.add_header("Content-Type", "application/json")
        req.add_header("Authorization", "Bearer %s" % key)

        with urllib.request.urlopen(req, timeout=300) as resp:
            result = json.load(resp)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:500]
        sys.exit("API 오류 %s: %s" % (e.code, detail))
    except urllib.error.URLError as e:
        sys.exit("네트워크 오류: %s" % e.reason)

    try:
        b64 = result["data"][0]["b64_json"]
    except (KeyError, IndexError, TypeError):
        sys.exit("예상치 못한 응답 형식: %s" % json.dumps(result)[:500])

    with open(a.out, "wb") as fh:
        fh.write(base64.b64decode(b64))
    print("저장 완료: %s" % a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
