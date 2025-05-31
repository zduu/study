import subprocess
import csv
import re
import numpy
import os

# 1. 定义固定的核心参数
T5_C = 599.85  # SCBC透平入口温度 (°C)
PR_ORC = 3.37  # ORC透平膨胀比
THETA_W_C = 127.76  # ORC透平入口温度 (°C)

# 2. 定义 PR_scbc 的扫描范围
# 从 2.2 到 4.0 (包含边界)，步长为 0.2
PR_SCBC_RANGE = numpy.arange(2.2, 4.0 + 0.1, 0.1)

# 3. 定义结果输出文件名
RESULTS_CSV_FILE = "pr_sensitivity_results.csv"

# 4. 主循环逻辑
def main():
    """
    主函数，执行参数敏感性分析。
    """
    print(f"开始执行参数敏感性分析，结果将保存到 {RESULTS_CSV_FILE}")

    # 检查依赖脚本是否存在（与本脚本同级目录）
    script_dir = os.path.dirname(os.path.abspath(__file__))
    required_scripts = ["modify_cycle_parameters.py", "full_cycle_simulator.py"]
    for script_name in required_scripts:
        script_path = os.path.join(script_dir, script_name)
        if not os.path.exists(script_path):
            print(f"错误：依赖脚本 {script_name} 未找到。请确保该脚本与本脚本在同一目录下。")
            return

    try:
        with open(RESULTS_CSV_FILE, 'w', newline='', encoding='utf-8') as csvfile:
            csv_writer = csv.writer(csvfile)
            # 写入表头
            csv_writer.writerow([
                "PR_scbc",
                "Total_Thermal_Efficiency_percent",
                "SCBC_Net_Power_MW",
                "ORC_Net_Power_MW"
            ])

            for current_pr_scbc in PR_SCBC_RANGE:
                current_pr_scbc = round(current_pr_scbc, 2) # 保持两位小数
                print(f"\n正在处理 PR_scbc = {current_pr_scbc}...")

                # a. 构造并执行 modify_cycle_parameters.py 命令
                command_modify = [
                    "python", os.path.join(script_dir, "modify_cycle_parameters.py"),
                    "--t5_c", str(T5_C),
                    "--pr_scbc", str(current_pr_scbc),
                    "--pr_orc", str(PR_ORC),
                    "--theta_w_c", str(THETA_W_C)
                ]
                try:
                    print(f"  执行: {' '.join(command_modify)}")
                    modify_result = subprocess.run(command_modify, check=True, capture_output=True, text=True, encoding='utf-8')
                    print(f"  modify_cycle_parameters.py 执行成功。")
                    if modify_result.stdout:
                        print(f"    输出: {modify_result.stdout.strip()}")
                    if modify_result.stderr:
                        print(f"    错误输出: {modify_result.stderr.strip()}")
                except subprocess.CalledProcessError as e:
                    print(f"  错误: 执行 modify_cycle_parameters.py 失败。返回码: {e.returncode}")
                    print(f"    Stdout: {e.stdout}")
                    print(f"    Stderr: {e.stderr}")
                    csv_writer.writerow([current_pr_scbc, "Error_Modify", "Error_Modify", "Error_Modify"])
                    continue # 继续下一个 PR_scbc 值
                except FileNotFoundError:
                    print(f"  错误: python 或 modify_cycle_parameters.py 未找到。请检查路径和环境。")
                    csv_writer.writerow([current_pr_scbc, "Error_FileNotFound_Modify", "Error_FileNotFound_Modify", "Error_FileNotFound_Modify"])
                    continue


                # b. 构造并执行 full_cycle_simulator.py 命令
                command_simulate = ["python", os.path.join(script_dir, "full_cycle_simulator.py")]
                output_text = ""
                try:
                    print(f"  执行: {' '.join(command_simulate)}")
                    # 假设 full_cycle_simulator.py 将输出打印到stdout，并且也可能写入 full_cycle_simulator_output.txt
                    # 我们优先使用 stdout，如果模拟器设计为主要输出到文件，则需要调整
                    result_simulate = subprocess.run(command_simulate, check=True, capture_output=True, text=True, encoding='utf-8')
                    output_text = result_simulate.stdout
                    print(f"  full_cycle_simulator.py 执行成功。")
                    # 如果 full_cycle_simulator.py 确认会更新 full_cycle_simulator_output.txt，
                    # 并且其内容比stdout更完整或更适合解析，可以选择读取文件：
                    # try:
                    #     with open("full_cycle_simulator_output.txt", "r", encoding='utf-8') as f:
                    #         output_text = f.read()
                    #     print("  已从 full_cycle_simulator_output.txt 读取输出。")
                    # except FileNotFoundError:
                    #     print("  警告: full_cycle_simulator_output.txt 未找到，将仅使用 stdout。")
                    # except Exception as e:
                    #     print(f"  警告: 读取 full_cycle_simulator_output.txt 时发生错误: {e}")

                except subprocess.CalledProcessError as e:
                    print(f"  错误: 执行 full_cycle_simulator.py 失败。返回码: {e.returncode}")
                    print(f"    Stdout: {e.stdout}")
                    print(f"    Stderr: {e.stderr}")
                    # 即使模拟失败，也尝试从其stdout中解析，可能包含部分信息或错误提示
                    output_text = e.stdout if e.stdout else ""
                    if not output_text and os.path.exists("full_cycle_simulator_output.txt"): # 尝试读取文件
                        try:
                            with open("full_cycle_simulator_output.txt", "r", encoding='utf-8') as f_err:
                                output_text = f_err.read()
                            print("  从 full_cycle_simulator_output.txt 读取了部分输出(模拟失败时)。")
                        except Exception as read_err:
                             print(f"  读取 full_cycle_simulator_output.txt (模拟失败时)也失败: {read_err}")
                    
                    # 决定是否在CSV中记录特定错误或通用错误
                    csv_writer.writerow([current_pr_scbc, "Error_Simulate", "Error_Simulate", "Error_Simulate"])
                    # continue # 根据需要决定是否在模拟失败时跳过解析

                except FileNotFoundError:
                    print(f"  错误: python 或 full_cycle_simulator.py 未找到。请检查路径和环境。")
                    csv_writer.writerow([current_pr_scbc, "Error_FileNotFound_Simulate", "Error_FileNotFound_Simulate", "Error_FileNotFound_Simulate"])
                    continue


                # c. 解析模拟输出
                total_eff = "NaN"
                scbc_power = "NaN"
                orc_power = "NaN"

                if output_text:
                    # 联合循环总热效率: 43.84%
                    eff_match = re.search(r"联合循环总热效率:\s*([\d\.]+)\s*%", output_text)
                    if eff_match:
                        total_eff = eff_match.group(1)
                    else:
                        print("  警告: 未能从输出中解析到\"联合循环总热效率\"。")

                    # 尝试多种可能的SCBC净输出功格式
                    # "SCBC净输出功 (最终): 247.75 MW" 或其他变体
                    scbc_patterns = [
                        r"SCBC净输出功 \(最终\):\s*([\d\.]+)\s*MW",
                        r"SCBC净输出功 \(迭代收敛后\):\s*([\d\.]+)\s*MW",
                        r"SCBC净输出功:\s*([\d\.]+)\s*MW"
                    ]
                    
                    for pattern in scbc_patterns:
                        scbc_match = re.search(pattern, output_text)
                        if scbc_match:
                            scbc_power = scbc_match.group(1)
                            break
                    
                    if scbc_power == "NaN":
                        print("  警告: 未能从输出中解析到\"SCBC净输出功\"。")
                        print("  尝试从联合循环输出部分查找...")
                        # 在联合循环部分再次尝试查找
                        section_match = re.search(r"--- 联合循环总性能 ---\s*\n(.*?)(?=\n\n|$)", output_text, re.DOTALL)
                        if section_match:
                            section_text = section_match.group(1)
                            scbc_section_match = re.search(r"SCBC净输出功:\s*([\d\.]+)\s*MW", section_text)
                            if scbc_section_match:
                                scbc_power = scbc_section_match.group(1)
                                print(f"  成功从联合循环部分找到SCBC功率: {scbc_power} MW")

                    # ORC净输出功: 19.08 MW
                    orc_match = re.search(r"ORC净输出功:\s*([\d\.]+)\s*MW", output_text)
                    if orc_match:
                        orc_power = orc_match.group(1)
                    else:
                        print("  警告: 未能从输出中解析到\"ORC净输出功\"。")
                else:
                    print("  警告: full_cycle_simulator.py 的输出为空，无法解析。")


                # d. 将结果写入CSV文件
                csv_writer.writerow([current_pr_scbc, total_eff, scbc_power, orc_power])
                print(f"  结果: PR_scbc={current_pr_scbc}, Eff={total_eff}%, SCBC_P={scbc_power}MW, ORC_P={orc_power}MW")
                print(f"已完成 PR_scbc = {current_pr_scbc} 的模拟。")

        print(f"\n参数敏感性分析完成。结果已保存到 {RESULTS_CSV_FILE}")

    except IOError as e:
        print(f"错误: 无法写入CSV文件 {RESULTS_CSV_FILE}。错误: {e}")
    except Exception as e:
        print(f"发生意外错误: {e}")

if __name__ == "__main__":
    main()