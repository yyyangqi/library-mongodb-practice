# -*- coding: utf-8 -*-
"""把模板中 KaiTi_GB2312 旧字体名替换为楷体（run 级与样式级）。"""
from docx import Document
from docx.oxml.ns import qn

P = r"C:\Users\26295\Doubao\chats\2026-10-21\new-chat\图书情报检索与统计平台\数据2403班-202414870302-杨淇.docx"
doc = Document(P)

def fix_fonts(root, tag):
    cnt = 0
    for el in root.iter(tag):
        for attr in (qn('w:eastAsia'), qn('w:ascii'), qn('w:hAnsi')):
            v = el.get(attr)
            if v and v.lower().replace('_','') in ('kaitigb2312', 'kaiti_gb2312'):
                el.set(attr, '楷体')
                cnt += 1
    return cnt

# document.xml 与 styles.xml 中所有 rFonts
from docx.oxml.ns import qn as _q
cnt1 = fix_fonts(doc.element, _q('w:rFonts'))
# 处理 styles part
for st in doc.styles.element.iter(_q('w:rFonts')):
    for attr in (_q('w:eastAsia'),):
        v = st.get(attr)
        if v and v.lower().replace('_','') in ('kaitigb2312','kaiti_gb2312'):
            st.set(attr, '楷体')

doc.save(P)
print("已替换 run 级字体数:", cnt1)
