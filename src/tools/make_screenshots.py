"""把 records 里的真实执行输出渲染成终端截图（PNG），按七个任务分目录存放。

目录结构：screenshots\\任务一 ... 任务七\\
每张图标题栏标注命令来源，页脚标注对应记录文件，正文为原始输出，不做改写。
"""
import os
import sys
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REC = os.path.join(ROOT, "records")
OUT = os.path.join(ROOT, "screenshots")

MONO = "C:/Windows/Fonts/consola.ttf"
CJK = "C:/Windows/Fonts/msyh.ttc"
SIZE = 15
MONO_W = 8.6
CJK_W = 15.0
LINE_H = 21
PAD = 18
MAXW = 1180

# (任务目录, 文件名, 标题栏, 记录文件, 起始标记, 行数)
SPEC = [
    ("任务一", "01_单机实例状态", "python src\\tools\\status_report.py  —— 实例状态", "任务一_单机实例状态与数据核对.txt", "单机实例状态与数据核对", 14),
    ("任务一", "02_数据核对", "python src\\tools\\status_report.py  —— 集合与索引核对", "任务一_单机实例状态与数据核对.txt", "[集合与文档数]", 22),
    ("任务一", "03_项目目录结构", "项目目录与源文件清单", "任务七_目录结构.txt", "项目根目录结构", 40),

    ("任务二", "01_数据备份导出", "python src\\tools\\backup_db.py dump", "任务二_数据备份导出记录.txt", "数据备份导出", 14),

    ("任务三", "01_检索1组合筛选", "检索 1：类别 + 价格区间组合筛选", "任务三_检索与统计执行记录.txt", "[检索 1]", 9),
    ("任务三", "02_检索6排序投影", "检索 6：评分排序取前 10（只返回书名/作者/评分）", "任务三_检索与统计执行记录.txt", "[检索 6]", 14),
    ("任务三", "03_统计3趋势", "统计 3：按年月统计借阅趋势（可读标签）", "任务三_检索与统计执行记录.txt", "[统计 3]", 40),
    ("任务三", "04_统计5落库", "统计 5：分类统计结果写入集合 category_stats", "任务三_检索与统计执行记录.txt", "[统计 5]", 10),
    ("任务三", "05_索引清单", "索引清单：books / readers / borrow_logs / audit_logs", "任务三_索引清单.txt", "[索引清单]", 40),
    ("任务三", "06_索引优化对比", "索引优化前后对比（放大集：5 万书 / 30 万流水）", "任务三_索引优化对比.txt", "[放大数据集]", 22),
    ("任务三", "07_权限_只读账号", "权限验证：lib_ro（read 角色，写入全被拒）", "任务三_账号与权限验证.txt", "[lib_ro 只读账号]", 12),
    ("任务三", "08_权限_读写账号", "权限验证：lib_rw（readWrite 角色）", "任务三_账号与权限验证.txt", "[lib_rw 读写账号]", 15),
    ("任务三", "09_权限_管理账号", "权限验证：lib_admin（dbOwner 角色）", "任务三_账号与权限验证.txt", "[lib_admin 管理账号]", 9),

    ("任务四", "01_主菜单", "python src\\main.py  —— 主菜单（21 项功能）", "任务四_程序运行记录.txt", "智慧图书馆数字资源平台 —— 主菜单", 29),
    ("任务四", "02_图书列表分页", "菜单 1：图书列表（分页 + 排序）", "任务四_程序运行记录.txt", "# 执行功能：1 图书列表", 14),
    ("任务四", "03_组合检索", "菜单 2：按类别 + 价格区间检索", "任务四_程序运行记录.txt", "# 执行功能：2 按类别 + 价格区间", 18),
    ("任务四", "04_标签多选", "菜单 3：按标签多选检索（$all）", "任务四_程序运行记录.txt", "# 执行功能：3 按标签多选检索", 11),
    ("任务四", "05_书名模糊", "菜单 4：按书名模糊检索（正则）", "任务四_程序运行记录.txt", "# 执行功能：4 按书名模糊检索", 11),
    ("任务四", "06_数据质量核查", "菜单 6：缺 tags 字段的数据质量核查", "任务四_程序运行记录.txt", "# 执行功能：6 数据质量核查", 15),
    ("任务四", "07_评分Top10", "菜单 7：评分 Top10（投影 + 排序）", "任务四_程序运行记录.txt", "# 执行功能：7 评分 Top10", 18),
    ("任务四", "08_读者查询", "菜单 10：读者列表 / 等级检索", "任务四_程序运行记录.txt", "# 执行功能：10 读者列表", 20),
    ("任务四", "09_分类统计落库", "菜单 13：分类统计 + 写入 category_stats", "任务四_程序运行记录.txt", "# 执行功能：13 分类统计", 15),
    ("任务四", "10_学院借阅Top5", "菜单 14：学院借阅 Top5（$lookup 关联）", "任务四_程序运行记录.txt", "# 执行功能：14 学院借阅", 13),
    ("任务四", "11_月度趋势", "菜单 15：月度借阅趋势（$year/$month）", "任务四_程序运行记录.txt", "# 执行功能：15 月度借阅", 42),
    ("任务四", "12_借阅排行", "菜单 16：借阅排行 Top10 + 馆藏位置", "任务四_程序运行记录.txt", "# 执行功能：16 借阅排行", 18),
    ("任务四", "13_GridFS清单", "菜单 19：GridFS 文件清单（6 个文件）", "任务四_程序运行记录.txt", "# 执行功能：19 GridFS", 16),
    ("任务四", "14_下载字节校验", "菜单 18：按书名下载电子书并校验字节", "任务四_程序运行记录.txt", "# 执行功能：18 按书名下载", 12),
    ("任务四", "15_操作日志", "菜单 20：最近 100 条操作日志（audit_logs）", "任务四_程序运行记录.txt", "# 执行功能：20 最近 100 条操作日志", 18),
    ("任务四", "16_导出CSV", "菜单 21：导出统计结果 CSV", "任务四_程序运行记录.txt", "# 执行功能：21 导出统计结果", 14),
    ("任务四", "17_GridFS上传", "GridFS 上传：按 manifest 建立 ISBN 关联（6 个文件）", "任务四_GridFS执行记录.txt", "[上传]", 18),

    ("任务五", "01_副本集启动", "副本集 rsLib：启动三个节点（27021/27022/27023）", "任务五_副本集部署与故障转移记录.txt", "[步骤1] 启动三个节点", 24),
    ("任务五", "02_副本集状态", "副本集状态核对：1 主 2 从 + 心跳", "任务五_副本集部署与故障转移记录.txt", "[步骤6] 副本集状态核对", 18),
    ("任务五", "03_读取偏好", "读取偏好验证：primary / secondaryPreferred / secondary", "任务五_副本集部署与故障转移记录.txt", "[步骤7] 读取偏好验证", 42),
    ("任务五", "04_故障转移第一轮", "故障转移第一轮：主节点被打掉，27023 接管", "任务五_副本集部署与故障转移记录.txt", "[步骤8] 故障转移演练第一轮", 42),
    ("任务五", "05_故障转移时间线", "故障转移事件时间线（从 mongod 日志抽取）", "任务五_副本集部署与故障转移记录.txt", "[步骤10] 角色变化事件时间线", 42),
    ("任务五", "06_节点增加", "节点增加演练：加入第四节点 127.0.0.1:27024", "任务五_副本集部署与故障转移记录.txt", "[步骤11] 节点增加演练", 36),

    ("任务六", "01_分片集群启动", "分片集群：启动配置服务器与两个分片", "任务六_分片集群部署与验证记录.txt", "[步骤2] 启动配置服务器与两个分片", 15),
    ("任务六", "02_注册分片", "分片集群：向 mongos 注册两个分片", "任务六_分片集群部署与验证记录.txt", "[步骤5] 向 mongos 注册两个分片", 18),
    ("任务六", "03_分片键与chunk", "分片键 {reader_card:1} 与 chunk 分布", "任务六_分片集群部署与验证记录.txt", "[步骤12 重测]", 20),
    ("任务六", "04_定向vs跨片查询", "定向查询 vs 跨分片查询（profiling 归属 + 耗时）", "任务六_分片集群部署与验证记录.txt", "[步骤13 定稿]", 34),
    ("任务六", "05_集群认证", "集群访问控制验证：无凭据/错口令/正确凭据 + keyfile", "任务六_分片集群部署与验证记录.txt", "[步骤14] 集群访问控制验证", 16),
]


def load(name):
    with open(os.path.join(REC, name), "r", encoding="utf-8") as f:
        return f.read().splitlines()


def slice_text(lines, marker, count):
    start = None
    for i, line in enumerate(lines):
        if marker in line:
            start = i
            break
    if start is None:
        return None
    seg = lines[start:start + count]
    while seg and not seg[-1].strip():
        seg.pop()
    return seg


def text_width(s):
    return sum(CJK_W if ord(ch) > 127 else MONO_W for ch in s)


def wrap(s, limit):
    if text_width(s) <= limit:
        return [s]
    out, cur, w = [], "", 0.0
    for ch in s:
        cw = CJK_W if ord(ch) > 127 else MONO_W
        if w + cw > limit and cur:
            out.append(cur)
            cur, w = ch, cw
        else:
            cur += ch
            w += cw
    if cur:
        out.append(cur)
    return out


def render(lines_seg, title, footer, out_path):
    f_cjk = ImageFont.truetype(CJK, SIZE)
    f_mono = ImageFont.truetype(MONO, SIZE)
    limit = MAXW - 2 * PAD
    body = []
    for line in lines_seg:
        body.extend(wrap(line.rstrip(), limit))
    if not body:
        body = ["(空)"]
    h = 34 + len(body) * LINE_H + 30 + PAD
    img = Image.new("RGB", (MAXW, h), (12, 12, 12))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, MAXW, 34], fill=(45, 45, 48))
    d.rectangle([0, 33, MAXW, 34], fill=(70, 70, 70))
    d.text((16, 8), title, font=f_cjk, fill=(235, 235, 235))
    y = 34 + 12
    for line in body:
        x = PAD
        for ch in line:
            f = f_mono if ord(ch) < 128 else f_cjk
            d.text((x, y), ch, font=f, fill=(210, 210, 210))
            x += MONO_W if ord(ch) < 128 else CJK_W
        y += LINE_H
    d.line([0, h - 26, MAXW, h - 26], fill=(60, 60, 60))
    d.text((PAD, h - 20), footer, font=f_cjk, fill=(140, 140, 140))
    img.save(out_path)


def main():
    made, missing = [], []
    total = len(SPEC)
    for idx, (folder, name, title, srcfile, marker, count) in enumerate(SPEC, 1):
        lines = load(srcfile)
        seg = slice_text(lines, marker, count)
        if seg is None:
            missing.append((folder, name, srcfile, marker))
            continue
        outdir = os.path.join(OUT, folder)
        os.makedirs(outdir, exist_ok=True)
        out_path = os.path.join(outdir, "%s_%s.png" % (folder, name))
        footer = "%s｜%s  来源：records\\%s（真实输出，未改写）" % (folder, name, srcfile)
        render(seg, title, footer, out_path)
        made.append((folder, os.path.basename(out_path), title, srcfile, len(seg)))
        print("[生成] %s\\%s" % (folder, os.path.basename(out_path)))
    print("\n生成 %d 张，缺失 %d 张" % (len(made), len(missing)))
    for m in missing:
        print("  [缺失] %s" % (m,))

    manifest = os.path.join(REC, "任务七_截图清单.txt")
    with open(manifest, "w", encoding="utf-8") as f:
        f.write("任务七  截图清单（共 %d 张，按七个任务分目录）\n" % len(made))
        f.write("说明：本环境为远程命令行会话，无法调用桌面截图接口；以下截图由程序把 records 中的\n")
        f.write("      真实命令输出按原样渲染为终端窗口图片，标题栏标注命令来源，页脚标注记录文件。\n")
        f.write("=" * 78 + "\n")
        cur = None
        for n, (folder, fn, title, src, lines_n) in enumerate(made, 1):
            if folder != cur:
                f.write("\n[%s]\n" % folder)
                cur = folder
            f.write("  %02d  %-34s %s\n" % (n, fn, title))
    print("[清单] %s" % manifest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
