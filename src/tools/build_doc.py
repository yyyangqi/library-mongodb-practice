"""生成《智慧图书馆数字资源平台》项目报告 DOCX。

数据全部取自本项目 records 目录下的真实执行记录，图表来自 screenshots 目录。
"""
import os
import sys

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SHOTS = os.path.join(ROOT, "screenshots")
OUT = os.path.join(ROOT, "docs", "智慧图书馆数字资源平台-项目报告.docx")

CN_BODY = "宋体"
CN_HEAD = "黑体"
EN_FONT = "Times New Roman"


def set_run(run, size=10.5, cn=CN_BODY, bold=False, color=(0, 0, 0)):
    run.font.name = EN_FONT
    run.font.size = Pt(size)
    run.bold = bold
    run.font.color.rgb = RGBColor(*color)
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    rfonts.set(qn("w:eastAsia"), cn)
    rfonts.set(qn("w:ascii"), EN_FONT)
    rfonts.set(qn("w:hAnsi"), EN_FONT)


def tune_styles(doc):
    st = doc.styles
    normal = st["Normal"]
    normal.font.name = EN_FONT
    normal.font.size = Pt(10.5)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), CN_BODY)
    pf = normal.paragraph_format
    pf.line_spacing = 1.38
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)
    pf.first_line_indent = Pt(21)
    pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    for name, size, before, after in (("Heading 1", 12, 12, 6), ("Heading 2", 10.5, 6, 3)):
        h = st[name]
        h.font.name = EN_FONT
        h.font.size = Pt(size)
        h.font.bold = True
        h.font.color.rgb = RGBColor(0, 0, 0)
        h.element.rPr.rFonts.set(qn("w:eastAsia"), CN_HEAD)
        hpf = h.paragraph_format
        hpf.space_before = Pt(before)
        hpf.space_after = Pt(after)
        hpf.first_line_indent = Pt(0)
        hpf.line_spacing = 1.38
        hpf.keep_with_next = True
        hpf.alignment = WD_ALIGN_PARAGRAPH.LEFT

    for name in ("Title", "Subtitle", "Caption"):
        if name not in [s.name for s in st]:
            continue


def body(doc, text, indent=True, size=10.5, align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_after=0):
    p = doc.add_paragraph()
    p.paragraph_format.first_line_indent = Pt(21) if indent else Pt(0)
    p.paragraph_format.line_spacing = 1.38
    p.paragraph_format.space_after = Pt(space_after)
    p.alignment = align
    run = p.add_run(text)
    set_run(run, size=size)
    return p


def heading(doc, text, level=1):
    p = doc.add_paragraph(style="Heading %d" % level)
    run = p.add_run(text)
    set_run(run, size=12 if level == 1 else 10.5, cn=CN_HEAD, bold=True)
    return p


def caption(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.first_line_indent = Pt(0)
    p.paragraph_format.line_spacing = 1.0
    p.paragraph_format.keep_with_next = True
    run = p.add_run(text)
    set_run(run, size=9, cn=CN_HEAD, bold=False)
    return p


def cell_text(cell, text, size=9, bold=False, align=WD_ALIGN_PARAGRAPH.LEFT):
    cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    p = cell.paragraphs[0]
    p.alignment = align
    p.paragraph_format.first_line_indent = Pt(0)
    p.paragraph_format.line_spacing = 1.0
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    run = p.add_run(text)
    set_run(run, size=size, bold=bold)


def three_line(table, header_rows=1):
    tbl = table._tbl
    tblPr = tbl.tblPr
    for el in tblPr.findall(qn("w:tblBorders")):
        tblPr.remove(el)
    borders = OxmlElement("w:tblBorders")
    for edge, sz in (("top", 8), ("bottom", 8)):
        e = OxmlElement("w:" + edge)
        e.set(qn("w:val"), "single")
        e.set(qn("w:sz"), str(sz))
        e.set(qn("w:color"), "000000")
        borders.append(e)
    for edge in ("left", "right", "insideH", "insideV"):
        e = OxmlElement("w:" + edge)
        e.set(qn("w:val"), "none")
        e.set(qn("w:sz"), "0")
        borders.append(e)
    tblPr.append(borders)
    # 表头下横线
    for cell in table.rows[header_rows - 1].cells:
        tcPr = cell._tc.get_or_add_tcPr()
        tcb = OxmlElement("w:tcBorders")
        e = OxmlElement("w:bottom")
        e.set(qn("w:val"), "single")
        e.set(qn("w:sz"), "4")
        e.set(qn("w:color"), "000000")
        tcb.append(e)
        tcPr.append(tcb)


def make_table(doc, headers, rows, widths=None, aligns=None, size=9):
    table = doc.add_table(rows=1, cols=len(headers))
    table.autofit = True
    table.alignment = WD_ALIGN_PARAGRAPH.CENTER
    hdr = table.rows[0]
    # 表头行不跨页、重复表头
    trPr = hdr._tr.get_or_add_trPr()
    cant = OxmlElement("w:cantSplit")
    trPr.append(cant)
    th = OxmlElement("w:tblHeader")
    trPr.append(th)
    for i, h in enumerate(headers):
        cell_text(hdr.cells[i], h, size=size, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
    for r in rows:
        row = table.add_row()
        trPr = row._tr.get_or_add_trPr()
        trPr.append(OxmlElement("w:cantSplit"))
        for i, v in enumerate(r):
            al = WD_ALIGN_PARAGRAPH.LEFT
            if aligns and i < len(aligns):
                al = aligns[i]
            cell_text(row.cells[i], str(v), size=size, align=al)
    if widths:
        for i, w in enumerate(widths):
            for row in table.rows:
                row.cells[i].width = Cm(w)
    three_line(table)
    return table


def add_toc(doc):
    p = doc.add_paragraph()
    p.paragraph_format.first_line_indent = Pt(0)
    r = p.add_run()
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), r'TOC \o "1-1" \h \z \u')
    inner = OxmlElement("w:r")
    t = OxmlElement("w:t")
    t.text = "（打开文档后按 Ctrl+A、F9 更新目录域）"
    inner.append(t)
    fld.append(inner)
    p._p.append(fld)


def add_page_number_footer(section):
    section.footer.is_linked_to_previous = False
    p = section.footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Pt(0)
    run = p.add_run()
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), "PAGE")
    r = OxmlElement("w:r")
    t = OxmlElement("w:t")
    t.text = "1"
    r.append(t)
    fld.append(r)
    run._r.addnext(fld)
    set_run(run, size=9)


def restart_numbering(section):
    sectPr = section._sectPr
    for el in sectPr.findall(qn("w:pgNumType")):
        sectPr.remove(el)
    pg = OxmlElement("w:pgNumType")
    pg.set(qn("w:start"), "1")
    sectPr.append(pg)


def picture(doc, name, cap, width=9.5):
    path = os.path.join(SHOTS, name)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Pt(0)
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.line_spacing = 1.0
    p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(path, width=Cm(width))
    caption(doc, cap)


def page_break(doc):
    from docx.enum.text import WD_BREAK
    p = doc.add_paragraph()
    p.paragraph_format.first_line_indent = Pt(0)
    p.add_run().add_break(WD_BREAK.PAGE)


def build():
    doc = Document()
    tune_styles(doc)
    # 打开文档时自动更新目录与页码域
    settings = doc.settings.element
    uf = OxmlElement("w:updateFields")
    uf.set(qn("w:val"), "true")
    settings.append(uf)

    sec = doc.sections[0]
    sec.page_width = Cm(21)
    sec.page_height = Cm(29.7)
    for attr in ("top_margin", "bottom_margin", "left_margin", "right_margin"):
        setattr(sec, attr, Cm(2.5))

    # ---------------- 封面 ----------------
    for _ in range(3):
        p = doc.add_paragraph()
        p.paragraph_format.first_line_indent = Pt(0)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Pt(0)
    run = p.add_run("智慧图书馆数字资源平台的设计与实现")
    set_run(run, size=22, cn=CN_HEAD, bold=True)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Pt(0)
    p.paragraph_format.space_before = Pt(8)
    run = p.add_run("——基于 MongoDB 单机、副本集与分片集群的课程实践")
    set_run(run, size=14, cn="楷体", bold=False)

    for _ in range(4):
        doc.add_paragraph()

    info = [("课　　程", "《NoSQL 数据库技术与应用》期末项目"),
            ("专　　业", "数据科学与大数据技术"),
            ("姓　　名", "杨　淇"),
            ("学　　号", "202414870302"),
            ("指导教师", "＿＿＿＿＿＿"),
            ("完成日期", "2026 年 11 月 9 日")]
    for k, v in info:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.first_line_indent = Pt(0)
        p.paragraph_format.space_before = Pt(6)
        run = p.add_run("%s：%s" % (k, v))
        set_run(run, size=12, cn=CN_BODY)

    page_break(doc)

    # 摘要并入封面页（控制篇幅）

    p = doc.add_paragraph()
    p.paragraph_format.first_line_indent = Pt(0)
    run = p.add_run("摘　要")
    set_run(run, size=12, cn=CN_HEAD, bold=True)
    body(doc, "本文以智慧图书馆数字资源平台为对象，完成从单机部署到副本集、分片集群的工程实践。"
              "平台以 MongoDB 8.0.4 为存储引擎，用 Python 3 与 pymongo 4.19 实现 21 项业务功能，"
              "覆盖图书、读者、借阅、统计、文件与审计六类数据。数据模型方面，books 与 readers 采用嵌入式文档；"
              "borrow_logs 具备“时间戳—元数据—测量值”结构，采用时间序列集合承载 3000 条借阅流水；"
              "电子书与封面图由 GridFS 存储，6 个文件下载后与源文件字节完全一致。检索与统计共实现 11 项，"
              "在此基础上对 books 的 8 个索引做优化前后对比：在扩展数据集（5 万图书、30 万借阅流水）上，"
              "组合条件查询的耗时由 26.366 ms 降至 0.573 ms，提升 46.03 倍；排序查询由 15.894 ms 降至 0.465 ms，"
              "提升 34.20 倍。权限方面以 read、readWrite、dbOwner 三个账号验证最小权限，只读账号的 4 项写入全部被拒绝。"
              "高可用方面部署三节点副本集 rsLib，两轮强制终止主节点的演练中，副本集分别用 11.6 s 与 17.4 s 完成选主，"
              "业务探针 54 次操作成功率 94.4%，业务中断约 7.3 s，并完成第四节点的加入与移除。"
              "扩展性方面搭建由配置服务器、两个分片与 mongos 组成的分片集群，为 borrow_logs 选定 reader_card 作为分片键并预分片，"
              "3000 条流水在两个分片各占 510 个桶、1500 条；定向查询只落在一个分片（1.91 ms），"
              "非分片键查询需两片归并（4.06～4.30 ms）。实践表明，按数据形态选择集合类型、按查询模式选择分片键，"
              "是 NoSQL 方案能否落地的关键。")
    p = doc.add_paragraph()
    p.paragraph_format.first_line_indent = Pt(0)
    p.paragraph_format.space_before = Pt(6)
    run = p.add_run("关键词：")
    set_run(run, size=10.5, cn=CN_HEAD, bold=True)
    run = p.add_run("MongoDB；时间序列集合；副本集；分片集群；GridFS")
    set_run(run, size=10.5)

    # ---------------- 正文（新分节，页码从 1 起） ----------------
    body_sec = doc.add_section(WD_SECTION.NEW_PAGE)
    restart_numbering(body_sec)
    add_page_number_footer(body_sec)


    # ============ 1 项目概述 ============
    heading(doc, "1　项目概述", 1)
    heading(doc, "1.1　背景与目标", 2)
    body(doc, "图书馆的业务数据长期以两类形态并存：一类是图书、读者这类字段相对固定、便于整体读取的主数据；"
              "另一类是借阅流水这类按时间持续追加、只做区间查询与聚合的时序数据；此外还有电子书、封面图等二进制资源。"
              "传统单表结构在处理第二、三类数据时，要么产生大量稀疏列，要么把文件塞进数据库导致备份膨胀。"
              "本项目以“智慧图书馆数字资源平台”为题，用文档数据库承载上述三类数据，并按课程要求把同一套业务程序"
              "依次部署到单机、三节点副本集与分片集群三种架构上，观察同一条查询在不同架构下的行为差异。")
    body(doc, "项目的具体目标有四项：第一，建立统一的数据模型与索引体系，使 50 种图书、30 名读者、3000 条借阅流水"
              "可以在同一套代码下被检索、统计与维护；第二，实现可运行、可复现的命令行程序，菜单覆盖增删改查、"
              "聚合统计、文件存取与操作审计；第三，通过副本集验证故障转移期间业务的真实损失，通过分片集群验证"
              "数据在物理分片上的分布与查询路由；第四，把每一步的命令、输出与结论留存为可核查的过程记录。")
    heading(doc, "1.2　交付物与任务映射", 2)
    body(doc, "课程任务书列出 7 项任务（F1—F11 共 11 个功能点）。本项目按任务顺序推进，交付物与任务的对应关系为："
              "7 个 Python 源文件与 8 个工具脚本对应 F1、F2；单机实例（端口 27017，开启认证）与三份数据文件导入对应 F3；"
              "11 项检索统计、索引优化对比与三账号权限验证对应 F4、F5、F6；21 项菜单程序、GridFS 存取与操作日志对应 F7、F8；"
              "三节点副本集 rsLib 与两轮故障转移演练对应 F9、F10；配置服务器、两个分片与 mongos 组成的分片集群对应 F11。"
              "全部执行过程分别记录在 records 目录下的 10 份文本记录中，并整理为 46 张截图（附录 A）。"
              "其中程序演示在开启认证的单机实例上以 lib_rw 账号完整跑通 21 项菜单，"
              "证明“账号口令认证 + 统一连接模块”的组合可在业务层面稳定运行。")
    heading(doc, "1.3　运行环境", 2)
    body(doc, "实验环境为 Windows 11 上的单机多实例部署：MongoDB 8.0.4 服务端（mongod、mongos 二进制位于 D 盘独立目录），"
              "Python 3.11 与 pymongo 4.19.0 作为客户端。所有实例共用一份 keyfile 做内部认证，客户端则以账号口令认证。"
              "项目不使用 mongosh 做数据操作，导入、建索引、演练与验证全部由 Python 脚本通过 pymongo 驱动完成，"
              "以保证过程可重复、结果可保存。程序通过环境变量 LIB_CONFIG 指定配置文件，从而在单机、副本集、"
              "分片集群三种目标之间切换，源代码不做任何硬编码改动。")

    # ============ 2 技术选型论证 ============
    heading(doc, "2　技术选型论证", 1)
    heading(doc, "2.1　业务数据的三个特征", 2)
    body(doc, "选型的第一依据是数据形态，而不是流行度。本平台的数据呈现三个特征。其一是结构不齐：图书文档中，"
              "标签（tags）字段在 4 本书中缺失，读者文档中收藏偏好（fav_categories）在 2 名读者中缺失，"
              "若用关系表存储，这些位置只能留空值，统计时还要额外过滤。其二是写入持续、读取集中：3000 条借阅流水"
              "按借阅日期分布在 2023—2025 三年，日常查询集中在“某读者某段时间借了什么”，而全量聚合（按学院、按年月、"
              "按类别）也需要在同一集合上完成。其三是资源体积差异大：封面图 15～26 KB、电子书 37～40 KB，"
              "数量少但体积远大于结构化字段，与结构化数据混存会拖慢热数据的读写。")
    heading(doc, "2.2　与关系型数据库的比较", 2)
    body(doc, "把三类数据放进 MySQL 这类关系库并非不可行，但需要在建表、关联与文件处理上付出额外成本。"
              "表 1 从五个维度对比两种方案在本项目中的实际差异。")
    caption(doc, "表 1　MongoDB 与关系型数据库在本项目中的对比")
    make_table(doc,
               ["对比维度", "关系型数据库（以 MySQL 为例）", "MongoDB 文档数据库"],
               [["数据结构", "需为 tags、fav_categories 建从表，或留空值", "内嵌数组，缺失即不存该字段"],
                ["借阅流水", "单表按月分区或拆表，归档需人工维护", "时间序列集合按时间自动分桶，自动过期"],
                ["聚合统计", "GROUP BY 多表连接，索引受连接方式限制", "$group、$lookup、$unwind 在集合内完成"],
                ["文件存储", "文件落磁盘、库里只存路径，一致性靠应用保证", "GridFS 把文件切块入库，与元数据同库"],
                ["水平扩展", "分库分表需中间件，跨库连接困难", "原生分片，mongos 自动路由与归并"]],
               widths=[3.0, 6.2, 6.2],
               aligns=[WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT])
    body(doc, "对比可知，关系型方案的优势在强事务与固定报表，而本项目没有跨表强事务需求，主要负载是"
              "“单集合内多条件检索 + 聚合 + 少量文件存取”，文档模型与之更贴合。")
    heading(doc, "2.3　与其它 NoSQL 产品的比较", 2)
    body(doc, "NoSQL 内部也存在明显分工：键值库擅长大并发简单读写，列族库擅长超大规模稀疏表，搜索引擎擅长全文检索，"
              "而本平台的负载是“多字段组合过滤 + 聚合 + 二级索引”，属于文档数据库的典型场景。表 2 给出对比。")
    caption(doc, "表 2　候选 NoSQL 方案对比")
    make_table(doc,
               ["方案", "数据模型", "本项目的适配点", "不适配之处"],
               [["Redis", "键值 / 内存", "读性能极高", "无二级索引与聚合，3000 条流水需全量载入内存"],
                ["HBase", "列族 / 稀疏表", "海量写入、水平扩展强", "无二级索引，按类别、评分等条件过滤需全表扫描"],
                ["Elasticsearch", "倒排索引", "全文检索与聚合强", "非权威存储，需与主库同步，运维成本高"],
                ["MongoDB", "文档 / BSON", "多字段索引、聚合管线、GridFS、原生分片", "跨文档强事务能力弱于关系库"]],
               widths=[2.6, 3.3, 5.6, 5.0],
               aligns=[WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT,
                       WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT])
    body(doc, "结合前两节，本项目选择 MongoDB 8.0.4：它的文档模型容纳了结构不齐的图书与读者数据，"
              "时间序列集合直接对应借阅流水的写入与聚合模式，GridFS 解决文件与元数据同库的问题，"
              "副本集与分片集群又能让同一份数据平滑地从单机扩展到高可用与水平分片，正好覆盖课程要求的三级架构。")
    heading(doc, "2.4　面向非技术读者的说明", 2)
    body(doc, "如果把平台比作一座图书馆，关系型数据库像一本装订死的总账，每页格式必须一致；"
              "MongoDB 像一叠可伸缩的卡片，每张卡片只写自己有的信息。借阅流水是不断加页的流水账，"
              "系统按时段自动打包；电子书这类大文件则被打成标准小块入库，取用时按块拼回，保证与原件一模一样。"
              "当一本书被很多读者借阅、访问压力变大时，可以把卡片分到两个书架同时服务，前台仍只看到一个目录。")

    # ============ 3 数据模型设计 ============
    heading(doc, "3　数据模型设计", 1)
    heading(doc, "3.1　数据库与集合结构", 2)
    body(doc, "数据库名为 smart_library，共 5 个业务集合。books 与 readers 为普通集合；borrow_logs 为时间序列集合，"
              "其物理存储落在 system.buckets.borrow_logs 桶集合中；audit_logs 记录程序操作；"
              "category_stats 保存分类统计的落库结果。三类数据之间用 ISBN 与借阅证号关联，"
              "不建立外键，关联在聚合管线中用 $lookup 完成。表 3 列出各集合的主要字段与类型。")
    caption(doc, "表 3　主要集合与字段")
    make_table(doc,
               ["集合", "类型", "主要字段（类型）", "文档数"],
               [["books", "普通集合", "isbn(string)、title(string)、author(string)、category(string)、price(double)、"
                                     "stock(int)、rating(double)、tags(array)、location(string)、borrow_count(int)", "50"],
                ["readers", "普通集合", "card_no(string)、name(string)、college(string)、level(string)、"
                                       "fav_categories(array)、register_date(date)", "30"],
                ["borrow_logs", "时间序列集合", "reader_card(string，timeField)、borrow_date(date，metaField)、"
                                             "book_isbn(string)、status(string)", "3000"],
                ["audit_logs", "普通集合", "ts(date)、action(string)、target(string)、operator(string)、detail(object)", "运行期累计"],
                ["category_stats", "普通集合", "category(string)、count(int)、avg_price(double)、avg_rating(double)", "6"]],
               widths=[2.4, 2.4, 9.4, 1.6],
               aligns=[WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER,
                       WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER])
    heading(doc, "3.2　books 与 readers：内嵌而非拆表", 2)
    body(doc, "一本书的标签数量不定，按关系型做法需建 book_tags 从表再做连接；本项目把 tags 直接存为字符串数组，"
              "并为该字段建多键索引，使“同时含多个标签”的查询可以用 $all 一次完成。读者同理，"
              "fav_categories 以数组内嵌。缺失字段不写空值，统计时用 $exists 判定即可，"
              "这正好支撑了第 4 章的“数据质量核查”功能——实际查出 4 本书无 tags、2 名读者无收藏偏好。")
    heading(doc, "3.3　borrow_logs：选用时间序列集合的理由", 2)
    body(doc, "借阅流水是典型的时序数据：只有一个时间点、一个维度（读者证号）和若干测量值，写入只追加，查询集中在时间区间与维度过滤。"
              "时间序列集合把同一维度、相邻时间的多条测量值压进一个“桶”，桶内用 control.min/control.max 记录各列极值，"
              "区间查询只读少量桶。实测 3000 条流水被压缩为 1020 个桶，每桶 3 条测量值；查询 R20240005 时读取 100 条记录仅扫描 34 个文档。")
    body(doc, "代价也须写明：时间序列集合不支持 explain，直连分片时不能按普通集合统计视图；"
              "在分片集群中分片键只能是 metaField，且 chunk 元数据落在桶集合上。这些限制在第 7 章单独讨论。")
    heading(doc, "3.4　audit_logs：自行设计的审计字段", 2)
    body(doc, "审计日志没有照搬通用日志表，而是按本平台的操作特点设计了 5 个字段：ts（发生时间，建降序索引，"
              "保证“最近 100 条”查询走索引而不排序）、action（操作类型，如 insert_book、borrow、export_csv，"
              "与 ts 组成复合索引以支持按类型回溯）、target（操作对象，图书 ISBN 或读者证号）、"
              "operator（执行账号，用于区分 lib_rw 与 lib_admin 的行为）、detail（自由结构，保存受影响文档的摘要）。"
              "detail 采用对象而非字符串，使后续可按字段检索；同时刻意不把整条业务文档写进日志，避免日志膨胀。")
    heading(doc, "3.5　五条设计决策", 2)
    for i, txt in enumerate([
        "以 ISBN 作为图书的业务主键并建唯一索引，_id 仍用 ObjectId，避免业务主键变更影响引用。",
        "借阅流水的分片键与查询主路径一致，均以读者证号为入口，使“读者借阅记录”能定向到单一分片。",
        "状态字段用中文枚举（已归还、逾期、借出），排序与统计时以固定顺序呈现，便于非技术用户核对。",
        "统计结果单独落库到 category_stats 并建唯一索引，避免每次打开报表都重算 3000 条流水。",
        "所有脚本从配置文件读取连接串与库名，路径由脚本自身位置推导，保证换机器后无需改代码。",
    ], 1):
        body(doc, "%d）%s" % (i, txt), indent=True)
    heading(doc, "3.6　索引设计", 2)
    body(doc, "索引按“查询模式驱动”而非“字段全建”。books 建 8 个索引（含 ISBN 唯一索引、类别+价格复合索引、"
              "标签多键索引、评分与借阅次数的降序索引）；readers 建 4 个；borrow_logs 建 4 个"
              "（其中 reader_card+borrow_date 复合索引由时间序列集合自动创建）；audit_logs 建 2 个；"
              "category_stats 建 1 个唯一索引。表 4 为完整清单（记录文件：任务三_索引清单.txt）。")
    caption(doc, "表 4　索引清单")
    make_table(doc,
               ["集合", "索引名（键与顺序）", "唯一"],
               [["books", "uk_isbn（isbn:1）", "是"],
                ["books", "idx_category_price（category:1, price:1）", "否"],
                ["books", "idx_tags（tags:1，多键）", "否"],
                ["books", "idx_title / idx_publish_date / idx_rating_desc / idx_borrow_count_desc", "否"],
                ["readers", "uk_card_no（card_no:1）", "是"],
                ["readers", "idx_college / idx_level / idx_fav_categories", "否"],
                ["borrow_logs", "reader_card_1_borrow_date_1（自动）/ idx_book_isbn / idx_status", "否"],
                ["audit_logs / category_stats", "idx_ts_desc、idx_action_ts / uk_category", "否 / 是"]],
               widths=[3.0, 11.4, 1.6],
               aligns=[WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT,
                       WD_ALIGN_PARAGRAPH.CENTER])

    # ============ 4 功能实现 ============
    heading(doc, "4　功能实现", 1)
    heading(doc, "4.1　程序结构与统一连接模块", 2)
    body(doc, "源代码共 9 个文件，按职责分层：config.py 负责读取配置与环境变量 LIB_CONFIG；db.py 是唯一的连接入口，"
              "封装 MongoClient 的创建、认证库选择、读取偏好设置与集合句柄获取；books.py、readers.py、borrow.py、"
              "stats.py、files.py、audit.py 各承担一类业务；main.py 提供 21 项菜单。所有业务模块只调用 db.py 暴露的句柄，"
              "不自行拼连接串，因此同一份代码可以在单机、副本集、分片集群之间切换目标——只需换配置文件。"
              "图 1 为程序启动后的主菜单。")
    picture(doc, os.path.join("任务四", "任务四_01_主菜单.png"), "图 1　命令行程序主菜单（21 项功能）")
    heading(doc, "4.2　检索与统计功能", 2)
    body(doc, "共实现 11 项检索与统计，覆盖等值、范围、多选、模糊、缺失值核查、排序投影、分组聚合与关联查询八种模式。"
              "表 5 列出功能要点与实测返回结果（记录文件：任务三_检索与统计执行记录.txt）。")
    caption(doc, "表 5　11 项检索与统计功能")
    make_table(doc,
               ["序号", "功能", "关键操作符", "实测结果"],
               [["1", "类别 + 价格区间筛选", "$and、$gte、$lte", "按类别与区间精确命中"],
                ["2", "标签多选匹配", "$all", "同时含多个标签的图书"],
                ["3", "书名模糊检索", "$regex（不区分大小写）", "命中同名或含关键词图书"],
                ["4", "出版年份范围", "$gte、$lte（日期比较）", "2019—2022 年图书"],
                ["5", "缺 tags 数据核查", "$exists: false", "4 本无标签图书"],
                ["6", "评分排序取前 10", "sort + projection", "只返回书名、作者、评分"],
                ["7", "分类藏书统计", "$group、$avg", "6 类，均价 89.53 / 47.02 / 90.86 / 40.67 / 59.00 / 95.60 元"],
                ["8", "学院借阅 Top5", "$lookup、$group、$sort", "计算机 500、经济管理 500、另三类各 400"],
                ["9", "年月借阅趋势", "$year、$month、$group", "2023—2025 年分别 1002 / 1005 / 993 条"],
                ["10", "借阅排行 Top10", "$sort、$lookup 馆藏位置", "Top10 含馆藏位置"],
                ["11", "分类统计落库", "$out / 批量写入 + 唯一索引", "category_stats 写入 6 条"]],
               widths=[1.2, 4.4, 5.2, 5.6],
               aligns=[WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.LEFT,
                       WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT])
    body(doc, "此外还对借阅状态做了分布统计，得到已归还 2142 条、逾期 429 条、借出 429 条，与 3000 条总量吻合，"
              "说明导入阶段没有丢行或重复写。")
    heading(doc, "4.3　索引优化前后对比", 2)
    body(doc, "为验证索引的实际收益，设计四条基准查询：Q1 按类别+价格区间（走复合索引）、Q2 按标签多选（走多键索引）、"
              "Q3 按评分排序（走降序索引）、Q4 按借阅日期区间（走时序集合的自动索引）。先在真实数据集上测 300 次，"
              "再构造放大集（books_bench 5 万条、borrow_bench 30 万条）复测，测完即删除放大集，正式库不受影响。"
              "表 6 给出放大集上的结果（记录文件：任务三_索引优化对比.txt）。")
    caption(doc, "表 6　索引优化前后耗时对比（放大集，5 万图书 / 30 万流水）")
    make_table(doc,
               ["查询", "优化前 / ms", "优化后 / ms", "提升倍数", "说明"],
               [["Q1 类别+价格", "23.541", "11.335", "2.08", "复合索引承担范围过滤"],
                ["Q2 标签多选", "26.366", "0.573", "46.03", "多键索引替代全表扫描"],
                ["Q3 评分排序", "15.894", "0.465", "34.20", "降序索引避免内存排序"],
                ["Q4 日期区间", "—", "—", "—", "时间序列集合上测不出 stage 与 docsExamined"]],
               widths=[3.0, 3.0, 3.0, 2.4, 5.6],
               aligns=[WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.RIGHT,
                       WD_ALIGN_PARAGRAPH.RIGHT, WD_ALIGN_PARAGRAPH.RIGHT, WD_ALIGN_PARAGRAPH.LEFT])
    body(doc, "真实数据集上因只有 50 本书，索引开销与全表扫描接近，Q1 甚至由 0.400 ms 变为 0.658 ms，Q3 仅提升 1.22 倍；"
              "放大集才能反映索引的真实价值。这说明小数据量下的性能结论不可外推，基准测试必须让规模与索引选择性相匹配。"
              "Q4 的空缺源于时间序列集合不支持 explain，已在第 7 章记录。")
    heading(doc, "4.4　账号与权限验证", 2)
    body(doc, "权限设计遵循最小权限：lib_ro 只有 read，供报表与查询；lib_rw 有 readWrite，供日常业务写入；"
              "lib_admin 有 dbOwner，供建索引用。三账号的 authSource 均为 smart_library。"
              "验证时对同一批操作分别在三个账号下执行，记录“允许”与“拒绝”。表 7 为结果（记录文件：任务三_账号与权限验证.txt）。")
    caption(doc, "表 7　三账号权限验证结果")
    make_table(doc,
               ["操作", "lib_ro（read）", "lib_rw（readWrite）", "lib_admin（dbOwner）"],
               [["查询 / 聚合", "允许", "允许", "允许"],
                ["插入、删除图书", "拒绝（4 项写入全拒）", "允许", "允许"],
                ["写审计日志", "拒绝", "允许", "允许"],
                ["createIndex / dropIndex", "拒绝", "允许", "允许"],
                ["collMod（改校验规则）", "拒绝", "拒绝", "允许"],
                ["createRole / dropDatabase", "拒绝", "拒绝", "允许"],
                ["建集合 / 删集合", "拒绝", "—", "允许"]],
               widths=[4.6, 4.8, 4.8, 4.0],
               aligns=[WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER,
                       WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER])
    body(doc, "验证中出现一项与预期相反的结果：readWrite 角色实测允许 createIndex 与 dropIndex，"
              "原因是二者属于集合级维护权限，已包含在 readWrite 内置角色中。这条经验列入第 7 章，也说明权限预期必须以实测为准。")
    heading(doc, "4.5　操作日志与结果导出", 2)
    body(doc, "程序在新增、删除、借还、导出等写操作后向 audit_logs 追加一条记录，菜单 20 可回看最近 100 条。"
              "统计结果除在终端展示外，菜单 21 会把分类统计导出为 CSV（exports\\category_stats.csv，6 行），"
              "供不熟悉数据库的使用者用表格软件查看。日志与导出同样经由 db.py 的连接句柄，"
              "因此在副本集或分片集群上运行时无需改代码。")

    # ============ 5 文件存储 ============
    heading(doc, "5　文件存储（GridFS）", 1)
    heading(doc, "5.1　存储机制", 2)
    body(doc, "MongoDB 单个文档上限 16 MB，电子书与封面图虽在 40 KB 以内，但为统一处理，项目采用 GridFS。"
              "GridFS 在 fs 桶下建两个集合：fs.files 保存文件名、长度、块大小、上传时间与自定义元数据；"
              "fs.chunks 按 255 KB 分块保存二进制。读取时按 files 中的块大小顺序拼回，因此“下载后字节数一致”"
              "是判断存取是否正确的最直接指标。")
    heading(doc, "5.2　上传与下载校验", 2)
    body(doc, "上传按 files_manifest.txt 建立 ISBN 关联：3 本电子书（39837、38524、37004 字节）分别对应 "
              "9787115428028、9787121362726、9787115546081；3 张封面图（23611、26053、15171 字节）按同样规则入库。"
              "上传完成后 fs.files 与 fs.chunks 各 6 条。下载校验时按书名反查 ISBN，再按文件 id 写入 downloads 目录，"
              "并与源文件逐字节比对：ebook_1.pdf 与 cover_1.png 的长度和内容完全一致（记录文件：任务四_GridFS执行记录.txt）。")
    heading(doc, "5.3　与“磁盘路径 + 数据库存路径”方案的取舍", 2)
    body(doc, "把文件放磁盘、库里只存路径是常见做法，优点是数据库体积小、可直接用系统工具查看；"
              "缺点是文件与元数据可能不一致——删了库记录而文件残留，或迁移时漏拷目录。GridFS 把两者放进同一副本集、"
              "同一分片，备份与恢复天然一致，代价是数据库体积增大、读取多一次拼装。本项目文件总量不足 200 KB，"
              "一致性收益大于体积代价，故选择 GridFS。")

    # ============ 6 架构演进 ============
    heading(doc, "6　架构演进：单机、副本集与分片集群", 1)
    heading(doc, "6.1　从单机到三节点副本集", 2)
    body(doc, "单机实例运行在 27017，开启 --auth，承担第 3—5 章的全部功能验证。为消除单点故障，"
              "在同一台机器上以三个端口搭建副本集 rsLib：27021（priority 2）、27022（priority 1）、27023（priority 1），"
              "三节点共用 deploy\\keyfile 做内部认证，客户端仍以 root 账号登录。副本集初始化后导入同一批数据并重建索引，"
              "核对 books 50、readers 30、borrow_logs 3000 与单机一致。")
    body(doc, "读取偏好验证是副本集的特有能力：primary 读取始终落在主节点；secondaryPreferred 在主节点可用时仍读主，"
              "主节点不可用时自动转向从节点；secondary 强制读从节点，若从节点落后会读到稍旧的数据。"
              "项目分别用三种偏好对同一查询取样，确认了上述行为，也为故障转移期间的降级读取提供了依据。")
    heading(doc, "6.2　故障转移演练与业务影响", 2)
    body(doc, "演练分两轮。第一轮用一次性脚本执行：17:47:00.949 对主节点 27021（PID 244984）执行 taskkill，"
              "11.6 s 后 27023 被选为主；17:47:15.567 重启 27021，3.7 s 后它以从节点身份加入。"
              "同期的业务探针以每秒一次的频率执行读写信封操作，共 54 次，失败 3 次，成功率 94.4%，"
              "首次失败发生在 17:47:05.458（AutoReconnect），最后一次在 17:47:12.519（ServerSelectionTimeout），"
              "业务中断约 7.3 s。第二轮改用分步命令复演，逐段留证：17:53:05.594 终止 27021（PID 246508），"
              "17:53:22.375 观测到 27023 成为 PRIMARY（宕机后 17.4 s），重启后 27021 于 17:53:45.620 完成 oplog 截断恢复，"
              "17:53:56.319 因 priority 更高重新当选主。表 8 汇总两轮数据（记录文件：任务五_副本集部署与故障转移记录.txt）。")
    caption(doc, "表 8　两轮故障转移实测数据")
    make_table(doc,
               ["项目", "第一轮（一次性脚本）", "第二轮（分步复演）"],
               [["终止主节点时刻", "17:47:00.949", "17:53:05.594"],
                ["新主产生时间", "约 11.6 s 后（27023）", "17:53:22.375（宕机后 17.4 s，27023）"],
                ["原主节点回归", "17:47:15.567 重启，3.7 s 后为 SECONDARY", "17:53:45.620 完成 oplog 截断恢复"],
                ["是否重新当选主", "否（未抢回）", "是，17:53:56.319 因 priority=2 重新当选"],
                ["业务探针", "54 次，失败 3 次，成功率 94.4%", "分段观测，写入恢复后自动重连"],
                ["业务中断时长", "约 7.3 s", "约 17.4 s（含观测间隔）"],
                ["失败类型", "AutoReconnect 1 次、ServerSelectionTimeout 2 次", "—"]],
               widths=[3.8, 6.6, 6.6],
               aligns=[WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT])
    body(doc, "两轮差异说明：第一轮探针间隔短、客户端重试策略生效，中断被压缩到 7.3 s；"
              "第二轮的“17.4 s”包含人工分步操作的等待，不代表副本集自身选主耗时。因此报告结论以第一轮为准，"
              "第二轮用于补齐角色变化的时间线证据。业务影响方面，写入在选主窗口内失败、读取可切到从节点，"
              "对借还书这类强一致操作需在应用层加重试与幂等；本平台程序已启用 retryWrites，"
              "探针中的 3 次失败均发生在连接重建期，未产生脏数据（执行输出见任务五记录与截图）。")
    heading(doc, "6.3　节点增加与移除", 2)
    body(doc, "为验证副本集的横向伸缩，演练加入第四节点 27024：先建 db/rs3 目录（首次启动因目录缺失报 FileNotOpen），"
              "再以 replSetReconfig 把配置版本由 1 提到 2、追加 _id=3 的成员；27024 完成初始同步后成为 SECONDARY，"
              "拓扑为 1 主 3 从。移除时再次 reconfig，版本 2→3→4 后成员被摘除并终止进程，拓扑回到 1 主 2 从。"
              "该演练确认了副本集成员变更不需要停机，也暴露了“日志目录必须预先创建”这一易错点。")
    heading(doc, "6.4　分片集群部署", 2)
    body(doc, "分片集群由四部分组成：配置服务器副本集 csrs（27019，单成员）、两个分片 shard1（27031）与 shard2（27032，"
              "各为单成员副本集）、路由 mongos（27101）。三个 mongod 与 mongos 共用同一 keyfile 并开启 authorization，"
              "root 账号建于 admin 库。mongos 注册两个分片后，先对 smart_library 执行 enableSharding，"
              "再对 borrow_logs 执行 shardCollection，按分片键预切分并迁移 chunk，完成后再导入数据。"
              "完整端口分配与启动顺序见 deploy\\端口与启动说明.txt 与附录 B。")
    body(doc, "导入完成后经 mongos 统计三集合数量与源文件一致（50 / 30 / 3000）。直连两个分片统计桶集合，"
              "shard1 持 510 个桶、1500 条，借阅证 R20240001—R20240015；shard2 同样 510 个桶、1500 条，"
              "借阅证 R20240016—R20240030，两片之和与 mongos 统计一致，证明数据确实分布在两个分片且基本均匀。"
              "图 2 为分片键与 chunk 分布的验证输出。")
    picture(doc, os.path.join("任务六", "任务六_03_分片键与chunk.png"), "图 2　分片键、chunk 归属与两片数据量验证")
    heading(doc, "6.5　分片键选择论证", 2)
    body(doc, "分片键一经指定便难以更改，且直接决定写入分布与查询路由，因此需要系统论证。本平台的可选键受一个硬约束限制："
              "borrow_logs 是时间序列集合，MongoDB 规定其分片键只能是 metaField（即 borrow_date 之外的那个维度字段）"
              "或 metaField 的子字段，因此 book_isbn、status 等普通字段无法直接作为分片键，候选实际落在 reader_card 上；"
              "若改用 borrow_date，则属于“用时间做分片键”，会造成写入热点。以下按候选逐一对比。"
              "第一候选 reader_card：基数 30，取值 R20240001—R20240030 连续可用，分布均匀（每证 100 条，正好 3000 条），"
              "而平台的查询主路径是“某读者的借阅记录”，带该字段的查询可被路由到单一分片，命中率最高；"
              "写入方面，30 个证号的借阅分散在不同桶，写入压力被摊到两片，不会集中到某一段。"
              "第二候选 borrow_date（时间键）：优点是天然适合时间区间查询，缺点是所有新写入的借阅都落在最新时间桶，"
              "形成单点写入热点，且历史冷数据与热数据被强行拆开，迁移时需要按时间反复切分，运维成本高；"
              "本平台借阅量按年递增，时间键会让某一分片长期承担全部写入。第三候选 book_isbn：理论上也可作为 metaField，"
              "但 50 种图书的借阅量严重不均——热门图书的借阅次数远高于冷门书，按 ISBN 分片会产生“热点书集中在一片”的问题；"
              "同时平台的主要查询是读者维度，按 ISBN 分片无法服务主路径。第四种做法是哈希分片：把 reader_card 做哈希后分片，"
              "写入更均匀，但范围查询（如“R20240001 至 R20240010”这类前缀查询）将退化为广播，且预分片失去意义。"
              "综合基数、分布均匀度、与查询模式的一致性以及时间序列集合的约束，项目选择 reader_card 作为范围分片键，"
              "并在 R20240016 处预切分，使两片各持一半证号；实测两片各 1500 条、定向查询仅命中 shard1，证明该选择成立。"
              "若未来借阅证数量增长到万级，应重新评估基数与倾斜度，必要时改为 reader_card 的哈希分片并对历史数据归档。")
    heading(doc, "6.6　定向查询与跨分片查询", 2)
    body(doc, "分片键的价值最终体现在路由上。项目对三类查询各测 30 次并取平均：带分片键的定向查询（reader_card=R20240005）、"
              "按非分片键但有序索引的查询（book_isbn）、按无单字段索引的状态查询（status=逾期）。"
              "由于时间序列集合不支持 explain，归属判定改用分片侧 profiling（level=2）加 comment 标记："
              "只统计真正执行到存储引擎的 command 记录。结果显示，定向查询在 shard1 上记录到 60 条执行（含 getMore），"
              "shard2 为 0 条，确认只访问一个分片；两类跨分片查询在两个分片均有执行。表 9 与图 3 为对比结果。")
    caption(doc, "表 9　定向查询与跨分片查询对比（各测 30 次）")
    make_table(doc,
               ["查询", "过滤字段", "命中分片", "返回条数", "平均耗时 / ms"],
               [["定向查询", "reader_card（分片键）", "shard1（1 个）", "100", "1.91"],
                ["跨分片查询", "book_isbn（有索引）", "shard1 + shard2", "60", "4.30"],
                ["跨分片查询", "status（无单字段索引）", "shard1 + shard2", "200", "4.06"]],
               widths=[3.0, 5.6, 4.0, 2.4, 3.0],
               aligns=[WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT,
                       WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.RIGHT, WD_ALIGN_PARAGRAPH.RIGHT])
    body(doc, "定向查询比两类跨片查询快 2.13～2.25 倍。差距的成因不在单条记录的读取，而在 mongos 必须把请求广播到两个分片、"
              "等待两片返回后再归并排序；分片越多，归并成本越高。这也解释了为什么分片键应当与最频繁的查询模式一致——"
              "它决定了系统是在“一个分片上做一次查询”还是在“所有分片上做一次查询再合并”。")
    picture(doc, os.path.join("任务六", "任务六_04_定向vs跨片查询.png"), "图 3　定向查询与跨分片查询的归属与耗时对比")

    # ============ 7 问题与总结 ============
    heading(doc, "7　问题与总结", 1)
    heading(doc, "7.1　主要技术难点与解决", 2)
    body(doc, "实践过程并非一次成功，以下六个问题对结果影响最大，均已定位并解决，解决方式也固化进脚本：")
    body(doc, "1）URI 中的 @ 未转义导致 InvalidURI。账号口令为 Super@2025 时，连接串中的 @ 会被当作主机分隔符解析失败。"
              "解决方式是用 urllib.parse.quote_plus 对用户名与口令编码，统一在 config.py 中处理，业务代码不再拼接连接串。")
    body(doc, "2）readWrite 角色权限预期错误。原以为该角色不能建索引，实测允许 createIndex 与 dropIndex。"
              "修正结论后重新组织权限表，并在报告中如实记录这一差异，避免把错误预期写进结论。")
    body(doc, "3）时间序列集合不支持 explain，直连分片按视图统计不可靠。shard1 上 borrow_logs 曾有 510 个桶却返回 0 条文档，"
              "原因是时序视图在分片侧的可见性受 chunk 归属影响。解决方式是直连分片统计桶集合 system.buckets.borrow_logs，"
              "用 control.count 求和得到真实条数；查询归属改用 profiling + comment 标记，只统计 op=command 的记录。")
    body(doc, "4）先导入后分片造成桶归属混乱。首次部署时先导入 3000 条再执行 shardCollection，结果 shard1 持 1020 个桶却统计出 3000 条、"
              "shard2 统计为 0，迁移后总量对不上。改为“先建集合、先 shardCollection 与预分片、再导入”的标准顺序后问题消失，"
              "最终两片各 510 桶、1500 条。")
    body(doc, "5）mongod 不会自动创建日志目录，导致 FileNotOpen。加入第四节点时 db/rs3 目录不存在，mongod 启动即失败。"
              "解决方式是在启动脚本中先 os.makedirs 建目录，再拉起进程。")
    body(doc, "6）长时间前台任务被当作后台任务终止，演练记录丢失。第一轮演练因单条命令超时被系统转为后台任务，"
              "终止该任务时连带杀掉了带 mongod 子进程的会话。解决方式是把演练拆成 kill、watch、restart、sync、logs "
              "五条几秒内结束的分步命令，每步立即落盘，记录不再依赖单条长任务的存活。")
    heading(doc, "7.2　经验总结", 2)
    body(doc, "三点体会最为关键。其一，选型要看数据形态与查询模式，而不是看产品排名：本项目若用关系库，标签与偏好的缺失值、"
              "借阅流水的分区归档都要额外设计；若用键值库，二级索引与聚合又无处落地。其二，性能结论必须建立在匹配的数据规模上："
              "50 本书时索引优化甚至为负收益，5 万本时才显出 46 倍差距，基准测试的规模选择与结论同等重要。其三，"
              "演练要能留证：命令、时间点、角色变化、业务影响缺一不可，而可留证的前提是把长任务拆成短步骤、每步落盘。")
    heading(doc, "7.3　不足与改进方向", 2)
    body(doc, "本项目仍有三处不足。第一，分片集群的两个分片与配置服务器均为单成员副本集，虽然具备分片能力，"
              "但单个分片进程故障仍会导致该片不可用，生产环境应为每片配置三成员副本集。第二，Q4 查询在时间序列集合上"
              "无法用 explain 取证，只能以耗时对比间接说明，后续可用 mongosh 的 serverStatus 或慢查询日志补充证据。"
              "第三，图形化验收受运行环境限制，MongoDB Compass 未能在本机完成安装，界面化核对改用命令行与导出文件替代，"
              "若交付环境具备桌面，可补做 Compass 中的集合、索引、分片状态可视化核对。")

    # ============ 参考文献 ============
    heading(doc, "参考文献", 1)
    refs = [
        "[1] MongoDB Inc. MongoDB Manual: Time Series Collections[EB/OL]. [2026-11-09]. "
        "https://www.mongodb.com/docs/manual/core/timeseries-collections/.",
        "[2] MongoDB Inc. MongoDB Manual: Sharding[EB/OL]. [2026-11-09]. "
        "https://www.mongodb.com/docs/manual/sharding/.",
        "[3] MongoDB Inc. MongoDB Manual: Replication[EB/OL]. [2026-11-09]. "
        "https://www.mongodb.com/docs/manual/replication/.",
        "[4] MongoDB Inc. GridFS[EB/OL]. [2026-11-09]. https://www.mongodb.com/docs/manual/core/gridfs/.",
        "[5] PyMongo 4.19 Documentation[EB/OL]. [2026-11-09]. https://pymongo.readthedocs.io/en/stable/.",
        "[6] GB/T 7713.2—2022 学术论文编写规则[S]. 北京: 中国标准出版社, 2022.",
    ]
    for r in refs:
        p = doc.add_paragraph()
        p.paragraph_format.first_line_indent = Pt(0)
        p.paragraph_format.left_indent = Pt(21)
        p.paragraph_format.line_spacing = 1.0
        p.paragraph_format.space_after = Pt(3)
        run = p.add_run(r)
        set_run(run, size=10.5)

    # ============ 附录 A ============
    page_break(doc)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Pt(0)
    run = p.add_run("附录 A　过程记录与截图清单")
    set_run(run, size=12, cn=CN_HEAD, bold=True)
    body(doc, "全部过程记录保存在项目 records 目录，共 10 份文本记录；截图保存在 screenshots 目录，共 46 张，"
              "并按七个任务分为 任务一 至 任务七 七个子目录，清单见 records\\任务七_截图清单.txt。"
              "截图由程序把记录文件中的真实命令输出按原样渲染为终端截图，标题栏标注命令来源、页脚标注记录文件，"
              "内容未作改写。各任务的取证要点如下：任务一为实例状态与数据核对（3 张）；任务二为数据备份导出（1 张）；"
              "任务三为检索统计、索引清单与优化对比、三账号权限验证（9 张）；任务四为菜单功能、GridFS 与日志导出（17 张）；"
              "任务五为副本集启动、状态核对、读取偏好、两轮故障转移与节点增加（6 张）；"
              "任务六为分片集群启动、注册分片、chunk 分布、定向与跨片对比、集群认证（5 张）；"
              "任务七为五个统计图表与图形化验收说明（5 张）。")

    # ============ 附录 B ============
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Pt(0)
    run = p.add_run("附录 B　运行手册")
    set_run(run, size=12, cn=CN_HEAD, bold=True)
    body(doc, "1）准备环境：安装 MongoDB 8.0.x 与 Python 3.10+，执行 python -m pip install pymongo。")
    body(doc, "2）选择目标实例：设置环境变量 LIB_CONFIG 指向 config\\config.json（单机 27017）、config\\config_rs.json"
              "（副本集 rsLib）或 config\\config_shard.json（分片集群 mongos 27101），不设置时默认使用单机配置。")
    body(doc, "3）初始化数据：依次运行 src\\tools\\init_db.py（导入三份数据文件）、create_indexes.py（建索引）、"
              "create_users.py（建三账号）；分片集群需先运行 shard_setup.py 的 conf/start-all/init/mongos/shards 子命令，"
              "再运行 shard_ops.py 的 reset/shard/import 子命令。")
    body(doc, "4）运行程序：python src\\main.py 打开 21 项菜单；单独验证某功能可运行 src\\tools\\exec_functions.py。")
    body(doc, "5）账号与端口：root/Super@2025（admin）、lib_ro/Read@2025（read）、lib_rw/Write@2025（readWrite）、"
              "lib_admin/Admin@2025（dbOwner），业务账号的 authSource 为 smart_library；"
              "端口为 27017（单机）、27021/27022/27023（副本集）、27019（配置服务器）、27031/27032（分片）、27101（mongos），"
              "详见 deploy\\端口与启动说明.txt。")
    body(doc, "6）备份与恢复：python src\\tools\\backup_db.py dump 导出到 backups\\<库名>_<时间戳>\\，"
              "restore 子命令按 _manifest.json 恢复；恢复后需重跑 create_indexes.py。")

    doc.save(OUT)
    print("[生成] %s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(build())
