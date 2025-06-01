import json
from state_point_calculator import StatePoint, to_pascal, to_kelvin
import os

def update_cycle_parameters(
    new_t5_c: float,
    new_pr_scbc: float,
    new_pr_orc: float,
    new_theta_w_orc_c: float,
    params_filepath="cycle_setup_parameters.json"
):
    """
    读取、修改并写回循环参数JSON文件。

    参数:
        new_t5_c (float): 新的SCBC透平入口温度 (°C)。
        new_pr_scbc (float): 新的SCBC主循环压比。
        new_pr_orc (float): 新的ORC透平膨胀比。
        new_theta_w_orc_c (float): 新的ORC透平入口温度 (°C)。
        params_filepath (str): 参数JSON文件的路径。
    """
# 参数边界检查
    if not (500 <= new_t5_c <= 600):
        print(f"错误: SCBC透平入口温度 new_t5_c ({new_t5_c}°C) 超出允许范围 [500, 600]°C。")
        return
    if not (2.2 <= new_pr_scbc <= 4.0):
        print(f"错误: SCBC主循环压比 new_pr_scbc ({new_pr_scbc}) 超出允许范围 [2.2, 4.0]。")
        return
    if not (100 <= new_theta_w_orc_c <= 130):
        print(f"错误: ORC透平入口温度 new_theta_w_orc_c ({new_theta_w_orc_c}°C) 超出允许范围 [100, 130]°C。")
        return
    if not (2.2 <= new_pr_orc <= 4.0):
        print(f"错误: ORC透平膨胀比 new_pr_orc ({new_pr_orc}) 超出允许范围 [2.2, 4.0]。")
        return
    
    # 尝试找到参数文件
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    
    # 首先尝试在output目录中查找文件
    output_dir = os.path.join(project_root, "output")
    output_file_path = os.path.join(output_dir, params_filepath)
    
    # 如果output目录中不存在该文件，则尝试从当前目录加载
    if not os.path.exists(output_file_path):
        output_file_path = os.path.join(script_dir, params_filepath)
    
    # 如果都不存在，则使用原始路径
    if not os.path.exists(output_file_path):
        output_file_path = params_filepath
    
    try:
        with open(output_file_path, 'r', encoding='utf-8') as f:
            params = json.load(f)
    except FileNotFoundError:
        print(f"错误: 参数文件 {output_file_path} 未找到。")
        return
    except json.JSONDecodeError:
        print(f"错误: 参数文件 {output_file_path} 格式不正确。")
        return

    # 1. 更新 SCBC 参数
    params["scbc_parameters"]["T5_turbine_inlet_C"] = new_t5_c
    params["scbc_parameters"]["PR_main_cycle_pressure_ratio"] = new_pr_scbc
    print(f"已更新 SCBC: T5_turbine_inlet_C = {new_t5_c}°C, PR_main_cycle_pressure_ratio = {new_pr_scbc}")
    
    # 1a. 计算并更新T9_precooler_outlet_C (基于压比和其他参数)
    scbc_fluid = params["fluids"]["scbc"]
    p1_kpa = params["scbc_parameters"]["p1_compressor_inlet_kPa"]
    T1_C = params["scbc_parameters"]["T1_compressor_inlet_C"]
    p2_kpa = p1_kpa * new_pr_scbc
    
    # 创建状态点实例
    compressor_inlet = StatePoint(scbc_fluid, "scbc_compressor_inlet")
    compressor_inlet.props_from_PT(to_pascal(p1_kpa, 'kpa'), to_kelvin(T1_C))
    
    # 预估预冷器出口温度T9随压比的关系（这是一个简化模型，实际需要热力学计算）
    # 在实际循环中，随着压比增加，预冷器出口温度会受到很多因素影响
    # 这里使用简单的线性模型作为初步估计: T9 = T1 + k*(PR-3.27)
    # 其中k是温度对压比的敏感度系数，基于84.38°C和3.27的压比

    base_T9_C = 84.38  # 基准点T9温度
    base_PR = 3.27     # 基准点压比
    sensitivity_factor = 5.0  # 温度对压比的敏感度系数，单位: °C/PR单位
    
    # 计算新的T9值
    new_T9_C = base_T9_C + sensitivity_factor * (new_pr_scbc - base_PR)
    
    # 限制T9的范围，确保不会出现不合理的温度
    min_T9_C = T1_C + 30  # 假设预冷器出口至少比压缩机入口高30°C
    max_T9_C = 120.0      # 假设最大不超过120°C
    new_T9_C = max(min_T9_C, min(new_T9_C, max_T9_C))
    
    # 更新参数
    params["scbc_parameters"]["T9_precooler_outlet_C"] = new_T9_C
    print(f"已更新 SCBC: T9_precooler_outlet_C = {new_T9_C:.2f}°C (基于压比 PR = {new_pr_scbc})")

    # 2. 更新 ORC 参数
    orc_fluid = params["fluids"]["orc"]
    p_eva_kpa_orc = params["orc_parameters"]["P_eva_kPa_orc"]
    
    # 更新ORC透平入口温度目标值
    params["orc_parameters"]["target_theta_w_orc_turbine_inlet_C"] = new_theta_w_orc_c
    print(f"已更新 ORC: target_theta_w_orc_turbine_inlet_C = {new_theta_w_orc_c}°C")
    
    # 更新ORC膨胀比目标值
    params["orc_parameters"]["target_pr_orc_expansion_ratio"] = new_pr_orc
    print(f"已更新 ORC: target_pr_orc_expansion_ratio = {new_pr_orc}")

    # 2a. 根据新的 pr_orc 计算并更新 P_cond_kPa_orc
    if new_pr_orc <= 0:
        print("错误: ORC膨胀比 pr_orc 必须大于0。")
        return
    new_p_cond_kpa_orc = p_eva_kpa_orc / new_pr_orc
    
    # 2c. 根据新的 P_cond_kPa_orc 计算并更新 T_pump_in_C_orc (假设为饱和液体温度)
    state_sat_cond_orc = StatePoint(orc_fluid, "temp_sat_cond_orc_for_pump_in")
    state_sat_cond_orc.props_from_PQ(to_pascal(new_p_cond_kpa_orc, 'kpa'), 0.0) # Q=0.0 表示饱和液体

    if state_sat_cond_orc.T is None:
        print(f"错误: 无法获取工质 {orc_fluid} 在 {new_p_cond_kpa_orc:.2f} kPa 下的饱和液体温度。无法更新泵进口温度。")
        # 保持原值或设为默认值？这里选择不更新并打印错误。
    else:
        new_t_pump_in_c_orc = state_sat_cond_orc.T - 273.15
        params["orc_parameters"]["T_pump_in_C_orc"] = new_t_pump_in_c_orc
        print(f"已更新 ORC: T_pump_in_C_orc = {new_t_pump_in_c_orc:.2f}°C (基于新的 P_cond={new_p_cond_kpa_orc:.2f} kPa下的饱和液体温度)")

    # 3. 写回JSON文件
    try:
        with open(output_file_path, 'w', encoding='utf-8') as f:
            json.dump(params, f, indent=4, ensure_ascii=False)
        print(f"参数已成功更新并写回到 {output_file_path}")
    except IOError:
        print(f"错误: 无法写入参数文件 {output_file_path}。")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="修改循环参数配置文件 (cycle_setup_parameters.json)。")
    parser.add_argument("--t5_c", type=float, required=True, help="新的SCBC透平入口温度 (°C)")
    parser.add_argument("--pr_scbc", type=float, required=True, help="新的SCBC主循环压比")
    parser.add_argument("--pr_orc", type=float, required=True, help="新的ORC透平膨胀比")
    parser.add_argument("--theta_w_c", type=float, required=True, help="新的ORC透平入口温度 (°C)")

    args = parser.parse_args()

    print("开始通过命令行参数修改循环参数...")
    update_cycle_parameters(
        new_t5_c=args.t5_c,
        new_pr_scbc=args.pr_scbc,
        new_pr_orc=args.pr_orc,
        new_theta_w_orc_c=args.theta_w_c
    )
    print("参数修改脚本执行完毕。")