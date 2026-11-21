#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把人性的枷锁精读笔记（Markdown）构建成单文件网页。

用法：
    python3 build.py            # 生成 site/ 下全部页面

产出：
    site/index.html            总览 + 122 章地图
    site/chNN.html             每章阅读器
    site/craft.html            写作技法手册（可搜索）
"""

import glob
import html
import json
import os
import re

ROOT = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(ROOT, 'web')
SITE = os.path.join(ROOT, 'site')

TOTAL_CHAPTERS = 122
CN = ['零', '一', '二', '三', '四', '五', '六', '七', '八', '九', '十']

NAMES = [
    ('Philip', '/ˈfɪlɪp/', '人名：菲利普'),
    ('Emma', '/ˈemə/', '人名：保姆艾玛'),
    ('Watkin', '/ˈwɒtkɪn/', '人名：沃特金（教母）'),
    ('Henrietta', '/ˌhenriˈetə/', '人名：亨丽埃塔'),
    ('William', '/ˈwɪljəm/', '人名：威廉（叔父）'),
    ('Louisa', '/luˈiːzə/', '人名：路易莎（婶母）'),
    ('Devonshire', '/ˈdevənʃə/', '地名：德文郡'),
    ('Onslow gardens', '/ˌɒnzləʊ ˈɡɑːdnz/', '地名：昂斯洛花园（伦敦）'),
    ('London', '/ˈlʌndən/', '地名：伦敦'),
    ('Kensington', '/ˈkenzɪŋtən/', '地名：肯辛顿'),
    ('Blackstable', '/ˈblæksteɪbl/', '地名：布莱克斯特布尔（虚构地名）'),
    ('Notting Hill', '/ˈnɒtɪŋ hɪl/', '地名：诺丁山'),
]

CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳㉑㉒㉓㉔㉕㉖㉗㉘㉙㉚㉛㉜㉝㉞㉟㊱㊲㊳㊴㊵㊶㊷㊸㊹㊺㊻㊼㊽㊾㊿"
NUM = {c: i + 1 for i, c in enumerate(CIRCLED)}
UNIT_RE = re.compile(r'^\*\*(?:([①-⑳㉑-㉟㊱-㊿])|(\d{1,3}))\*\*$')
CJK = re.compile(r'[\u4e00-\u9fff]')
CJK_JOIN = re.compile(r'[\u4e00-\u9fff，。、；：？！“”‘’（）《》〈〉—…·]')


# ---------------------------------------------------------------- 小工具

def esc(t):
    return html.escape(t, quote=False)


def attr(t):
    return html.escape(t, quote=True)


def link_target(url):
    if url.endswith('.md'):
        base = os.path.basename(url)[:-3]
        if base.startswith('writing-craft'):
            return 'craft.html'
        m = re.match(r'ch(\d+)-study-guide', base)
        if m:
            return 'ch%s.html' % m.group(1)
    return url


def smart_join(lines):
    out = ''
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if not out:
            out = line
        elif CJK_JOIN.match(out[-1]) or CJK_JOIN.match(line[0]):
            out += line
        else:
            out += ' ' + line
    return out


def link_refs(s):
    if not s:
        return s
    return ''.join(
        '<a class="ref" href="#p-%d">%s</a>' % (NUM[c], c) if c in NUM else c
        for c in s
    )


def inline(text, refs=True):
    """行内标记：**粗**、`代码`、*斜*、[链接](x)。先保护 code，粗体才能跨过 code。"""
    codes = []

    def stash(m):
        codes.append(m.group(1))
        return '\x01%d\x01' % (len(codes) - 1)

    raw = re.sub(r'`([^`]*)`', stash, text)
    s = esc(raw)
    s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
    s = re.sub(
        r'\[([^\]]+)\]\(([^)]+)\)',
        lambda m: '<a href="%s">%s</a>' % (attr(link_target(m.group(2))), m.group(1)),
        s,
    )
    s = re.sub(r'(?<![\w*])\*(?!\s)([^*]+?)(?<!\s)\*(?![\w*])', r'<em>\1</em>', s)
    if refs:
        s = link_refs(s)

    def back(m):
        return '<code>%s</code>' % esc(codes[int(m.group(1))])

    return re.sub(r'\x01(\d+)\x01', back, s)


def annotate(text, words):
    """把本段词表里的词在原文中加虚线下划线，悬停出音标释义。"""
    terms = sorted({w['w'] for w in words if w.get('w')}, key=len, reverse=True)
    if not terms:
        return text
    tips = {}
    for w in words:
        tips.setdefault(w['w'], w)
    pattern = re.compile(
        r'(?<![\w\-])(' + '|'.join(re.escape(t) for t in terms) + r')(?![\w\-])',
        re.I,
    )

    def repl(m):
        key = m.group(1)
        w = tips.get(key) or tips.get(key.lower()) or {}
        phon = w.get('p', '')
        gloss = w.get('g', '')
        tip = gloss if not phon or phon == '—' else '%s · %s' % (phon, gloss)
        return '<span class="gloss" data-tip="%s">%s</span>' % (attr(tip), m.group(0))

    return pattern.sub(repl, text)


# ---------------------------------------------------------------- 表格

def split_row(row):
    row = row.strip()
    if row.startswith('|'):
        row = row[1:]
    if row.endswith('|'):
        row = row[:-1]
    return [c.strip() for c in row.split('|')]


def render_table(rows, words_out=None):
    rows = [r for r in rows if not re.match(r'^\|[\s:|-]*-[\s:|-]*\|$', r.strip())]
    if not rows:
        return ''
    cells = [split_row(r) for r in rows]
    header, body = cells[0], cells[1:]

    if len(header) == 2 and header[0] == '' and header[1] == '':
        items = ''.join(
            '<div><dt>%s</dt><dd>%s</dd></div>' % (inline(d[0], False), inline(d[1], False))
            for d in body if len(d) >= 2
        )
        return '<dl class="spec">%s</dl>' % items

    if header and header[0] == '词':
        rows_html = ['<tr>%s</tr>' % ''.join('<th>%s</th>' % inline(h, False) for h in header)]
        for d in body:
            if words_out is not None and len(d) >= 3:
                words_out.append({'w': d[0], 'p': d[1], 'g': d[2]})
            rows_html.append('<tr>%s</tr>' % ''.join('<td>%s</td>' % inline(x, False) for x in d))
        return '<table class="wordtable">%s</table>' % ''.join(rows_html)

    head = ''.join('<th>%s</th>' % inline(h, False) for h in header)
    body_html = []
    for d in body:
        body_html.append('<tr>%s</tr>' % ''.join('<td>%s</td>' % inline(x) for x in d))
    return ('<div class="tbl-wrap"><table class="gen"><thead><tr>%s</tr></thead>'
            '<tbody>%s</tbody></table></div>') % (head, ''.join(body_html))


# ---------------------------------------------------------------- 区块

def render_sent(text):
    text = text.replace('【句】', '', 1).lstrip('：: ')
    return '<div class="sent">%s</div>' % inline(text)


def render_quote(paras, words=None):
    if not paras:
        return ''
    out = []
    for p in paras:
        p = p.strip()
        if not p:
            continue
        if not CJK.search(p):
            body = annotate(esc(p), words or [])
            out.append('<p class="en">%s</p>' % body)
        else:
            out.append('<p>%s</p>' % inline(p))
    return '<blockquote>%s</blockquote>' % ''.join(out)


def render_blocks(lines, words=None, toc=None):
    out = []
    i, n = 0, len(lines)
    while i < n:
        s = lines[i].strip()
        if not s:
            i += 1
            continue
        if s == '---':
            out.append('<hr>')
            i += 1
            continue
        if s.startswith('#'):
            level = len(s) - len(s.lstrip('#'))
            text = s[level:].strip()
            tag = 'h%d' % min(level, 4)
            hid = ''
            if toc is not None and level in (2, 3):
                hid = 'h-%d' % (len(toc) + 1)
                toc.append((hid, level, text))
            out.append('<%s%s>%s</%s>' % (tag, (' id="%s"' % hid) if hid else '', inline(text), tag))
            i += 1
            continue
        if s.startswith('<details'):
            block = []
            while i < n:
                block.append(lines[i])
                if lines[i].strip().startswith('</details>'):
                    i += 1
                    break
                i += 1
            text = '\n'.join(block)
            m = re.search(r'<summary>(.*?)</summary>', text, re.S)
            summ = m.group(1).strip() if m else '展开'
            inner = re.sub(r'</?details[^>]*>', '', text)
            inner = re.sub(r'<summary>.*?</summary>', '', inner, flags=re.S)
            out.append('<details class="qa"><summary>%s</summary><div class="inner">%s</div></details>'
                       % (inline(summ), render_blocks(inner.split('\n'))))
            continue
        if s.startswith('>'):
            buf = []
            while i < n and lines[i].lstrip().startswith('>'):
                buf.append(re.sub(r'^\s*>\s?', '', lines[i]))
                i += 1
            paras, cur = [], []
            for b in buf:
                if b.strip():
                    cur.append(b)
                elif cur:
                    paras.append(smart_join(cur))
                    cur = []
            if cur:
                paras.append(smart_join(cur))
            out.append(render_quote(paras, words))
            continue
        if s.startswith('|'):
            rows = []
            while i < n and lines[i].strip().startswith('|'):
                rows.append(lines[i])
                i += 1
            out.append(render_table(rows))
            continue
        if re.match(r'^[-*]\s+', s) or re.match(r'^\d+\.\s+', s):
            ordered = bool(re.match(r'^\d+\.\s+', s))
            start = int(re.match(r'^(\d+)\.', s).group(1)) if ordered else 1
            items = []
            while i < n:
                cur = lines[i].strip()
                m = re.match(r'^([-*]|\d+\.)\s+(.*)$', cur)
                if not m:
                    break
                cont = [m.group(2)]
                i += 1
                while i < n and lines[i].strip() and not re.match(r'^([-*]|\d+\.)\s+', lines[i].strip()) \
                        and not lines[i].strip().startswith(('>', '|', '#')) and lines[i].strip() != '---':
                    cont.append(lines[i].strip())
                    i += 1
                items.append(smart_join(cont))
            if ordered:
                open_tag = '<ol start="%d">' % start if start != 1 else '<ol>'
                out.append('%s%s</ol>' % (open_tag, ''.join('<li>%s</li>' % inline(x) for x in items)))
            else:
                out.append('<ul>%s</ul>' % ''.join('<li>%s</li>' % inline(x) for x in items))
            continue

        buf = [s]
        i += 1
        while i < n and lines[i].strip() and not lines[i].strip().startswith(('>', '|', '#')) \
                and lines[i].strip() != '---' and not re.match(r'^([-*]|\d+\.)\s+', lines[i].strip()):
            buf.append(lines[i].strip())
            i += 1
        text = smart_join(buf)
        if text.startswith('【句】'):
            out.append(render_sent(text))
        elif re.match(r'^\*\*[^*]+\*\*$', text):
            out.append('<h4>%s</h4>' % inline(text.strip('*')))
        else:
            out.append('<p>%s</p>' % inline(text))
    return '\n'.join(out)


# ---------------------------------------------------------------- 场景

def parse_unit(chunk, words):
    """一段：原文 + 译文 + 词表 + 句注。"""
    i, n = 0, len(chunk)
    qlines = []
    while i < n and (not chunk[i].strip() or chunk[i].lstrip().startswith('>')):
        if chunk[i].lstrip().startswith('>'):
            qlines.append(re.sub(r'^\s*>\s?', '', chunk[i]))
        else:
            qlines.append('')
        i += 1

    paras, cur = [], []
    for b in qlines:
        if b.strip():
            cur.append(b)
        elif cur:
            paras.append(smart_join(cur))
            cur = []
    if cur:
        paras.append(smart_join(cur))

    en, trans = [], []
    for p in paras:
        if p.startswith('**译｜**'):
            trans.append(p.replace('**译｜**', '', 1).strip())
        elif p.startswith('译｜'):
            trans.append(p.replace('译｜', '', 1).strip())
        else:
            en.append(p)

    rest = chunk[i:]
    rows, sents, extra = [], [], []
    words = words or []
    j = 0
    while j < len(rest):
        s = rest[j].strip()
        if not s:
            j += 1
            continue
        if s.startswith('|'):
            while j < len(rest) and rest[j].strip().startswith('|'):
                rows.append(rest[j])
                j += 1
            continue
        if s.startswith('【句】'):
            buf = [s]
            j += 1
            while j < len(rest) and rest[j].strip() and not rest[j].strip().startswith(('|', '【句】')):
                buf.append(rest[j].strip())
                j += 1
            sents.append(smart_join(buf))
            continue
        extra.append(s)
        j += 1

    unit_words = []
    if rows:
        for r in rows:
            if re.match(r'^\|[\s:|-]*-[\s:|-]*\|$', r.strip()):
                continue
            c = split_row(r)
            if len(c) >= 3 and c[0] and c[0] != '词':
                unit_words.append({'w': c[0], 'p': c[1], 'g': c[2]})

    parts = []
    for p in en:
        parts.append('<p class="en">%s</p>' % annotate(esc(p), unit_words))
    for p in trans:
        parts.append('<p class="trans">%s</p>' % inline(p))

    chips = []
    if rows:
        table = render_table(rows)
        chips.append(
            '<details class="anno" data-kind="w"><summary>词 · %d</summary><div class="anno-body">%s</div></details>'
            % (max(0, len([r for r in rows if not re.match(r'^\|[\s:|-]*-[\s:|-]*\|$', r.strip())]) - 1), table)
        )
    if sents:
        chips.append(
            '<details class="anno" data-kind="s"><summary>句 · %d</summary><div class="anno-body">%s</div></details>'
            % (len(sents), ''.join(render_sent(x) for x in sents))
        )
    if chips:
        parts.append('<div class="chipbar">%s</div>' % ''.join(chips))
    if extra:
        parts.append(render_blocks(extra))

    return ''.join(parts), words


def render_scene(title, lines, toc):
    """返回 (正文 HTML, 右侧讲解 HTML)。"""
    m = re.match(r'^场景\s*(\d+)[｜|]\s*(.+)$', title)
    num, name = (m.group(1), m.group(2)) if m else ('', title)
    sid = 'scene-%s' % (num or len(toc))
    toc.append((sid, 3, title))

    head = ('<h3 class="scene-title" id="%s"><span class="tag">场景 %s</span>%s</h3>'
            % (sid, num, inline(name)))

    def find(marker):
        for k, l in enumerate(lines):
            if l.strip() == marker:
                return k
        return None

    i_notes = find('**细读**')
    i_craft = find('**写法**')
    marks = sorted([x for x in (i_notes, i_craft) if x is not None])
    body_end = marks[0] if marks else len(lines)

    body = lines[:body_end]
    notes = lines[i_notes + 1:i_craft] if (i_notes is not None and i_craft is not None) else (
        lines[i_notes + 1:] if i_notes is not None else [])
    craft = lines[i_craft + 1:] if i_craft is not None else []

    lead = ''
    k = 0
    while k < len(body) and not body[k].strip():
        k += 1
    if k < len(body) and body[k].lstrip().startswith('>'):
        q = []
        while k < len(body) and body[k].lstrip().startswith('>'):
            q.append(re.sub(r'^\s*>\s?', '', body[k]))
            k += 1
        text = smart_join([x for x in q if x.strip()])
        text = re.sub(r'^\*\*这一场：\*\*\s*', '', text)
        text = re.sub(r'^这一场：\s*', '', text)
        lead = '<div class="scene-lead"><b>这一场　</b>%s</div>' % inline(text)

    units = []
    marks_u = [k2 for k2, l in enumerate(body) if UNIT_RE.match(l.strip())]
    for idx, start in enumerate(marks_u):
        stop = marks_u[idx + 1] if idx + 1 < len(marks_u) else len(body)
        mm = UNIT_RE.match(body[start].strip())
        label = mm.group(1) or mm.group(2)
        n = NUM[label] if mm.group(1) else int(mm.group(2))
        inner, _ = parse_unit(body[start + 1:stop], [])
        units.append('<div class="unit" id="p-%d"><span class="num">%s</span>%s</div>' % (n, label, inner))

    panels = []
    if notes:
        panels.append(
            '<details class="notes" open><summary>细读<em>文意与手法</em></summary><div class="inner">%s</div></details>'
            % render_blocks(notes))
    if craft:
        panels.append(
            '<details class="craft" open><summary>写法<em>这一场教什么</em></summary><div class="inner">%s</div></details>'
            % render_blocks(craft))

    html_scene = ('<section class="scene" id="%s" data-scene="%s">%s%s%s%s</section>'
                  % (sid, num, head, lead, ''.join(units), ''.join(panels)))

    cp = []
    if notes:
        cp.append('<div class="cp-sec" data-kind="notes"><h4>细读</h4><div class="cp-inner">%s</div></div>'
                  % render_blocks(notes))
    if craft:
        cp.append('<div class="cp-sec" data-kind="craft"><h4>写法</h4><div class="cp-inner">%s</div></div>'
                  % render_blocks(craft))

    html_cp = ''
    if cp:
        html_cp = ('<div class="cp" data-scene="%s" hidden>'
                   '<div class="cp-head"><span class="tag">场景 %s</span><b>%s</b></div>'
                   '<div class="cp-body">%s</div></div>') % (num, num, inline(name), ''.join(cp))

    return html_scene, html_cp


def render_scenes_section(lines, toc):
    intro, scenes_out, panes = [], [], []
    subs, cur_title, cur = [], None, []
    for l in lines:
        if l.startswith('### '):
            if cur_title is not None:
                subs.append((cur_title, cur))
            cur_title, cur = l[4:].strip(), []
        elif cur_title is not None:
            cur.append(l)
        elif l.strip():
            intro.append(render_blocks([l]))
    if cur_title is not None:
        subs.append((cur_title, cur))

    for title, body in subs:
        if title.startswith('场景'):
            h, cp = render_scene(title, body, toc)
            scenes_out.append(h)
            if cp:
                panes.append(cp)
        elif title.startswith('五场戏'):
            hid = 'scenes-map'
            toc.append((hid, 3, title))
            intro.append('<h3 id="%s" class="zh-only">%s</h3>' % (hid, inline(title)))
            intro.append('<div class="zh-only">%s</div>' % render_blocks(body))
        else:
            hid = 'h-%d' % (len(toc) + 1)
            toc.append((hid, 3, title))
            intro.append('<h3 id="%s">%s</h3>' % (hid, inline(title)))
            intro.append(render_blocks(body))

    grid = ''
    if scenes_out:
        grid = ('<div class="scenes-grid"><div class="scenes-main">%s</div>'
                '<aside class="companion" id="companion">%s</aside></div>'
                % (''.join(scenes_out), ''.join(panes)))
    return '\n'.join(intro) + grid, panes


def render_test_section(lines, toc):
    cut = None
    for k, l in enumerate(lines):
        if l.strip().startswith('**参考答案**') or l.strip().startswith('**理解题参考答案**'):
            cut = k
            break
    if cut is None:
        return render_blocks(lines)
    before = render_blocks(lines[:cut])
    after = render_blocks(lines[cut + 1:])
    answers = ('<details class="notes answers"><summary>参考答案<em>先自己答，再对</em></summary>'
               '<div class="inner">%s</div></details>') % after
    return before + answers


def _trim(lines):
    out = list(lines)
    while out and (not out[0].strip() or out[0].strip() == '---'):
        out.pop(0)
    while out and (not out[-1].strip() or out[-1].strip() == '---'):
        out.pop()
    return out


def parse_chapter(path):
    num = int(re.search(r'ch(\d+)-', os.path.basename(path)).group(1))
    md = open(path, encoding='utf-8').read()
    lines = md.split('\n')

    first = next(i for i, l in enumerate(lines) if l.startswith('## '))
    front, rest = lines[:first], lines[first:]

    # ---- 头部
    title, sub, meta, spec, callout = '', '', '', '', ''
    body = [l for l in front if l.strip()]
    for l in body:
        if l.startswith('# ') and not title:
            title = l[2:].strip()
    stripped = [l for l in body if not l.startswith('# ')]
    texts = [l for l in stripped if not l.strip().startswith('|') and not l.strip().startswith('>')]
    if texts:
        sub = inline(texts[0])
    for t in texts[1:]:
        if re.match(r'^\d+\s*词', t.strip()):
            meta = t.strip()
            break
    spec_rows = [l for l in stripped if l.strip().startswith('|')]
    if spec_rows:
        spec = render_table(spec_rows)

    # 引言（两条线）
    call_lines = []
    in_q = False
    for l in stripped:
        if l.strip().startswith('>'):
            in_q = True
            call_lines.append(l)
        elif in_q and not l.strip():
            call_lines.append(l)

    # ---- 分节
    sections = []
    cur_title, cur = None, []
    for l in rest:
        if l.startswith('## '):
            if cur_title is not None:
                sections.append((cur_title, cur))
            cur_title, cur = l[3:].strip(), []
        else:
            cur.append(l)
    if cur_title is not None:
        sections.append((cur_title, cur))
    sections = [(t, _trim(lines_)) for t, lines_ in sections]

    def kind_of(t):
        for key, val in (('原文', 'read'), ('逐场精读', 'scenes'),
                         ('词与句', 'lang'), ('毛姆怎么写', 'craft'), ('背景', 'bg'),
                         ('自测', 'test'), ('下一章', 'next')):
            if key in t:
                return val
        return 'other'

    toc = []
    body_html = []
    companion = []
    all_words = []
    for idx, (stitle, slines) in enumerate(sections, 1):
        kind = kind_of(stitle)
        sid = 'sec-%d' % idx
        toc.append((sid, 2, stitle))
        body_html.append('<section class="sec" data-kind="%s" id="%s">' % (kind, sid))
        body_html.append('<h2 class="sec-title">%s</h2>' % inline(stitle))

        if kind == 'read':
            idxs = [i for i, l in enumerate(slines) if l.lstrip().startswith('>')]
            if idxs:
                i0, i1 = idxs[0], idxs[-1] + 1
            else:
                i0, i1 = len(slines), len(slines)
            before, qlines, after = slines[:i0], slines[i0:i1], slines[i1:]

            body_html.append(render_blocks(before))
            paras, cur = [], []
            for l in qlines:
                b = re.sub(r'^\s*>\s?', '', l)
                if b.strip():
                    cur.append(b)
                elif cur:
                    paras.append(smart_join(cur))
                    cur = []
            if cur:
                paras.append(smart_join(cur))
            body_html.append('<div class="reader">%s</div>' %
                             ''.join('<p class="en">%s</p>' % esc(p) for p in paras))
            body_html.append(render_blocks(after))

        elif kind == 'scenes':
            scene_html, _panes = render_scenes_section(slines, toc)
            body_html.append(scene_html)

        elif kind == 'test':
            body_html.append(render_test_section(slines, toc))

        else:
            body_html.append(render_blocks(slines, all_words, toc if kind == 'craft' else None))

        body_html.append('</section>')

    text = '\n'.join(body_html)

    # 收集词条（给词汇小测）：从所有词表里取
    words = []
    seen = set()
    for m in re.finditer(r'\|\s*([^|\n]+?)\s*\|\s*([^|\n]*?)\s*\|\s*([^|\n]+?)\s*\|', md):
        pass
    # 用渲染过程中收集的表格更稳：重新扫一遍 md 的「词」表
    for block in re.findall(r'(\| 词 \| 音标 \| 释义 \|(?:\n\|.*)+)', md):
        for row in block.split('\n')[1:]:
            if re.match(r'^\|[\s:|-]*-[\s:|-]*\|$', row.strip()):
                continue
            c = split_row(row)
            if len(c) >= 3 and c[0] and c[0] not in seen:
                seen.add(c[0])
                words.append({'w': c[0], 'p': c[1], 'g': c[2]})

    chapter_cn = title.split('·')[0].strip().strip('《人性的枷锁》') if title else ''
    return {
        'num': num,
        'title': title,
        'sub': sub,
        'spec': spec,
        'meta': meta,
        'callout': render_quote(_quote_paras(call_lines)),
        'body': text,
        'toc': toc,
        'nsec': len(sections),
        'words': words,
    }


def _quote_paras(lines):
    buf, out, cur = [], [], []
    for l in lines:
        if l.strip().startswith('>'):
            cur.append(re.sub(r'^\s*>\s?', '', l))
        elif cur:
            buf.append(cur)
            cur = []
    if cur:
        buf.append(cur)
    for block in buf:
        paras, c = [], []
        for b in block:
            if b.strip():
                c.append(b)
            elif c:
                paras.append(smart_join(c))
                c = []
        if c:
            paras.append(smart_join(c))
        out.extend(paras)
    return out


# ---------------------------------------------------------------- 页面

def load(name):
    return open(os.path.join(WEB, name), encoding='utf-8').read()


def shell(title, bodyclass, page, crumb, left, content, right, data, fab=''):
    tpl = load('page.html')
    return (tpl.replace('%%TITLE%%', attr(title))
               .replace('%%CSS%%', load('style.css'))
               .replace('%%BODYCLASS%%', bodyclass)
               .replace('%%PAGE%%', page)
               .replace('%%CRUMB%%', crumb)
               .replace('%%LEFT%%', left)
               .replace('%%RIGHT%%', right)
               .replace('%%CONTENT%%', content)
               .replace('%%DATA%%', json.dumps(data, ensure_ascii=False))
               .replace('%%FAB%%', fab)
               .replace('%%JS%%', load('app.js')))



def latest_review():
    fs = sorted(glob.glob(os.path.join(ROOT, 'review-*.md')))
    if not fs:
        return None
    name = os.path.basename(fs[-1])[:-3]
    nums = [str(int(x)) for x in name.split('-')[1:]]
    return name + '.html', '复习 · ' + '–'.join(nums)


def reviews():
    out = []
    for f in sorted(glob.glob(os.path.join(ROOT, 'review-*.md'))):
        name = os.path.basename(f)[:-3]
        nums = [int(x) for x in name.split('-')[1:]]
        out.append((nums[0], nums[-1], name + '.html', '复习 · %d–%d' % (nums[0], nums[-1])))
    return out


def review_link(page):
    rv = latest_review()
    if not rv:
        return ''
    href, label = rv
    cls = ' class="cur"' if page == 'review' else ''
    return '<a%s href="%s">%s<span>跨章</span></a>' % (cls, href, label)


def left_nav(num, available, page=''):
    items = []
    rv_by_end = {}
    for a, b, href, label in reviews():
        rv_by_end.setdefault(b, []).append((href, label))
    for n in range(1, TOTAL_CHAPTERS + 1):
        label = '<span class="n">%02d</span>第 %d 章' % (n, n)
        if n == num:
            items.append('<li><a class="cur" href="ch%02d.html">%s</a></li>' % (n, label))
        elif n in available:
            items.append('<li><a href="ch%02d.html">%s</a></li>' % (n, label))
        else:
            items.append('<li><span class="off">%s</span></li>' % label)
        for href, label2 in rv_by_end.get(n, []):
            items.append('<li><a href="%s"><span class="n"></span>%s</a></li>' % (href, label2))

    tools = ''
    if num:
        tools = ('<div class="ch-tools">'
                 '<button class="btn small" id="wbBtn" type="button">生词本 <b id="wbCount">0</b></button>'
                 '<button class="btn small" id="quizBtn2" type="button">小测</button></div>')

    return """<aside class="nav-left" id="navLeft">
  <div class="panel-bar"><span>导航</span><button class="panel-close" type="button" data-close="left" aria-label="关闭">×</button></div>
  <div class="brand">Of Human Bondage</div>
  <div class="site-name">人性的枷锁 · 精读</div>
  <nav class="gl-links">
    <a class="%s" href="index.html">总览<span>122 章</span></a>
    <a class="%s" href="reading.html">阅读方法手册<span>初读</span></a>
    <a class="%s" href="craft.html">写作技法手册<span>21 条</span></a>
  </nav>
  %s
  <div class="side-label ch-label">章节</div>
  <ol class="ch-list">%s</ol>
</aside>""" % ('cur' if page == 'home' else '',
               'cur' if page == 'reading' else '',
               'cur' if page == 'craft' else '', tools, ''.join(items))


def right_nav(toc, title):
    if not toc:
        return ''
    links = []
    for hid, lv, text in toc:
        cls = 'lv2' if lv == 2 else 'lv3'
        links.append('<a class="%s" href="#%s">%s</a>' % (cls, hid, esc(text)))
    return """<aside class="nav-right" id="navRight">
  <div class="rn-head"><span>%s</span><button class="rn-toggle" id="toggleRight2" type="button" data-close="right" aria-label="收起目录">×</button></div>
  <nav class="toc">%s</nav>
</aside>""" % (esc(title or '目录'), ''.join(links))


def build_chapter(path, available):
    ch = parse_chapter(path)
    num = ch['num']
    title = ch['title']
    words = ch['words']
    cn = ['零', '一', '二', '三', '四', '五', '六', '七', '八', '九', '十']

    head = ['<header class="doc-head">']
    if title:
        head.append('<h1 class="doc-title">%s</h1>' % inline(title))
    if ch['sub']:
        head.append('<div class="doc-sub">%s</div>' % ch['sub'])
    if ch['meta']:
        head.append('<p class="doc-meta">%s</p>' % inline(ch['meta'], False))
    if ch['callout']:
        head.append('<div class="questions">%s</div>' % ch['callout'])
    head.append('</header>')

    content = '\n'.join(head) + ch['body']

    # 写作练习（独立一节）
    ch['toc'].append(('sec-write', 2, CN[ch['nsec'] + 1] + '、写作练习'))
    content += '''
<section class="sec" data-kind="write" id="sec-write">
<h2 class="sec-title">九、写作练习</h2>
<div class="writing">
  <div class="hint">任务见第四节「现在就写」。写两句也好，内容只存在本机浏览器。</div>
  <textarea placeholder="在这里写…"></textarea>
  <div class="row">
    <span class="count">0 词</span>
    <span class="status"></span>
    <span class="spacer"></span>
    <button class="btn copy" type="button">复制</button>
    <button class="btn clear" type="button">清空</button>
  </div>
</div>
</section>
'''
    content = content.replace('九、写作练习', CN[ch['nsec'] + 1] + '、写作练习', 1)
    if '现在就写' not in ch['body']:
        content = content.replace('任务见第四节「现在就写」。写两句也好，', '')

    nav = []
    if (num - 1) in available:
        nav.append('<a href="ch%02d.html">← 第%s章</a>' % (num - 1, cn[num - 1] if num - 1 <= 10 else num - 1))
    else:
        nav.append('<span class="off">← 上一章</span>')
    if (num + 1) in available:
        nav.append('<a href="ch%02d.html">第%s章 →</a>' % (num + 1, cn[num + 1] if num + 1 <= 10 else num + 1))
    else:
        nav.append('<span class="off">下一章 →</span>')
    content += '<nav class="chnav">%s</nav>' % ''.join(nav)

    words_n = re.search(r'(\d+)\s*词', ch['meta'] or '')
    ch_name = '第%s章' % cn[num] if num <= 10 else '第 %d 章' % num

    html_doc = shell(
        title='%s · Of Human Bondage' % ch_name,
        bodyclass='chapter',
        page='chapter',
        crumb='<b>人性的枷锁</b> · %s' % ch_name,
        left=left_nav(num, available, 'chapter'),
        content=content,
        right=right_nav(ch['toc'], '本章目录'),
        data={'id': 'ch%d' % num, 'href': 'ch%02d.html' % num, 'num': cn[num] if num <= 10 else str(num), 'words': words},
    )

    out = os.path.join(SITE, 'ch%02d.html' % num)
    open(out, 'w', encoding='utf-8').write(html_doc)
    return num, title, words_n.group(1) if words_n else ''


def available_chapters():
    out = set()
    for p in glob.glob(os.path.join(ROOT, 'ch*-study-guide.md')):
        m = re.search(r'ch(\d+)-', os.path.basename(p))
        if m:
            out.add(int(m.group(1)))
    return out


def build_doc(md_name, out_name, page, page_title, crumb, subtitle, toc_label='本页目录', search=True):
    md = open(os.path.join(ROOT, md_name), encoding='utf-8').read()
    lines = md.split('\n')
    title = lines[0].lstrip('# ').strip()
    toc = []
    body = render_blocks(lines[1:], toc=toc)
    body = re.sub(r'<a class="ref" href="#p-\d+">(.*?)</a>', r'\1', body)
    box = '<input class="search" type="search" placeholder="搜索关键词…">' if search else ''

    content = (
        '<div class="doc-main">\n'
        '<header class="doc-head">\n'
        '  <h1 class="doc-title">%s</h1>\n'
        '  <div class="doc-sub">%s</div>\n'
        '  %s\n'
        '</header>\n'
        '<div class="sec">%s</div>\n'
        '</div>' % (inline(title), subtitle, box, body)
    )

    doc = shell(
        title='%s · Of Human Bondage' % title,
        bodyclass='',
        page=page,
        crumb='<b>人性的枷锁</b> · %s' % crumb,
        left=left_nav(0, available_chapters(), page),
        content=content,
        right=right_nav(toc, toc_label),
        data={},
    )
    open(os.path.join(SITE, out_name), 'w', encoding='utf-8').write(doc)


def build_craft():
    build_doc('writing-craft.md', 'craft.html', 'craft', '写作技法手册',
              '技法手册',
              '技法索引 · 当索引用，别当教材读；真正的教学在每章笔记的「写法」里。')


def build_reviews():
    for f in sorted(glob.glob(os.path.join(ROOT, 'review-*.md'))):
        name = os.path.basename(f)[:-3]
        build_doc(name + '.md', name + '.html', 'review', '复习', '复习',
                  '跨章复习：把散在各章的线收一收，顺便把词和句型过一遍。')


def build_reading():
    build_doc('reading-method.md', 'reading.html', 'reading', '阅读方法手册',
              '阅读方法',
              '初读用来建立整体感知：故事、人物、情感、作者怎么讲。深读留给第二遍。')


def available_chapters():
    out = set()
    for p in glob.glob(os.path.join(ROOT, 'ch*-study-guide.md')):
        m = re.search(r'ch(\d+)-', os.path.basename(p))
        if m:
            out.add(int(m.group(1)))
    return out


def build_index(chapters):
    cells = []
    for n in range(1, TOTAL_CHAPTERS + 1):
        if n in chapters:
            cells.append('<a class="cell" href="ch%02d.html" data-ch="%d" title="%s">%d</a>'
                         % (n, n, attr(chapters[n]['title']), n))
        else:
            cells.append('<span class="cell todo" data-ch="%d" title="待做">%d</span>' % (n, n))

    total_words = sum(int(c['words']) for c in chapters.values() if c['words'])
    done = len(chapters)

    content = '''<div class="home">
  <div class="brand">Of Human Bondage · 1915</div>
  <h1>人性的枷锁<br>精读计划</h1>
  <p class="lead">一章一份笔记：原文对照、逐场精读、语言点，加一节「一个作家怎么读，怎么写」。<br>
  点亮着的格子开始读。</p>
  <div class="stats">
    <div class="stat"><b>%d</b><span>已生成章节</span></div>
    <div class="stat"><b>%d</b><span>全书章数</span></div>
    <div class="stat"><b>%s</b><span>已读词数</span></div>
  </div>
  <div class="grid">%s</div>
  <div class="links">
    <a href="craft.html"><b>写作技法手册 →</b><span>21 条技法 · 句式库 · 自检清单</span></a>
    <a href="ch05.html"><b>从第五章读起 →</b><span>轻章样板：十二张照片</span></a>
    <a href="review-01-05.html"><b>复习 · 第 1–5 章 →</b><span>时间线、母题、30 词、八个问题</span></a>
  </div>
</div>''' % (done, TOTAL_CHAPTERS, '{:,}'.format(total_words), ''.join(cells))

    doc = shell(
        title='人性的枷锁 · 精读计划',
        bodyclass='no-right',
        page='home',
        crumb='<b>人性的枷锁</b> · 总览',
        left=left_nav(0, set(chapters), 'home'),
        content=content,
        right='',
        data={},
    )
    open(os.path.join(SITE, 'index.html'), 'w', encoding='utf-8').write(doc)


def main():
    os.makedirs(SITE, exist_ok=True)
    paths = sorted(glob.glob(os.path.join(ROOT, 'ch*-study-guide.md')))
    available = set(int(re.search(r'ch(\d+)-', os.path.basename(p)).group(1)) for p in paths)
    chapters = {}
    for path in paths:
        num, title, words = build_chapter(path, available)
        chapters[num] = {'title': title, 'words': words}
        print('  ch%02d.html  %s' % (num, title))
    build_craft()
    print('  craft.html')
    build_reading()
    print('  reading.html')
    build_reviews()
    print('  review pages')
    build_index(chapters)
    print('  index.html')
    print('done →', SITE)


if __name__ == '__main__':
    main()
