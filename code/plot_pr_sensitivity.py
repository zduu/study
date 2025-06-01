import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import os
import matplotlib as mpl
from matplotlib.font_manager import FontProperties

def setup_chinese_font():
    """设置支持中文显示的字体"""
    # 对于无法显示中文的情况，我们将使用英文标签
    plt.rcParams['font.family'] = ['DejaVu Sans', 'Arial', 'sans-serif']
    plt.rcParams['axes.unicode_minus'] = False
    print("使用英文标签以避免中文显示问题")

def plot_pr_sensitivity(csv_filepath=None, output_filename=None):
    """
    读取PR_scbc敏感性分析结果并绘制图表。

    参数:
    csv_filepath (str): 包含敏感性分析结果的CSV文件路径。
    output_filename (str): 保存图表的图片文件名。
    """
    # 设置中文字体
    setup_chinese_font()
    
    # 设置文件路径
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    output_dir = os.path.join(project_root, "output")
    os.makedirs(output_dir, exist_ok=True)
    
    # 如果未提供文件路径，使用默认值
    if csv_filepath is None:
        csv_filepath = os.path.join(output_dir, "pr_sensitivity_results.csv")
    # 如果提供的是相对路径，则将其视为相对于output目录
    elif not os.path.isabs(csv_filepath):
        csv_filepath = os.path.join(output_dir, csv_filepath)
    
    if output_filename is None:
        output_filename = os.path.join(output_dir, "pr_sensitivity_plot.png")
    # 如果提供的是相对路径，则将其视为相对于output目录
    elif not os.path.isabs(output_filename):
        output_filename = os.path.join(output_dir, output_filename)
    
    try:
        # 1. 读取CSV数据
        df = pd.read_csv(csv_filepath)
        # 打印CSV文件的列名，帮助理解数据结构
        print(f"CSV文件的列名: {list(df.columns)}")
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
    ax1.set_xlabel("SCBC Pressure Ratio (PR_scbc)", fontsize=14)
    ax1.set_ylabel("Total Thermal Efficiency ηt (%)", color=color_efficiency, fontsize=14)
    line1 = ax1.plot(x_data, df["Total_Thermal_Efficiency_percent"], color=color_efficiency, marker='o', linestyle='-', label="Total Thermal Efficiency ηt (%)")
    
    ax1.tick_params(axis='y', labelcolor=color_efficiency, labelsize=12)
    ax1.tick_params(axis='x', labelsize=12)

    # 4. 次Y轴 (右侧) - SCBC净功 和 ORC净功
    ax2 = ax1.twinx()  # 第一个次Y轴 (SCBC)
    ax3 = ax1.twinx()  # 第二个次Y轴 (ORC)

    # 配置第二个次Y轴 (ax3 for ORC) 使其不与第一个次Y轴 (ax2) 重叠
    ax3.spines["right"].set_position(("outward", 60)) # 向右偏移60个点

    color_scbc_power = 'tab:blue'
    color_orc_power = 'tab:green'

    # 配置 ax2 (SCBC净功)
    ax2.set_ylabel("SCBC Net Power Ps (MW)", color=color_scbc_power, fontsize=14)
    line2 = ax2.plot(x_data, df["SCBC_Net_Power_MW"], color=color_scbc_power, marker='s', linestyle='--', label="SCBC Net Power Ps (MW)")
    
    ax2.tick_params(axis='y', labelcolor=color_scbc_power, labelsize=12)

    # 配置 ax3 (ORC净功)
    ax3.set_ylabel("ORC Net Power Po (MW)", color=color_orc_power, fontsize=14)
    line3 = ax3.plot(x_data, df["ORC_Net_Power_MW"], color=color_orc_power, marker='^', linestyle=':', label="ORC Net Power Po (MW)")
    
    ax3.tick_params(axis='y', labelcolor=color_orc_power, labelsize=12)

    # 统一Y轴刻度格式，例如保留两位小数
    ax1.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.2f'))
    ax2.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.2f'))
    ax3.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.2f'))

    # 5. 添加图表标题和图例
    plt.title("Effect of SCBC Pressure Ratio on Combined Cycle Performance (Triple Y-axes)", fontsize=16)
    
    # 合并图例
    lines = line1 + line2 + line3
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc='upper center', bbox_to_anchor=(0.5, -0.20), fancybox=True, shadow=True, ncol=3, fontsize=10)

    # 6. 启用网格线
    ax1.grid(True, linestyle='--', alpha=0.7)
    ax2.grid(True, linestyle='--', alpha=0.7, axis='y', color=color_scbc_power)
    ax3.grid(True, linestyle='--', alpha=0.7, axis='y', color=color_orc_power)

    # 调整布局以防止标签重叠
    fig.tight_layout(rect=[0, 0.1, 1, 0.95])

    # 7. 显示和/或保存图表
    try:
        plt.savefig(output_filename, dpi=300)
        print(f"图表已保存为 '{output_filename}'")
    except Exception as e:
        print(f"保存图表时发生错误: {e}")
    
    plt.show()

def plot_exergy_efficiency(csv_filepath=None, output_filename=None):
    """
    绘制顶循环压比对火用效率的影响图。

    参数:
    csv_filepath (str): 包含敏感性分析结果的CSV文件路径。
    output_filename (str): 保存图表的图片文件名。
    """
    # 设置中文字体
    setup_chinese_font()
    
    # 设置文件路径
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    output_dir = os.path.join(project_root, "output")
    os.makedirs(output_dir, exist_ok=True)
    
    # 如果未提供文件路径，使用默认值
    if csv_filepath is None:
        csv_filepath = os.path.join(output_dir, "pr_sensitivity_results.csv")
    # 如果提供的是相对路径，则将其视为相对于output目录
    elif not os.path.isabs(csv_filepath):
        csv_filepath = os.path.join(output_dir, csv_filepath)
    
    if output_filename is None:
        output_filename = os.path.join(output_dir, "pr_exergy_efficiency_plot.png")
    # 如果提供的是相对路径，则将其视为相对于output目录
    elif not os.path.isabs(output_filename):
        output_filename = os.path.join(output_dir, output_filename)
    
    try:
        # 1. 读取CSV数据
        df = pd.read_csv(csv_filepath)
        print(f"CSV文件的列名: {list(df.columns)}")
    except FileNotFoundError:
        print(f"错误：找不到CSV文件 '{csv_filepath}'。请确保文件存在于正确的路径。")
        return
    except Exception as e:
        print(f"读取CSV文件时发生错误: {e}")
        return

    # 确保必要的列存在
    required_columns = ["PR_scbc", "Total_Exergy_Efficiency_percent", "Carnot_Efficiency_percent", "Exergy_Eff_to_Carnot_Ratio"]
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        print(f"警告：CSV文件中缺少以下列: {missing_columns}。图表可能不完整。")
    
    # 2. 创建图表
    fig, ax1 = plt.subplots(figsize=(12, 7)) # 调整图表大小

    # 设置X轴
    x_data = df["PR_scbc"]

    # 检查Carnot_Efficiency_percent是否为常数
    is_carnot_constant = False
    carnot_value = None
    if "Carnot_Efficiency_percent" in df.columns:
        # 检查第一个值与其他值是否相同
        first_val = df["Carnot_Efficiency_percent"].iloc[0]
        is_carnot_constant = all(df["Carnot_Efficiency_percent"] == first_val)
        if is_carnot_constant:
            carnot_value = first_val
            print(f"注意: Carnot_Efficiency_percent是常数值: {carnot_value}%")
        
    # 3. 主Y轴 (左侧) - 总火用效率
    color_exergy = 'tab:purple'
    ax1.set_xlabel("SCBC Pressure Ratio (PR_scbc)", fontsize=14)
    ax1.set_ylabel("Efficiency (%)", color='black', fontsize=14)
    
    if "Total_Exergy_Efficiency_percent" in df.columns:
        line1 = ax1.plot(x_data, df["Total_Exergy_Efficiency_percent"], color=color_exergy, marker='o', linestyle='-', label="Total Exergy Efficiency ηe (%)")
    else:
        line1 = []
        print("警告：找不到'Total_Exergy_Efficiency_percent'列，跳过火用效率图")
    
    # 如果Carnot效率是常数，则添加水平线
    if is_carnot_constant and carnot_value is not None:
        carnot_line = ax1.axhline(y=carnot_value, color='tab:orange', linestyle='--', 
                                 label=f"Theoretical Carnot Efficiency: {carnot_value:.2f}%")
    
    ax1.tick_params(axis='y', labelsize=12)
    ax1.tick_params(axis='x', labelsize=12)

    # 4. 次Y轴 (右侧) - 火用/卡诺比
    ax2 = None
    line2 = []
    
    if "Exergy_Eff_to_Carnot_Ratio" in df.columns:
        ax2 = ax1.twinx()  # 创建次Y轴
        color_ratio = 'tab:green'
        
        # 设置正确的比例，使曲线不完全重合
        min_ratio = df["Exergy_Eff_to_Carnot_Ratio"].min()
        max_ratio = df["Exergy_Eff_to_Carnot_Ratio"].max()
        ratio_range = max_ratio - min_ratio
        
        # 设置y轴的范围，使其与主y轴有区分
        y_min = min_ratio - ratio_range * 0.1  # 下限向下扩展10%
        y_max = max_ratio + ratio_range * 0.1  # 上限向上扩展10%
        ax2.set_ylim(y_min, y_max)
        
        ax2.set_ylabel("Exergy/Carnot Efficiency Ratio", color=color_ratio, fontsize=14)
        line2 = ax2.plot(x_data, df["Exergy_Eff_to_Carnot_Ratio"], color=color_ratio, marker='^', 
                        linestyle=':', label="Exergy/Carnot Efficiency Ratio")
        ax2.tick_params(axis='y', labelcolor=color_ratio, labelsize=12)
    else:
        print("警告：找不到'Exergy_Eff_to_Carnot_Ratio'列，跳过火用/卡诺比图")

    # 统一Y轴刻度格式
    ax1.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.2f'))
    if ax2 is not None:
        ax2.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.3f'))

    # 5. 添加图表标题和图例
    plt.title("Effect of SCBC Pressure Ratio on Exergy Efficiency", fontsize=16)
    
    # 合并图例
    lines = line1 + (line2 if line2 else [])
    if is_carnot_constant and carnot_value is not None:
        lines = line1 + [carnot_line] + (line2 if line2 else [])
    
    labels = [l.get_label() for l in lines]
    if lines:
        ax1.legend(lines, labels, loc='upper center', bbox_to_anchor=(0.5, -0.15), 
                  fancybox=True, shadow=True, ncol=2, fontsize=10)

    # 6. 启用网格线
    ax1.grid(True, linestyle='--', alpha=0.7)

    # 调整布局
    fig.tight_layout(rect=[0, 0.1, 1, 0.95])

    # 7. 显示和/或保存图表
    try:
        plt.savefig(output_filename, dpi=300)
        print(f"火用效率图表已保存为 '{output_filename}'")
    except Exception as e:
        print(f"保存火用效率图表时发生错误: {e}")
    
    plt.show()

if __name__ == "__main__":
    # 打印CSV文件的列说明
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    output_dir = os.path.join(project_root, "output")
    csv_path = os.path.join(output_dir, "pr_sensitivity_results.csv")
    
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        print("\nCSV文件列说明:")
        print(f"{'列名':<30} {'含义':<50}")
        print(f"{'-'*30} {'-'*50}")
        print(f"{'PR_scbc':<30} {'顶循环压比':<50}")
        print(f"{'Total_Thermal_Efficiency_percent':<30} {'总热效率 (%)':<50}")
        print(f"{'Total_Exergy_Efficiency_percent':<30} {'总火用效率 (%)':<50}")
        print(f"{'SCBC_Net_Power_MW':<30} {'SCBC净功率 (MW)':<50}")
        print(f"{'ORC_Net_Power_MW':<30} {'ORC净功率 (MW)':<50}")
        print(f"{'Total_Net_Power_MW':<30} {'总净功率 (MW)':<50}")
        print(f"{'Carnot_Efficiency_percent':<30} {'理论卡诺效率 (%)':<50}")
        print(f"{'Exergy_Eff_to_Carnot_Ratio':<30} {'火用效率/卡诺效率比':<50}")
        print("\n")
    
    # 绘制常规性能图表
    plot_pr_sensitivity()
    
    # 绘制火用效率图表
    plot_exergy_efficiency()