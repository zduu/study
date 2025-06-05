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
PR_ORC = 3.37  # ORC透平膨胀比
THETA_W_C = 127.76  # ORC涡轮机入口温度 (°C)

# 2. 定义 PR_scbc 的扫描范围
# 从 2.2 到 4.0 (包含边界)，步长为 0.1
PR_SCBC_RANGE = numpy.arange(2.2, 4.0 + 0.1, 0.1)

# 3. 定义结果输出文件名
RESULTS_CSV_FILE = "pr_sensitivity_results.csv"

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

# 4. 主循环逻辑
def main():
    """
    主函数，执行参数敏感性分析。
    """
    # 设置输出文件路径
    output_csv_path = get_output_csv_path()
    print(f"开始执行参数敏感性分析，结果将保存到 {output_csv_path}")

    # 检查依赖脚本是否存在（与本脚本同级目录）
    script_dir = os.path.dirname(os.path.abspath(__file__))
    required_scripts = ["modify_cycle_parameters.py", "full_cycle_simulator.py"]
    for script_name in required_scripts:
        script_path = os.path.join(script_dir, script_name)
        if not os.path.exists(script_path):
            print(f"错误：依赖脚本 {script_name} 未找到。请确保该脚本与本脚本在同一目录下。")
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

        # 2. 定义PR_scbc范围
        pr_range = np.linspace(2.2, 4.0, 19)  # 从2.2到4.0，取19个点
        
        # 3. 创建结果存储结构
        results = []
        result_headers = ["PR_scbc", "Total_Thermal_Efficiency_percent", "Total_Exergy_Efficiency_percent", 
                         "SCBC_Net_Power_MW", "ORC_Net_Power_MW", "Total_Net_Power_MW", "Carnot_Efficiency_percent",
                         "Exergy_Eff_to_Carnot_Ratio"]
        
        # 4. 运行敏感性分析
        print("开始PR_scbc敏感性分析...")
        print(f"分析范围: PR_scbc = {min(pr_range):.2f} 到 {max(pr_range):.2f}，共{len(pr_range)}个点")
        
        for i, pr_value in enumerate(pr_range):
            print(f"\n[{i+1}/{len(pr_range)}] 分析 PR_scbc = {pr_value:.4f}")
            start_time = time.time()
            
            # 运行modify_cycle_parameters.py重新生成参数
            modify_script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "modify_cycle_parameters.py")
            modify_cmd = [
                "python", modify_script_path,
                "--t5_c", str(T5_C),
                "--pr_scbc", str(pr_value),
                "--pr_orc", str(PR_ORC),
                "--theta_w_c", str(THETA_W_C)
            ]
            
            try:
                subprocess.run(modify_cmd, check=True, capture_output=True)
                print(f"  成功重新生成参数: PR_scbc = {pr_value:.4f}")
                
                # 运行full_cycle_simulator.py
                simulator_script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "full_cycle_simulator.py")
                simulate_cmd = ["python", simulator_script_path]
                sim_result = subprocess.run(simulate_cmd, check=True, capture_output=True, text=True, encoding='utf-8')
                output_text = sim_result.stdout
                
                # 从输出文本中提取指标
                metrics = extract_metrics_from_output(output_text)
                
                # 检查是否成功提取关键指标
                if metrics['total_thermal_efficiency'] is not None or metrics['scbc_net_power'] is not None:
                    # 计算㶲效率/卡诺效率比
                    exergy_to_carnot_ratio = None
                    if metrics['total_exergy_efficiency'] is not None and metrics['carnot_efficiency'] is not None:
                        exergy_to_carnot_ratio = metrics['total_exergy_efficiency'] / metrics['carnot_efficiency']
                    
                    # 存储结果
                    results.append([
                        pr_value, 
                        metrics['total_thermal_efficiency'],
                        metrics['total_exergy_efficiency'],
                        metrics['scbc_net_power'],
                        metrics['orc_net_power'],
                        metrics['total_net_power'],
                        metrics['carnot_efficiency'],
                        exergy_to_carnot_ratio
                    ])
                    
                    print(f"  成功提取结果:")
                    print(f"    总热效率: {metrics['total_thermal_efficiency']}%")
                    print(f"    总㶲效率: {metrics['total_exergy_efficiency']}%")
                    print(f"    SCBC净功: {metrics['scbc_net_power']} MW")
                    print(f"    ORC净功: {metrics['orc_net_power']} MW")
                    print(f"    总净功: {metrics['total_net_power']} MW")
                else:
                    print(f"  警告: 无法从输出中提取关键指标")
            
            except subprocess.CalledProcessError as e:
                print(f"  错误: 运行命令失败: {e}")
                print(f"  错误输出: {e.stderr}")
            except Exception as e:
                print(f"  错误: PR_scbc = {pr_value:.4f} 的模拟失败: {e}")
            
            elapsed_time = time.time() - start_time
            print(f"  耗时: {elapsed_time:.2f} 秒")
        
        # 5. 保存结果到CSV
        if results:
            try:
                with open(output_csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(result_headers)
                    writer.writerows(results)
                print(f"\n结果已保存到: {output_csv_path}")
                # 删除自动绘制和提示图表的相关代码
                # try:
                #     from plot_pr_sensitivity import plot_pr_sensitivity
                #     plot_pr_sensitivity(output_csv_path)
                #     print("已生成敏感性分析图表")
                # except Exception as e:
                #     print(f"绘制图表时发生错误: {e}")
            except Exception as e:
                print(f"\n保存CSV时发生错误: {e}")
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
    return os.path.join(output_dir, "pr_sensitivity_results.csv")

if __name__ == "__main__":
    main()