import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import os

def setup_chinese_font():
    # 推荐使用思源黑体或微软雅黑等支持中文的字体
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS', 'sans-serif']
    plt.rcParams['axes.unicode_minus'] = False


def plot_pr_sensitivity_cn(csv_filepath=None, output_filename=None):
    """
    读取PR_scbc敏感性分析结果并绘制带中文标签的图表。
    """
    setup_chinese_font()

    # 设置文件路径
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    output_dir = os.path.join(project_root, "output")
    os.makedirs(output_dir, exist_ok=True)

    if csv_filepath is None:
        csv_filepath = os.path.join(output_dir, "pr_sensitivity_results.csv")
    elif not os.path.isabs(csv_filepath):
        csv_filepath = os.path.join(output_dir, csv_filepath)

    if output_filename is None:
        output_filename = os.path.join(output_dir, "pr_sensitivity_plot_cn.png")
    elif not os.path.isabs(output_filename):
        output_filename = os.path.join(output_dir, output_filename)

    try:
        df = pd.read_csv(csv_filepath)
        print(f"CSV文件的列名: {list(df.columns)}")
    except Exception as e:
        print(f"读取CSV文件失败: {e}")
        return

    # 支持英文列名的CSV，自动映射为中文标签
    col_map = {
        "PR_scbc": "主循环压比(PR_scbc)",
        "Total_Thermal_Efficiency_percent": "总热效率(%)",
        "SCBC_Net_Power_MW": "SCBC净功(MW)",
        "ORC_Net_Power_MW": "ORC净功(MW)"
    }
    # 如果是英文列名，重命名为中文
    if all(col in df.columns for col in col_map.keys()):
        df = df.rename(columns=col_map)

    required_columns = [
        "主循环压比(PR_scbc)", "总热效率(%)", "SCBC净功(MW)", "ORC净功(MW)"
    ]
    for col in required_columns:
        if col not in df.columns:
            print(f"错误：CSV文件中缺少必需的列 '{col}'。")
            return

    fig, ax1 = plt.subplots(figsize=(12, 7))
    x_data = df["主循环压比(PR_scbc)"]

    # 主Y轴 - 总热效率
    color_eff = 'tab:red'
    ax1.set_xlabel("主循环压比(PR_scbc)", fontsize=14)
    ax1.set_ylabel("效率 (%)", color=color_eff, fontsize=14)
    line1 = ax1.plot(x_data, df["总热效率(%)"], color=color_eff, marker='o', linestyle='-', label="总热效率(%)")
    
    # 标注总热效率最高点
    best_eff_idx = df["总热效率(%)"].idxmax()
    best_eff_pr = df.loc[best_eff_idx, "主循环压比(PR_scbc)"]
    best_eff = df.loc[best_eff_idx, "总热效率(%)"]
    ax1.annotate(f"最高热效率: {best_eff:.2f}%\n压比 = {best_eff_pr:.2f}", 
                 xy=(best_eff_pr, best_eff),
                 xytext=(20, -30), textcoords='offset points',
                 arrowprops=dict(arrowstyle="->", color=color_eff),
                 color=color_eff, fontsize=10)
    
    ax1.tick_params(axis='y', labelcolor=color_eff, labelsize=12)
    ax1.tick_params(axis='x', labelsize=12)

    # 次Y轴 - SCBC净功
    ax2 = ax1.twinx()
    color_scbc = 'tab:blue'
    ax2.set_ylabel("SCBC净功(MW)", color=color_scbc, fontsize=14)
    line2 = ax2.plot(x_data, df["SCBC净功(MW)"], color=color_scbc, marker='s', linestyle='--', label="SCBC净功(MW)")
    
    # 标注SCBC净功最高点
    best_scbc_idx = df["SCBC净功(MW)"].idxmax()
    best_scbc_pr = df.loc[best_scbc_idx, "主循环压比(PR_scbc)"]
    best_scbc = df.loc[best_scbc_idx, "SCBC净功(MW)"]
    ax2.annotate(f"最高SCBC净功: {best_scbc:.2f} MW\n压比 = {best_scbc_pr:.2f}", 
                 xy=(best_scbc_pr, best_scbc),
                 xytext=(-100, 20), textcoords='offset points',
                 arrowprops=dict(arrowstyle="->", color=color_scbc),
                 color=color_scbc, fontsize=10)
    
    ax2.tick_params(axis='y', labelcolor=color_scbc, labelsize=12)

    # 再次Y轴 - ORC净功
    ax3 = ax1.twinx()
    color_orc = 'tab:green'
    ax3.spines["right"].set_position(("outward", 60))
    ax3.set_ylabel("ORC净功(MW)", color=color_orc, fontsize=14)
    line3 = ax3.plot(x_data, df["ORC净功(MW)"], color=color_orc, marker='^', linestyle=':', label="ORC净功(MW)")
    
    # 标注ORC净功最高点
    best_orc_idx = df["ORC净功(MW)"].idxmax()
    best_orc_pr = df.loc[best_orc_idx, "主循环压比(PR_scbc)"]
    best_orc = df.loc[best_orc_idx, "ORC净功(MW)"]
    ax3.annotate(f"最高ORC净功: {best_orc:.2f} MW\n压比 = {best_orc_pr:.2f}", 
                 xy=(best_orc_pr, best_orc),
                 xytext=(20, 20), textcoords='offset points',
                 arrowprops=dict(arrowstyle="->", color=color_orc),
                 color=color_orc, fontsize=10)
    
    ax3.tick_params(axis='y', labelcolor=color_orc, labelsize=12)

    # 格式化Y轴
    ax1.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.2f'))
    ax2.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.2f'))
    ax3.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.2f'))

    # 标题和图例
    plt.title("主循环压比对联合循环性能的影响（三Y轴）", fontsize=16)
    lines = line1 + line2 + line3
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc='upper center', bbox_to_anchor=(0.5, -0.20), fancybox=True, shadow=True, ncol=3, fontsize=12)

    # 网格
    ax1.grid(True, linestyle='--', alpha=0.7)
    ax2.grid(True, linestyle='--', alpha=0.7, axis='y', color=color_scbc)
    ax3.grid(True, linestyle='--', alpha=0.7, axis='y', color=color_orc)

    fig.tight_layout(rect=[0, 0.1, 1, 0.95])

    try:
        plt.savefig(output_filename, dpi=300)
        print(f"中文标签图表已保存为 '{output_filename}'")
    except Exception as e:
        print(f"保存图表时发生错误: {e}")
    plt.show()

def plot_exergy_efficiency_cn(csv_filepath=None, output_filename=None):
    """
    生成与 pr_exergy_efficiency_plot.png 一致的火用效率分析图（中文标签）。
    """
    setup_chinese_font()
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    output_dir = os.path.join(project_root, "output")
    os.makedirs(output_dir, exist_ok=True)
    if csv_filepath is None:
        csv_filepath = os.path.join(output_dir, "pr_sensitivity_results.csv")
    elif not os.path.isabs(csv_filepath):
        csv_filepath = os.path.join(output_dir, csv_filepath)
    if output_filename is None:
        output_filename = os.path.join(output_dir, "pr_exergy_efficiency_plot_cn.png")
    elif not os.path.isabs(output_filename):
        output_filename = os.path.join(output_dir, output_filename)
    try:
        df = pd.read_csv(csv_filepath)
        print(f"CSV文件的列名: {list(df.columns)}")
    except Exception as e:
        print(f"读取CSV文件失败: {e}")
        return
    # 自动映射英文列名为中文
    col_map = {
        "PR_scbc": "主循环压比(PR_scbc)",
        "Total_Exergy_Efficiency_percent": "总火用效率(%)",
        "Carnot_Efficiency_percent": "卡诺效率(%)",
        "Exergy_Eff_to_Carnot_Ratio": "火用/卡诺比"
    }
    if all(col in df.columns for col in col_map.keys()):
        df = df.rename(columns=col_map)
    # 检查所需列
    required_columns = ["主循环压比(PR_scbc)", "总火用效率(%)", "卡诺效率(%)", "火用/卡诺比"]
    for col in required_columns:
        if col not in df.columns:
            print(f"错误：CSV文件中缺少必需的列 '{col}'。")
            return
    x_data = df["主循环压比(PR_scbc)"]
    fig, ax1 = plt.subplots(figsize=(12, 7))
    color_exergy = 'tab:purple'
    color_carnot = 'tab:orange'
    color_ratio = 'tab:green'
    # 主Y轴 - 总火用效率
    ax1.set_xlabel("主循环压比(PR_scbc)", fontsize=14)
    ax1.set_ylabel("效率 (%)", color=color_exergy, fontsize=14)
    line1 = ax1.plot(x_data, df["总火用效率(%)"], color=color_exergy, marker='o', linestyle='-', label="总火用效率(%)")
    # 卡诺效率
    line2 = ax1.plot(x_data, df["卡诺效率(%)"], color=color_carnot, linestyle='--', label="卡诺效率(%)")
    ax1.tick_params(axis='y', labelcolor=color_exergy, labelsize=12)
    ax1.tick_params(axis='x', labelsize=12)
    # 次Y轴 - 火用/卡诺比
    ax2 = ax1.twinx()
    ax2.set_ylabel("火用/卡诺比", color=color_ratio, fontsize=14)
    line3 = ax2.plot(x_data, df["火用/卡诺比"], color=color_ratio, marker='^', linestyle=':', label="火用/卡诺比")
    ax2.tick_params(axis='y', labelcolor=color_ratio, labelsize=12)
    # 格式化Y轴
    ax1.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.2f'))
    ax2.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.3f'))
    # 标题和图例
    plt.title("主循环压比对火用效率与卡诺效率的影响", fontsize=16)
    lines = line1 + line2 + line3
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc='upper center', bbox_to_anchor=(0.5, -0.15), fancybox=True, shadow=True, ncol=3, fontsize=12)
    ax1.grid(True, linestyle='--', alpha=0.7)
    ax2.grid(True, linestyle='--', alpha=0.7, axis='y', color=color_ratio)
    fig.tight_layout(rect=[0, 0.1, 1, 0.95])
    try:
        plt.savefig(output_filename, dpi=300)
        print(f"火用效率中文图表已保存为 '{output_filename}'")
    except Exception as e:
        print(f"保存图表时发生错误: {e}")
    plt.show()

if __name__ == "__main__":
    plot_pr_sensitivity_cn()
    plot_exergy_efficiency_cn()
