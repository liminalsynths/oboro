"""把 web/product image/ 裡的產品原圖轉成網站用的照片，並更新 index.html。

用法（在 repo 根目錄）：python3 tools/build_images.py

- 每個資料夾只取單一字母命名的檔案（a、b、c…），照字母順序排
- 從原圖正中央裁成 2:3 直式，輸出 img/<款式>-<序號>.webp（1080×1620）
- 更新 index.html 裡的模糊預覽圖、各款照片張數，並把 IMG_VERSION 加一
"""
import base64
import io
import re
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'web' / 'product image'
OUT = ROOT / 'img'
HTML = ROOT / 'index.html'

# 資料夾 → 網站上的款式 id
FOLDERS = {
    '白款Saku Oshima': 'oshima',
    '粉紅款 Saku Kawaz': 'kawazu',
}


def crop_2x3(im):
    im = ImageOps.exif_transpose(im)
    if im.mode in ('RGBA', 'LA'):
        bg = Image.new('RGB', im.size, 'white')
        bg.paste(im, mask=im.getchannel('A'))
        im = bg
    im = im.convert('RGB')
    # 原圖比 2:3 寬就裁左右，比 2:3 高就裁上下，都從正中央取
    w, h = im.size
    if w * 3 > h * 2:
        cw, ch = h * 2 // 3, h
    else:
        cw, ch = w, w * 3 // 2
    left, top = (w - cw) // 2, (h - ch) // 2
    return im.crop((left, top, left + cw, top + ch))


def main():
    placeholders, counts = {}, {}
    for folder, vid in FOLDERS.items():
        for old in OUT.glob(f'{vid}-*.webp'):
            old.unlink()
        files = sorted(
            (f for f in (SRC / folder).iterdir() if re.fullmatch(r'[a-z]', f.stem.lower())),
            key=lambda f: f.stem.lower(),
        )
        for i, f in enumerate(files, 1):
            sq = crop_2x3(Image.open(f))
            sq.resize((1080, 1620), Image.LANCZOS).save(OUT / f'{vid}-{i}.webp', 'WEBP', quality=78, method=6)
            buf = io.BytesIO()
            sq.resize((16, 24), Image.LANCZOS).save(buf, 'JPEG', quality=60)
            placeholders[f'{vid}-{i}'] = 'data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode()
            print(f'{vid}-{i}.webp  <-  {folder}/{f.name}')
        counts[vid] = len(files)

    html = HTML.read_text(encoding='utf-8')
    block = ',\n'.join(f"      '{k}': '{v}'" for k, v in placeholders.items())
    html, n = re.subn(r'(const PLACEHOLDERS = \{\n).*?(\n    \};)', lambda m: m.group(1) + block + m.group(2), html, flags=re.S)
    assert n == 1, 'PLACEHOLDERS block not found'
    for vid, c in counts.items():
        html, n = re.subn(rf"(\{{ id: '{vid}',[^}}]*?photos: )\d+", rf'\g<1>{c}', html)
        assert n == 1, f'photos count for {vid} not found'
    html, n = re.subn(r"const IMG_VERSION = '(\d+)';", lambda m: f"const IMG_VERSION = '{int(m.group(1)) + 1}';", html)
    assert n == 1, 'IMG_VERSION not found'
    HTML.write_text(html, encoding='utf-8')
    print('index.html updated:', counts)


if __name__ == '__main__':
    main()
