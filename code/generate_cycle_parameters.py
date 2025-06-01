import json
import os
from state_point_calculator import StatePoint, to_kelvin, to_pascal, T0_K

def calculate_orc_parameters(scbc_states):
    """
    根据SCBC状态点计算ORC循环参数
    """
    # 从SCBC状态点获取GO热侧温度
    T8_GO_HotIn = scbc_states.get("P8_GO_HotIn_Final", {}).get("T", None)
    T9_GO_HotOut = scbc_states.get("P9_GO_HotOut_CS_In", {}).get("T", None)
    
    if not T8_GO_HotIn or not T9_GO_HotOut:
        raise ValueError("无法获取GO热侧温度数据")
    
    # 计算ORC蒸发温度（取GO热侧平均温度减去最小温差）
    T_eva_orc = (T8_GO_HotIn + T9_GO_HotOut) / 2 - 20  # 增加最小温差到20K
    
    # 创建临时状态点来计算饱和压力
    temp_state = StatePoint("R245fa", "temp")
    temp_state.props_from_TQ(T_eva_orc, 1.0)  # 饱和蒸汽状态
    
    if not temp_state.P:
        raise ValueError("无法计算ORC蒸发压力")
    
    P_eva_orc_kPa = temp_state.P / 1000  # 转换为kPa
    
    # 使用固定的膨胀比（参考论文值）
    target_pr_orc = 3.37  # 固定膨胀比
    
    # 根据膨胀比计算冷凝压力
    P_cond_orc_kPa = P_eva_orc_kPa / target_pr_orc
    
    # 根据冷凝压力计算冷凝温度
    temp_state.props_from_PQ(to_pascal(P_cond_orc_kPa, 'kpa'), 0.0)  # 饱和液体状态
    if not temp_state.T:
        raise ValueError("无法计算ORC冷凝温度")
    
    T_cond_orc = temp_state.T
    
    # 打印调试信息
    print(f"\nORC参数计算过程:")
    print(f"  SCBC GO热侧温度: {T8_GO_HotIn-273.15:.2f}°C (进口) to {T9_GO_HotOut-273.15:.2f}°C (出口)")
    print(f"  ORC蒸发温度: {T_eva_orc-273.15:.2f}°C")
    print(f"  ORC蒸发压力: {P_eva_orc_kPa:.2f} kPa")
    print(f"  ORC冷凝温度: {T_cond_orc-273.15:.2f}°C")
    print(f"  ORC冷凝压力: {P_cond_orc_kPa:.2f} kPa")
    print(f"  ORC膨胀比: {target_pr_orc:.2f} (固定值)")
    
    return {
        # 可计算的参数
        "P_eva_kPa_orc": P_eva_orc_kPa,
        "T_pump_in_C_orc": T_cond_orc - 273.15,  # 转换为摄氏度
        "target_theta_w_orc_turbine_inlet_C": T_eva_orc - 273.15 + 5,  # 5K过热度
        "target_pr_orc_expansion_ratio": target_pr_orc,
        
        # 需要设定的参数（基于经验值）
        "eta_TO_turbine": 0.8,  # 透平效率
        "eta_PO_pump": 0.75,    # 泵效率
        "max_iter_orc_mdot": 40,  # 最大迭代次数
        "tol_orc_T_approach_K": 0.1,  # 温度收敛容差
        "m_dot_orc_initial_guess_kg_s": 100.0  # 初始质量流量猜测值
    }

def calculate_scbc_parameters(scbc_states):
    """
    根据SCBC状态点计算SCBC循环参数
    """
    # 从状态点获取关键参数
    P1 = scbc_states.get("P1_MC_In", {}).get("P", None)
    T1 = scbc_states.get("P1_MC_In", {}).get("T", None)
    T5 = scbc_states.get("P5_ER_Out_Turbine_In", {}).get("T", None)
    P2 = scbc_states.get("P2_MC_Out", {}).get("P", None)
    m_dot_total = scbc_states.get("P5_ER_Out_Turbine_In", {}).get("m_dot", None)
    m_dot_mc = scbc_states.get("P1_MC_In", {}).get("m_dot", None)
    
    if not all([P1, T1, T5, P2, m_dot_total, m_dot_mc]):
        raise ValueError("无法获取SCBC关键状态点数据")
    
    # 计算压比
    PR_main = P2 / P1
    
    # 打印调试信息
    print(f"\nSCBC参数计算过程:")
    print(f"  压缩机入口压力: {P1/1000:.2f} kPa")
    print(f"  压缩机入口温度: {T1-273.15:.2f}°C")
    print(f"  透平入口温度: {T5-273.15:.2f}°C")
    print(f"  主循环压比: {PR_main:.2f}")
    print(f"  总质量流量: {m_dot_total:.2f} kg/s")
    print(f"  压缩机分支质量流量: {m_dot_mc:.2f} kg/s")
    
    return {
        # 可计算的参数
        "p1_compressor_inlet_kPa": P1 / 1000,  # 转换为kPa
        "T1_compressor_inlet_C": T1 - 273.15,  # 转换为摄氏度
        "T5_turbine_inlet_C": T5 - 273.15,  # 转换为摄氏度
        "PR_main_cycle_pressure_ratio": PR_main,
        "T9_precooler_outlet_C": scbc_states.get("P9_GO_HotOut_CS_In", {}).get("T", None) - 273.15,
        "m_dot_total_main_flow_kg_s": m_dot_total,
        "m_dot_mc_branch_kg_s": m_dot_mc,
        
        # 需要设定的参数（基于经验值）
        "eta_T_turbine": 0.9,  # 透平效率
        "eta_C_compressor": 0.85,  # 压缩机效率
        "eta_H_HTR_effectiveness": 0.86,  # 高温换热器效率
        "eta_L_LTR_effectiveness": 0.86,  # 低温换热器效率
        "max_iter_scbc_main_loop": 20,  # 最大迭代次数
        "tol_scbc_h_kJ_kg": 0.1  # 焓收敛容差
    }

def calculate_parameters_from_key_variables(new_t5_c, new_pr_scbc, new_pr_orc, new_theta_w_orc_c):
    """
    根据四个关键变量计算所有循环参数
    
    参数:
        new_t5_c (float): 新的SCBC透平入口温度 (°C)
        new_pr_scbc (float): 新的SCBC主循环压比
        new_pr_orc (float): 新的ORC透平膨胀比
        new_theta_w_orc_c (float): 新的ORC透平入口温度 (°C)
    """
    # 创建临时状态点用于计算
    scbc_state = StatePoint("CO2", "temp")
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
    T_eva_orc = (T8_GO_HotIn + T9_GO_HotOut) / 2 - 10  # 20K最小温差
    
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

def generate_cycle_parameters(scbc_states=None, key_variables=None):
    """
    生成完整的循环参数文件
    
    参数:
        scbc_states: 可选的SCBC状态点字典
        key_variables: 可选的四个关键变量字典，包含:
            - new_t5_c: SCBC透平入口温度 (°C)
            - new_pr_scbc: SCBC主循环压比
            - new_pr_orc: ORC透平膨胀比
            - new_theta_w_orc_c: ORC透平入口温度 (°C)
    """
    try:
        if key_variables:
            # 使用四个关键变量计算参数
            cycle_params = calculate_parameters_from_key_variables(
                key_variables.get('new_t5_c'),
                key_variables.get('new_pr_scbc'),
                key_variables.get('new_pr_orc'),
                key_variables.get('new_theta_w_orc_c')
            )
        else:
            # 使用原有的SCBC状态点计算
            scbc_params = calculate_scbc_parameters(scbc_states)
            orc_params = calculate_orc_parameters(scbc_states)
            
            cycle_params = {
                "fluids": {
                    "scbc": "CO2",
                    "orc": "R245fa"
                },
                "reference_conditions": {
                    "T0_C": T0_K - 273.15,
                    "P0_kPa": 101.325
                },
                "scbc_parameters": scbc_params,
                "orc_parameters": orc_params,
                "heat_exchangers_common": {
                    "min_temp_diff_pinch_C": 10.0,
                    "approach_temp_eva_K_orc": 10
                },
                "notes": {
                    "phi_ER_MW_heat_input": 600.0,
                    "cost_fuel_cQ_dollar_per_MWh": 7.4
                }
            }
        
        # 确保输出目录存在
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        output_dir = os.path.join(project_root, "output")
        os.makedirs(output_dir, exist_ok=True)
        
        # 保存参数文件
        output_file = os.path.join(output_dir, "cycle_setup_parameters.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(cycle_params, f, indent=4, ensure_ascii=False)
        
        print(f"成功生成循环参数文件: {output_file}")
        return cycle_params
        
    except Exception as e:
        print(f"生成循环参数时发生错误: {e}")
        return None

def update_cycle_parameters(scbc_states):
    """
    更新现有的循环参数文件
    """
    try:
        # 读取现有参数文件
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        output_dir = os.path.join(project_root, "output")
        params_file = os.path.join(output_dir, "cycle_setup_parameters.json")
        
        if os.path.exists(params_file):
            with open(params_file, 'r', encoding='utf-8') as f:
                existing_params = json.load(f)
        else:
            existing_params = {}
        
        # 更新参数
        new_params = generate_cycle_parameters(scbc_states)
        if new_params:
            # 保留一些用户可能手动修改的参数
            if "notes" in existing_params:
                new_params["notes"] = existing_params["notes"]
            
            # 保存更新后的参数
            with open(params_file, 'w', encoding='utf-8') as f:
                json.dump(new_params, f, indent=4, ensure_ascii=False)
            
            print(f"成功更新循环参数文件: {params_file}")
            return new_params
        
    except Exception as e:
        print(f"更新循环参数时发生错误: {e}")
        return None

if __name__ == "__main__":
    # 测试代码
    test_key_variables = {
        "new_t5_c": 599.85,
        "new_pr_scbc": 3.27,
        "new_pr_orc": 3.37,
        "new_theta_w_orc_c": 127.76
    }
    
    generate_cycle_parameters(key_variables=test_key_variables) 