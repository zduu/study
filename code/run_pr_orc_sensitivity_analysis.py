import subprocess
import csv
import re
import numpy
import os
import pandas as pd
import numpy as np
import json
import time
import matplotlib.pyplot as plt
from full_cycle_simulator import load_cycle_parameters, simulate_scbc_orc_cycle, calculate_theoretical_exergy_efficiency

# 1. 定义固定的核心参数
T5_C = 599.85  # SCBC透平入口温度 (°C)
PR_SCBC = 3.27  # SCBC压比
THETA_W_C_RANGE = [110, 120, 130]  # ORC透平入口温度范围 (°C)

# 2. 定义 PR_ORC 的扫描范围
# 从 2.2 到 4.0 (包含边界)，步长为 0.2
PR_ORC_RANGE = [2.2, 2.4, 2.6, 2.8, 3.0, 3.2, 3.4, 3.6, 3.8, 4.0]  # 使用精确的列表而不是numpy.arange

# 3. 定义结果输出文件名
RESULTS_CSV_FILE = "pr_orc_sensitivity_results.csv"

# 辅助函数：从模拟输出中提取关键数据
def extract_metrics_from_output(output_text):
    """
    从模拟器输出文本中提取关键性能指标
    """
    metrics = {
        'total_thermal_efficiency': None,
        'total_exergy_efficiency': None,
        'scbc_net_power': None,
        'orc_net_power': None,
        'total_net_power': None,
        'carnot_efficiency': None
    }
    
    if not output_text:
        return metrics
    
    # 提取热效率
    thermal_eff_match = re.search(r"联合循环总热效率:\s*([\d\.]+)%", output_text)
    if thermal_eff_match:
        metrics['total_thermal_efficiency'] = float(thermal_eff_match.group(1))
    
    # 提取㶲效率
    exergy_eff_match = re.search(r"联合循环总㶲效率:\s*([\d\.]+)%", output_text)
    if exergy_eff_match:
        metrics['total_exergy_efficiency'] = float(exergy_eff_match.group(1))
    
    # 提取SCBC净功率
    scbc_power_match = re.search(r"SCBC净输出功:\s*([\d\.]+)\s*MW", output_text)
    if scbc_power_match:
        metrics['scbc_net_power'] = float(scbc_power_match.group(1))
    
    # 提取ORC净功率
    orc_power_match = re.search(r"ORC净输出功:\s*([\d\.]+)\s*MW", output_text)
    if orc_power_match:
        metrics['orc_net_power'] = float(orc_power_match.group(1))
    
    # 提取总净功率
    total_power_match = re.search(r"联合循环总净输出功:\s*([\d\.]+)\s*MW", output_text)
    if total_power_match:
        metrics['total_net_power'] = float(total_power_match.group(1))
    
    # 提取理论火用效率（卡诺效率）
    carnot_match = re.search(r"基于T5温度.*?的理论火用效率:\s*([\d\.]+)%", output_text)
    if carnot_match:
        metrics['carnot_efficiency'] = float(carnot_match.group(1))
    
    return metrics

def plot_results(results_df):
    """
    绘制敏感性分析结果图表
    """
    plt.style.use('default')  # 使用默认样式
    fig, ax1 = plt.subplots(figsize=(12, 8))
    
    # 设置中文字体
    plt.rcParams['font.sans-serif'] = ['Arial Unicode MS']  # 使用支持中文的字体
    plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
    
    # 创建第二个Y轴
    ax2 = ax1.twinx()
    
    # 为每个THETA_W_C值绘制热效率和㶲效率
    markers = ['o', 's', '^']  # 不同的标记样式
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c']  # 不同的颜色
    
    # 计算y轴范围
    thermal_min = results_df['Total_Thermal_Efficiency_percent'].min()
    thermal_max = results_df['Total_Thermal_Efficiency_percent'].max()
    exergy_min = results_df['Total_Exergy_Efficiency_percent'].min()
    exergy_max = results_df['Total_Exergy_Efficiency_percent'].max()
    
    # 为每个轴添加5%的边距
    thermal_range = thermal_max - thermal_min
    exergy_range = exergy_max - exergy_min
    thermal_min = thermal_min - thermal_range * 0.05
    thermal_max = thermal_max + thermal_range * 0.05
    exergy_min = exergy_min - exergy_range * 0.05
    exergy_max = exergy_max + exergy_range * 0.05
    
    for i, theta_w in enumerate(THETA_W_C_RANGE):
        data = results_df[results_df['THETA_W_C'] == theta_w]
        
        # 在左Y轴绘制热效率
        ax1.plot(data['PR_ORC'], data['Total_Thermal_Efficiency_percent'], 
                marker=markers[i], color=colors[i], linestyle='-', linewidth=2,
                label=f'THETA_W_C = {theta_w}°C (热效率)')
        
        # 在右Y轴绘制㶲效率
        ax2.plot(data['PR_ORC'], data['Total_Exergy_Efficiency_percent'], 
                marker=markers[i], color=colors[i], linestyle='--', linewidth=2,
                label=f'THETA_W_C = {theta_w}°C (火用效率)')
    
    # 设置左Y轴（热效率）
    ax1.set_xlabel('ORC压比 (PR_ORC)', fontsize=12)
    ax1.set_ylabel('热效率 (%)', fontsize=12, color='#1f77b4')
    ax1.tick_params(axis='y', labelcolor='#1f77b4')
    ax1.set_ylim(thermal_min-0.05, thermal_max+0.35)
    
    # 设置右Y轴（㶲效率）
    ax2.set_ylabel('火用效率 (%)', fontsize=12, color='#ff7f0e')
    ax2.tick_params(axis='y', labelcolor='#ff7f0e')
    ax2.set_ylim(exergy_min-0.2, exergy_max+0.2)
    
    # 设置标题和网格
    plt.title('不同THETA_W_C下PR_ORC对系统效率的影响', fontsize=14, pad=20)
    ax1.grid(True, linestyle='--', alpha=0.7)
    
    # 设置x轴范围
    ax1.set_xlim(min(PR_ORC_RANGE) - 0.2, max(PR_ORC_RANGE) + 0.2)
    
    # 设置刻度字体大小
    ax1.tick_params(axis='both', which='major', labelsize=10)
    ax2.tick_params(axis='both', which='major', labelsize=10)
    
    # 创建两个图例
    # 热效率图例
    thermal_lines = []
    thermal_labels = []
    for i, theta_w in enumerate(THETA_W_C_RANGE):
        line = ax1.plot([], [], marker=markers[i], color=colors[i], linestyle='-', linewidth=2)[0]
        thermal_lines.append(line)
        thermal_labels.append(f'THETA_W_C = {theta_w}°C (热效率)')
    
    # 火用效率图例
    exergy_lines = []
    exergy_labels = []
    for i, theta_w in enumerate(THETA_W_C_RANGE):
        line = ax2.plot([], [], marker=markers[i], color=colors[i], linestyle='--', linewidth=2)[0]
        exergy_lines.append(line)
        exergy_labels.append(f'THETA_W_C = {theta_w}°C (火用效率)')
    
    # 添加图例
    legend1 = ax1.legend(thermal_lines, thermal_labels, 
                        bbox_to_anchor=(1.05, 0.7), loc='upper left', fontsize=10,
                        title='热效率 (实线)')
    legend2 = ax2.legend(exergy_lines, exergy_labels,
                        bbox_to_anchor=(1.05, 0.3), loc='upper left', fontsize=10,
                        title='火用效率 (虚线)')
    
    # 添加第二个图例到图表
    ax1.add_artist(legend1)
    
    plt.tight_layout()
    plt.savefig('output/pr_orc_sensitivity_plot.png', dpi=300, bbox_inches='tight')
    plt.close()

def main():
    """
    主函数，执行参数敏感性分析。
    """
    # 设置输出文件路径
    output_csv_path = get_output_csv_path()
    print(f"开始执行参数敏感性分析，结果将保存到 {output_csv_path}")

    # 检查依赖脚本是否存在
    script_dir = os.path.dirname(os.path.abspath(__file__))
    required_scripts = ["modify_cycle_parameters.py", "full_cycle_simulator.py"]
    for script_name in required_scripts:
        script_path = os.path.join(script_dir, script_name)
        if not os.path.exists(script_path):
            print(f"错误：依赖脚本 {script_name} 未找到。")
            return

    # 确保输出目录存在
    output_dir = os.path.dirname(output_csv_path)
    os.makedirs(output_dir, exist_ok=True)

    try:
        # 1. 加载基础参数
        params_path = get_params_path()
        print(f"从 {params_path} 加载参数...")
        params = load_cycle_parameters(params_path)
        if not params:
            print("无法加载参数文件。")
            return

        # 2. 创建结果存储结构
        results = []
        result_headers = ["THETA_W_C", "PR_ORC", "Total_Thermal_Efficiency_percent", 
                         "Total_Exergy_Efficiency_percent", "SCBC_Net_Power_MW", 
                         "ORC_Net_Power_MW", "Total_Net_Power_MW", "Carnot_Efficiency_percent"]
        
        # 3. 运行敏感性分析
        total_cases = len(THETA_W_C_RANGE) * len(PR_ORC_RANGE)
        current_case = 0
        
        for theta_w in THETA_W_C_RANGE:
            for pr_orc in PR_ORC_RANGE:
                current_case += 1
                print(f"\n[{current_case}/{total_cases}] 分析 THETA_W_C = {theta_w}°C, PR_ORC = {pr_orc:.4f}")
                start_time = time.time()
                
                # 运行modify_cycle_parameters.py重新生成参数
                modify_script_path = os.path.join(script_dir, "modify_cycle_parameters.py")
                modify_cmd = [
                    "python", modify_script_path,
                    "--t5_c", str(T5_C),
                    "--pr_scbc", str(PR_SCBC),
                    "--pr_orc", str(pr_orc),
                    "--theta_w_c", str(theta_w)
                ]
                
                try:
                    subprocess.run(modify_cmd, check=True, capture_output=True)
                    
                    # 运行full_cycle_simulator.py
                    simulator_script_path = os.path.join(script_dir, "full_cycle_simulator.py")
                    simulate_cmd = ["python", simulator_script_path]
                    sim_result = subprocess.run(simulate_cmd, check=True, capture_output=True, text=True, encoding='utf-8')
                    output_text = sim_result.stdout
                    
                    # 从输出文本中提取指标
                    metrics = extract_metrics_from_output(output_text)
                    
                    # 存储结果
                    results.append([
                        theta_w,
                        pr_orc,
                        metrics['total_thermal_efficiency'],
                        metrics['total_exergy_efficiency'],
                        metrics['scbc_net_power'],
                        metrics['orc_net_power'],
                        metrics['total_net_power'],
                        metrics['carnot_efficiency']
                    ])
                    
                    print(f"  成功提取结果:")
                    print(f"    总热效率: {metrics['total_thermal_efficiency']}%")
                    print(f"    总㶲效率: {metrics['total_exergy_efficiency']}%")
                    
                except subprocess.CalledProcessError as e:
                    print(f"  错误: 运行命令失败: {e}")
                    print(f"  错误输出: {e.stderr}")
                except Exception as e:
                    print(f"  错误: 模拟失败: {e}")
                
                elapsed_time = time.time() - start_time
                print(f"  耗时: {elapsed_time:.2f} 秒")
        
        # 4. 保存结果到CSV
        if results:
            try:
                with open(output_csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(result_headers)
                    writer.writerows(results)
                print(f"\n结果已保存到: {output_csv_path}")
                
                # 5. 绘制结果图表
                results_df = pd.DataFrame(results, columns=result_headers)
                plot_results(results_df)
                print("已生成敏感性分析图表")
                
            except Exception as e:
                print(f"\n保存结果时发生错误: {e}")
        else:
            print("\n没有有效结果可保存，请检查模拟结果")

    except Exception as e:
        print(f"发生意外错误: {e}")

def get_params_path():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    output_dir = os.path.join(project_root, "output")
    os.makedirs(output_dir, exist_ok=True)
    return os.path.join(output_dir, "cycle_setup_parameters.json")

def get_output_csv_path():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    output_dir = os.path.join(project_root, "output")
    os.makedirs(output_dir, exist_ok=True)
    return os.path.join(output_dir, "pr_orc_sensitivity_results.csv")

if __name__ == "__main__":
    main() 