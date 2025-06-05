import json
import os
from state_point_calculator import StatePoint, to_pascal, to_kelvin, T0_K

def generate_cycle_parameters(new_t5_c, new_pr_scbc, new_pr_orc, new_theta_w_orc_c):
    """
    根据四个关键变量重新生成完整的循环参数
    
    参数:
        new_t5_c (float): 新的SCBC透平入口温度 (°C)
        new_pr_scbc (float): 新的SCBC主循环压比
        new_pr_orc (float): 新的ORC透平膨胀比
        new_theta_w_orc_c (float): 新的ORC涡轮机入口温度 (°C)
    """
    # 参数边界检查
    if not (500 <= new_t5_c <= 600):
        print(f"错误: SCBC透平入口温度 new_t5_c ({new_t5_c}°C) 超出允许范围 [500, 600]°C。")
        return None
    if not (2.2 <= new_pr_scbc <= 4.0):
        print(f"错误: SCBC主循环压比 new_pr_scbc ({new_pr_scbc}) 超出允许范围 [2.2, 4.0]。")
        return None
    if not (100 <= new_theta_w_orc_c <= 130):
        print(f"错误: ORC涡轮机入口温度 new_theta_w_orc_c ({new_theta_w_orc_c}°C) 超出允许范围 [100, 130]°C。")
        return None
    if not (2.2 <= new_pr_orc <= 4.0):
        print(f"错误: ORC透平膨胀比 new_pr_orc ({new_pr_orc}) 超出允许范围 [2.2, 4.0]。")
        return None
    
    # 创建临时状态点用于计算
    orc_state = StatePoint("R245fa", "temp")
    
    # 1. 计算SCBC参数
    # 基础参数
    p1_kpa = 7400.0  # 压缩机入口压力固定
    T1_C = 35.0      # 压缩机入口温度固定
    p2_kpa = p1_kpa * new_pr_scbc
    
    # 计算T9 (预冷器出口温度)
    base_T9_C = 84.38  # 基准点T9温度
    base_PR = 3.27     # 基准点压比
    sensitivity_factor = 5.0  # 温度对压比的敏感度系数
    new_T9_C = base_T9_C + sensitivity_factor * (new_pr_scbc - base_PR)
    min_T9_C = T1_C + 30
    max_T9_C = 120.0
    new_T9_C = max(min_T9_C, min(new_T9_C, max_T9_C))
    
    # 2. 计算ORC参数
    # 计算ORC蒸发温度（基于SCBC GO热侧温度）
    T8_GO_HotIn = new_T9_C + 63.29  # 基于基准值计算
    T9_GO_HotOut = new_T9_C
    T_eva_orc = (T8_GO_HotIn + T9_GO_HotOut) / 2 - 8.2  # 20K最小温差
    
    # 计算ORC蒸发压力
    orc_state.props_from_TQ(to_kelvin(T_eva_orc), 1.0)
    if not orc_state.P:
        raise ValueError("无法计算ORC蒸发压力")
    P_eva_orc_kPa = orc_state.P / 1000
    
    # 计算ORC冷凝压力
    P_cond_orc_kPa = P_eva_orc_kPa / new_pr_orc
    
    # 计算ORC冷凝温度
    orc_state.props_from_PQ(to_pascal(P_cond_orc_kPa, 'kpa'), 0.0)
    if not orc_state.T:
        raise ValueError("无法计算ORC冷凝温度")
    T_cond_orc = orc_state.T
    
    # 构建完整的参数结构
    cycle_params = {
        "fluids": {
            "scbc": "CO2",
            "orc": "R245fa"
        },
        "reference_conditions": {
            "T0_C": T0_K - 273.15,
            "P0_kPa": 101.325
        },
        "scbc_parameters": {
            "p1_compressor_inlet_kPa": p1_kpa,
            "T1_compressor_inlet_C": T1_C,
            "T5_turbine_inlet_C": new_t5_c,
            "PR_main_cycle_pressure_ratio": new_pr_scbc,
            "T9_precooler_outlet_C": new_T9_C,
            "m_dot_total_main_flow_kg_s": 2641.42,  # 固定值
            "m_dot_mc_branch_kg_s": 1945.09,        # 固定值
            "eta_T_turbine": 0.9,
            "eta_C_compressor": 0.85,
            "eta_H_HTR_effectiveness": 0.86,
            "eta_L_LTR_effectiveness": 0.86,
            "max_iter_scbc_main_loop": 20,
            "tol_scbc_h_kJ_kg": 0.1
        },
        "orc_parameters": {
            "P_eva_kPa_orc": P_eva_orc_kPa,
            "T_pump_in_C_orc": T_cond_orc - 273.15,
            "target_theta_w_orc_turbine_inlet_C": new_theta_w_orc_c,
            "target_pr_orc_expansion_ratio": new_pr_orc,
            "eta_TO_turbine": 0.8,
            "eta_PO_pump": 0.75,
            "max_iter_orc_mdot": 40,
            "tol_orc_T_approach_K": 0.1,
            "m_dot_orc_initial_guess_kg_s": 100.0
        },
        "heat_exchangers_common": {
            "min_temp_diff_pinch_C": 10.0,
            "approach_temp_eva_K_orc": 10
        },
        "notes": {
            "phi_ER_MW_heat_input": 600.0,
            "cost_fuel_cQ_dollar_per_MWh": 7.4
        }
    }
    
    return cycle_params

def update_cycle_parameters(
    new_t5_c: float,
    new_pr_scbc: float,
    new_pr_orc: float,
    new_theta_w_orc_c: float,
    params_filepath="cycle_setup_parameters.json"
):
    """
    重新生成循环参数JSON文件。

    参数:
        new_t5_c (float): 新的SCBC透平入口温度 (°C)。
        new_pr_scbc (float): 新的SCBC主循环压比。
        new_pr_orc (float): 新的ORC透平膨胀比。
        new_theta_w_orc_c (float): 新的ORC涡轮机入口温度 (°C)。
        params_filepath (str): 参数JSON文件的路径。
    """
    try:
        # 根据四个关键变量生成新的参数
        new_params = generate_cycle_parameters(new_t5_c, new_pr_scbc, new_pr_orc, new_theta_w_orc_c)
        if not new_params:
            return
        
        # 确定输出文件路径
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        output_dir = os.path.join(project_root, "output")
        os.makedirs(output_dir, exist_ok=True)
        output_file_path = os.path.join(output_dir, params_filepath)
        
        # 写入JSON文件
        with open(output_file_path, 'w', encoding='utf-8') as f:
            json.dump(new_params, f, indent=4, ensure_ascii=False)
        
        print(f"参数已成功重新生成并写入到 {output_file_path}")
        print(f"已更新 SCBC: T5_turbine_inlet_C = {new_t5_c}°C, PR_main_cycle_pressure_ratio = {new_pr_scbc}")
        print(f"已更新 SCBC: T9_precooler_outlet_C = {new_params['scbc_parameters']['T9_precooler_outlet_C']:.2f}°C (基于压比 PR = {new_pr_scbc})")
        print(f"已更新 ORC: target_theta_w_orc_turbine_inlet_C = {new_theta_w_orc_c}°C")
        print(f"已更新 ORC: target_pr_orc_expansion_ratio = {new_pr_orc}")
        print(f"已更新 ORC: T_pump_in_C_orc = {new_params['orc_parameters']['T_pump_in_C_orc']:.2f}°C (基于新的 P_cond={new_params['orc_parameters']['P_eva_kPa_orc']/new_pr_orc:.2f} kPa下的饱和液体温度)")
        
    except Exception as e:
        print(f"错误: 重新生成参数文件时发生错误: {e}")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="重新生成循环参数配置文件 (cycle_setup_parameters.json)。")
    parser.add_argument("--t5_c", type=float, required=True, help="新的SCBC透平入口温度 (°C)")
    parser.add_argument("--pr_scbc", type=float, required=True, help="新的SCBC主循环压比")
    parser.add_argument("--pr_orc", type=float, required=True, help="新的ORC透平膨胀比")
    parser.add_argument("--theta_w_c", type=float, required=True, help="新的ORC涡轮机入口温度 (°C)")

    args = parser.parse_args()

    print("开始通过命令行参数重新生成循环参数...")
    update_cycle_parameters(
        new_t5_c=args.t5_c,
        new_pr_scbc=args.pr_scbc,
        new_pr_orc=args.pr_orc,
        new_theta_w_orc_c=args.theta_w_c
    )
    print("参数生成脚本执行完毕。")