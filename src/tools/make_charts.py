"""生成验收用的统计图（浅色、留白、无边框风格），输出到 screenshots/charts。"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "screenshots", "charts")
if not os.path.isdir(OUT):
    os.makedirs(OUT)

font_manager.fontManager.addfont("C:/Windows/Fonts/msyh.ttc")
plt.rcParams["font.family"] = "Microsoft YaHei"
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.facecolor"] = "#FFFFFF"
plt.rcParams["axes.edgecolor"] = "#DDDDDD"
plt.rcParams["axes.labelcolor"] = "#333333"
plt.rcParams["xtick.color"] = "#555555"
plt.rcParams["ytick.color"] = "#555555"
plt.rcParams["text.color"] = "#333333"

BAR = "#7FA0AE"
BAR2 = "#C9D8DE"
ACCENT = "#B4674E"


def frame(ax):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.spines["left"].set_color("#DDDDDD")
    ax.spines["bottom"].set_color("#DDDDDD")
    ax.grid(axis="y", color="#F0F0F0", linewidth=0.8)
    ax.set_axisbelow(True)


def chart_category():
    cats = ["计算机", "文学", "经济管理", "数学", "外语", "历史"]
    vals = [15, 12, 7, 6, 5, 5]
    fig, ax = plt.subplots(figsize=(7.2, 3.6), dpi=200)
    bars = ax.barh(cats[::-1], vals[::-1], height=0.55, color=BAR)
    for b, v in zip(bars, vals[::-1]):
        ax.text(v + 0.4, b.get_y() + b.get_height() / 2, str(v),
                va="center", fontsize=9, color="#666666")
    ax.set_xlim(0, 18)
    ax.set_xlabel("藏书量 / 种")
    ax.set_title("六个类别的藏书量（共 50 种）", fontsize=11, loc="left")
    frame(ax)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "图表1_分类藏书量.png"))
    plt.close(fig)


def chart_trend():
    years = ["2023", "2024", "2025"]
    vals = [1002, 1005, 993]
    fig, ax = plt.subplots(figsize=(7.2, 3.6), dpi=200)
    ax.plot(years, vals, marker="o", color=BAR, linewidth=1.6, markersize=6)
    for x, y in zip(years, vals):
        ax.annotate(str(y), (x, y), textcoords="offset points", xytext=(0, 9),
                    ha="center", fontsize=9, color="#666666")
    ax.set_ylim(960, 1030)
    ax.set_ylabel("借阅流水 / 条")
    ax.set_title("2023—2025 年借阅流水（合计 3000 条）", fontsize=11, loc="left")
    frame(ax)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "图表2_年度借阅趋势.png"))
    plt.close(fig)


def chart_index():
    labels = ["Q1 类别+价格", "Q2 标签多选", "Q3 评分排序"]
    before = [23.541, 26.366, 15.894]
    after = [11.335, 0.573, 0.465]
    fig, ax = plt.subplots(figsize=(7.2, 3.8), dpi=200)
    x = range(len(labels))
    ax.bar([i - 0.18 for i in x], before, width=0.34, color=BAR2, label="优化前")
    ax.bar([i + 0.18 for i in x], after, width=0.34, color=BAR, label="优化后")
    for i in x:
        ax.text(i - 0.18, before[i] + 0.8, "%.2f" % before[i], ha="center", fontsize=8.5, color="#666666")
        ax.text(i + 0.18, after[i] + 0.8, "%.2f" % after[i], ha="center", fontsize=8.5, color="#666666")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontsize=9.5)
    ax.set_ylabel("30 次平均耗时 / ms")
    ax.set_ylim(0, 30)
    ax.set_title("索引优化前后耗时对比（放大集：5 万图书 / 30 万流水）", fontsize=11, loc="left")
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    frame(ax)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "图表3_索引优化对比.png"))
    plt.close(fig)


def chart_shards():
    shards = ["shard1\n27031", "shard2\n27032"]
    buckets = [510, 510]
    docs = [1500, 1500]
    fig, ax = plt.subplots(figsize=(7.2, 3.4), dpi=200)
    x = range(len(shards))
    ax.bar([i - 0.17 for i in x], buckets, width=0.32, color=BAR2, label="桶数量")
    ax.bar([i + 0.17 for i in x], docs, width=0.32, color=BAR, label="借阅流水条数")
    for i in x:
        ax.text(i - 0.17, buckets[i] + 30, str(buckets[i]), ha="center", fontsize=8.5, color="#666666")
        ax.text(i + 0.17, docs[i] + 30, str(docs[i]), ha="center", fontsize=8.5, color="#666666")
    ax.set_xticks(list(x))
    ax.set_xticklabels(shards, fontsize=9.5)
    ax.set_ylim(0, 1800)
    ax.set_title("borrow_logs 在两个分片上的分布（各 1500 条）", fontsize=11, loc="left")
    ax.legend(frameon=False, fontsize=9, loc="upper right")
    frame(ax)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "图表4_分片数据分布.png"))
    plt.close(fig)


def chart_failover():
    events = [
        ("主节点 27021 正常", 0.0, 0.0),
        ("taskkill 主节点", 0.0, 0.0),
    ]
    fig, ax = plt.subplots(figsize=(7.6, 2.6), dpi=200)
    t0, t1, t2, t3 = 0, 11.6, 15.3, 16.0
    ax.hlines(0.6, t0, t1, color=BAR, linewidth=6)
    ax.hlines(0.2, t1, t2, color=ACCENT, linewidth=6)
    ax.hlines(0.6, t2, t3, color=BAR, linewidth=6, alpha=0.5)
    ax.text(t1, 0.78, "0.949 s 终止 27021", fontsize=8.5, color="#666666")
    ax.text(t1 + 0.3, 0.06, "11.6 s 后 27023 升主", fontsize=8.5, color="#666666")
    ax.text(t3 - 1.5, 0.78, "15.567 s 重启 27021 → SECONDARY", fontsize=8.5, color="#666666")
    ax.set_yticks([])
    ax.set_xlim(-1, t3 + 2)
    ax.set_xlabel("故障转移经过时间 / s")
    ax.set_title("第一轮故障转移的角色变化与业务中断窗口", fontsize=11, loc="left")
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color("#DDDDDD")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "图表5_故障转移时间线.png"))
    plt.close(fig)


def main():
    chart_category()
    chart_trend()
    chart_index()
    chart_shards()
    chart_failover()
    for f in sorted(os.listdir(OUT)):
        print("[图表] %s" % f)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
