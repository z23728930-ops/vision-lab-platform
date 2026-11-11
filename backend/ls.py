import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np


def draw_node(ax, center, width, height, n_samples, class_ratio, main_label, sub_label, purity_val):
    """
    绘制决策树的单个节点。

    参数:
        ax (matplotlib.axes.Axes): 绘图的Axes对象。
        center (tuple): 节点中心的 (x, y) 坐标。
        width (float): 节点的宽度。
        height (float): 节点的高度。
        n_samples (int): 节点中的样本总数。
        class_ratio (float): Class 1 (蓝色) 的样本比例 (0到1之间)。
        main_label (str): 节点的主要标签 (例如 "Root Node")。
        sub_label (str): 节点的次要标签 (例如 "(High Impurity)")。
        purity_val (float): 节点的纯度值 (例如 Gini Impurity)。
    """
    x, y = center

    # 1. 绘制结点背景框 (颜色深浅代表主要类别的倾向)
    # class_ratio 是 class 1 (蓝色) 的比例. 0 = 全红, 1 = 全蓝, 0.5 = 混合

    # 定义纯红和纯蓝的基色 (略微去饱和，使其更柔和)
    light_red = np.array([1.0, 0.85, 0.85])  # 浅红色
    light_blue = np.array([0.85, 0.85, 1.0])  # 浅蓝色

    # 根据 class_ratio 在两种颜色之间进行线性插值
    bg_color_array = (1 - class_ratio) * light_red + class_ratio * light_blue
    bg_color = tuple(bg_color_array)

    rect = patches.FancyBboxPatch((x - width / 2, y - height / 2), width, height,
                                  boxstyle="round,pad=0.1",
                                  linewidth=1.5, edgecolor='gray', facecolor=bg_color,
                                  zorder=1)  # 确保背景在其他元素之下
    ax.add_patch(rect)

    # 2. 在结点内绘制代表样本的点 (展示纯度)
    n_class1 = int(n_samples * class_ratio)
    n_class0 = n_samples - n_class1

    # 随机生成点的位置，留出顶部和底部空间给标签和纯度条
    points_x = np.random.uniform(x - width / 2 + 0.1, x + width / 2 - 0.1, n_samples)
    points_y = np.random.uniform(y - height / 2 + 0.15, y + height / 2 - 0.35, n_samples)  # 调整范围

    # 绘制 Class 0 (红色圆点)
    ax.scatter(points_x[:n_class0], points_y[:n_class0], c='#d62728', s=30, alpha=0.8, edgecolors='white',
               linewidth=0.7, zorder=2)  # zorder确保点在背景之上
    # 绘制 Class 1 (蓝色方块)
    ax.scatter(points_x[n_class0:], points_y[n_class0:], c='#1f77b4', s=30, marker='s', alpha=0.8, edgecolors='white',
               linewidth=0.7, zorder=2)

    # 3. 标签
    ax.text(x, y + height / 2 - 0.1, main_label, ha='center', fontsize=13, fontweight='bold', zorder=3)
    ax.text(x, y + height / 2 - 0.25, sub_label, ha='center', fontsize=10, style='italic', color='dimgray', zorder=3)

    # 4. 绘制纯度条 (Gini Impurity 或 Entropy 的可视化)
    bar_x = x - width / 2 + 0.1
    bar_y = y - height / 2 + 0.08  # 略高于原始位置
    bar_w = width - 0.2
    bar_h = 0.08  # 略厚

    # 背景条
    ax.add_patch(patches.Rectangle((bar_x, bar_y), bar_w, bar_h, color='lightgray', ec='gray', linewidth=0.5, zorder=3))
    # 蓝色比例部分
    ax.add_patch(patches.Rectangle((bar_x, bar_y), bar_w * class_ratio, bar_h, color='#1f77b4', zorder=4))
    # 红色比例部分 (剩下的)
    ax.add_patch(
        patches.Rectangle((bar_x + bar_w * class_ratio, bar_y), bar_w * (1 - class_ratio), bar_h, color='#d62728',
                          zorder=4))

    ax.text(x, bar_y - 0.08, f"Impurity: {purity_val:.2f}", ha='center', fontsize=9, style='italic', color='gray',
            zorder=3)


def draw_decision_tree_viz():
    """
    绘制决策树划分的可视化示意图。
    """
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 8)
    ax.axis('off')  # 隐藏坐标轴

    # 结点参数
    w, h = 2.5, 2.0  # 节点略高，以便容纳更多内容
    samples = 60  # 增加样本数量，使节点内部更密集

    # --- 1. 父结点 (高杂质) ---
    # 50% 红, 50% 蓝. Gini = 0.5
    draw_node(ax, (5, 6), w, h, samples, 0.5, "Root Node", "(High Impurity)", 0.5)

    # --- 2. 划分箭头 ---
    # 使用直线箭头
    arrow_props = dict(arrowstyle="->", lw=3, color='#555555')

    # 左箭头
    # 起点在父节点下方，终点在左子节点上方
    ax.annotate("", xy=(2.8, 3.7), xytext=(4.5, 5.1), arrowprops=arrow_props)
    # 文本位置调整到箭头的中间，并计算合适的旋转角度
    ax.text(3.65, 4.4, "Feature X < 5", ha='center', fontsize=10, rotation=39,
            bbox=dict(facecolor='white', edgecolor='lightgray', boxstyle="round,pad=0.2", alpha=0.8))

    # 右箭头
    # 起点在父节点下方，终点在右子节点上方
    ax.annotate("", xy=(7.2, 3.7), xytext=(5.5, 5.1), arrowprops=arrow_props)
    # 文本位置调整到箭头的中间，并计算合适的旋转角度
    ax.text(6.35, 4.4, "Feature X >= 5", ha='center', fontsize=10, rotation=-39,
            bbox=dict(facecolor='white', edgecolor='lightgray', boxstyle="round,pad=0.2", alpha=0.8))

    # --- 3. 子结点 (低杂质/高纯度) ---

    # 左子结点: 主要是红色 (Class 0). 比如 90% 红.
    # Gini ≈ 1 - (0.9^2 + 0.1^2) = 0.18
    draw_node(ax, (2.5, 2.5), w, h, samples, 0.1, "Leaf Node A", "(High Purity - Red)", 0.18)

    # 右子结点: 主要是蓝色 (Class 1). 比如 90% 蓝.
    draw_node(ax, (7.5, 2.5), w, h, samples, 0.9, "Leaf Node B", "(High Purity - Blue)", 0.18)

    # 标题
    plt.title("Decision Tree Split: Information Gain Visualization", fontsize=16, y=0.95, fontweight='bold')

    # 添加一个清晰的图例，解释点类型
    legend_elements = [
        plt.Line2D([0], [0], marker='o', color='w', label='Class A (Red)',
                   markerfacecolor='#d62728', markersize=8, markeredgecolor='white', markeredgewidth=0.7),
        plt.Line2D([0], [0], marker='s', color='w', label='Class B (Blue)',
                   markerfacecolor='#1f77b4', markersize=8, markeredgecolor='white', markeredgewidth=0.7)
    ]
    ax.legend(handles=legend_elements, loc='upper center', bbox_to_anchor=(0.5, 0.05),
              ncol=2, frameon=False, fontsize=10)

    plt.tight_layout()
    plt.show()


# 运行绘图函数
if __name__ == "__main__":
    draw_decision_tree_viz()