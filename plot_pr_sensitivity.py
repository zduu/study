import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

def plot_pr_sensitivity(csv_filepath='pr_sensitivity_results.csv', output_filename='pr_sensitivity_plot.png'):
    """
    读取PR_scbc敏感性分析结果并绘制图表。

    参数:
    csv_filepath (str): 包含敏感性分析结果的CSV文件路径。
    output_filename (str): 保存图表的图片文件名。
    """
    try:
        # 1. 读取CSV数据
        df = pd.read_csv(csv_filepath)
    except FileNotFoundError:
        print(f"错误：找不到CSV文件 '{csv_filepath}'。请确保文件存在于正确的路径。")
        return
    except Exception as e:
        print(f"读取CSV文件时发生错误: {e}")
        return

    # 确保必要的列存在
    required_columns = ["PR_scbc", "Total_Thermal_Efficiency_percent", "SCBC_Net_Power_MW", "ORC_Net_Power_MW"]
    for col in required_columns:
        if col not in df.columns:
            print(f"错误：CSV文件中缺少必需的列 '{col}'。")
            return

    # 2. 创建图表
    fig, ax1 = plt.subplots(figsize=(12, 7)) # 调整图表大小以便更好地显示

    # 设置X轴
    x_data = df["PR_scbc"]

    # 3. 主Y轴 (左侧) - 总热效率
    color_efficiency = 'tab:red'
    ax1.set_xlabel("顶循环压比 (PR_scbc)", fontsize=14)
    ax1.set_ylabel("总热效率 ηt (%)", color=color_efficiency, fontsize=14)
    line1 = ax1.plot(x_data, df["Total_Thermal_Efficiency_percent"], color=color_efficiency, marker='o', linestyle='-', label="总热效率 ηt (%)")
    ax1.tick_params(axis='y', labelcolor=color_efficiency, labelsize=12)
    ax1.tick_params(axis='x', labelsize=12)

    # 4. 次Y轴 (右侧) - SCBC净功 和 ORC净功
    ax2 = ax1.twinx()  # 共享X轴
    color_scbc_power = 'tab:blue'
    color_orc_power = 'tab:green'
    ax2.set_ylabel("净输出功率 (MW)", fontsize=14) # 共享标签

    line2 = ax2.plot(x_data, df["SCBC_Net_Power_MW"], color=color_scbc_power, marker='s', linestyle='--', label="SCBC净功 Ps (MW)")
    line3 = ax2.plot(x_data, df["ORC_Net_Power_MW"], color=color_orc_power, marker='^', linestyle=':', label="ORC净功 Po (MW)")
    ax2.tick_params(axis='y', labelsize=12) # 右侧Y轴刻度颜色默认为黑色

    # 统一Y轴刻度格式，例如保留两位小数
    ax1.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.2f'))
    ax2.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.2f'))

    # 5. 添加图表标题和图例
    plt.title("顶循环压比对联合循环性能的影响", fontsize=16)
    
    # 合并图例
    lines = line1 + line2 + line3
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc='upper center', bbox_to_anchor=(0.5, -0.15), fancybox=True, shadow=True, ncol=3, fontsize=10)

    # 6. 启用网格线
    ax1.grid(True, linestyle='--', alpha=0.7)
    ax2.grid(True, linestyle='--', alpha=0.7, axis='y') # 只在Y轴上为ax2添加网格，避免与ax1的X轴网格重叠

    # 调整布局以防止标签重叠
    fig.tight_layout(rect=[0, 0.1, 1, 0.95]) # 调整rect以给图例留出空间

    # 7. 显示和/或保存图表
    try:
        plt.savefig(output_filename, dpi=300)
        print(f"图表已保存为 '{output_filename}'")
    except Exception as e:
        print(f"保存图表时发生错误: {e}")
    
    plt.show()

if __name__ == "__main__":
    # 设置中文字体，确保图表能正确显示中文
    # 请根据您的系统和安装的字体进行调整
    # 例如: plt.rcParams['font.sans-serif'] = ['SimHei'] # Windows
    # plt.rcParams['font.family'] = ['Arial Unicode MS'] # macOS with Arial Unicode MS
    # plt.rcParams['axes.unicode_minus'] = False # 解决负号显示问题

    # 尝试设置一个常用的中文字体，如果找不到，matplotlib会回退到默认字体
    try:
        plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Heiti TC', 'sans-serif']
        plt.rcParams['axes.unicode_minus'] = False  # 正确显示负号
    except Exception as e:
        print(f"设置中文字体时出现警告: {e}. 图表中的中文可能无法正确显示。")

    plot_pr_sensitivity()