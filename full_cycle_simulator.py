import json
import contextlib
from state_point_calculator import StatePoint, to_kelvin, to_pascal, T0_K
from cycle_components import (
    model_compressor_MC,
    model_turbine_T,
    model_pump_ORC,
    model_heat_exchanger_effectiveness,
    model_evaporator_GO,
    model_cooler_set_T_out,
    model_heater_set_T_out
)
import sys  # For redirecting output if needed
sys.stdout.reconfigure(encoding='utf-8')

# Optional: for numerical root finding
# from scipy.optimize import root_scalar

def calculate_exergy_efficiency(Q_in_J_s, T_source_K, W_net_J_s):
    """
    计算热力循环的火用效率。
    
    参数:
        Q_in_J_s: 循环吸收的热量 (J/s 或 W)
        T_source_K: 热源温度 (K)
        W_net_J_s: 循环净输出功 (J/s 或 W)
        
    返回:
        火用效率 (无量纲)
    """
    # 卡诺因子
    carnot_factor = 1 - T0_K / T_source_K
    
    # 热输入的火用
    E_in_J_s = Q_in_J_s * carnot_factor
    
    # 火用效率
    if E_in_J_s > 0:
        exergy_efficiency = W_net_J_s / E_in_J_s
    else:
        exergy_efficiency = 0
        
    return exergy_efficiency

def calculate_theoretical_exergy_efficiency(T_source_K):
    """
    计算理论火用效率 (卡诺效率)
    
    参数:
        T_source_K: 热源温度 (K)
        
    返回:
        理论火用效率 (无量纲)
    """
    return 1 - T0_K / T_source_K

def load_cycle_parameters(filename="cycle_setup_parameters.json"):
    """从JSON文件加载循环设定参数"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            params = json.load(f)
        print(f"成功从 {filename} 加载循环参数。")
        return params
    except FileNotFoundError:
        print(f"错误: 参数文件 {filename} 未找到。请先运行 状态点计算.py 生成该文件。")
        return None
    except json.JSONDecodeError:
        print(f"错误: 参数文件 {filename} 格式不正确，无法解析。")
        return None
    except Exception as e:
        print(f"加载参数文件时发生未知错误: {e}")
        return None


def calculate_scbc_high_temp_loop(
        params, state1_mc_in, current_m_dot_total, current_m_dot_mc_branch
):
    """
    封装SCBC高温侧和相关低温侧的计算逻辑。
    此函数会进行内部迭代以收敛回热器。
    返回计算得到的 Q_er_calc (J/s), W_net_scbc_J_s, 和所有相关的状态点。
    """
    scbc_params = params.get("scbc_parameters", {})
    scbc_fluid = params.get("fluids", {}).get("scbc", "CO2")

    # --- 主压缩机 (MC) ---
    # MC的进口状态和流量由外部传入
    state1 = state1_mc_in
    state1.m_dot = current_m_dot_mc_branch  # Ensure MC branch flow rate is set

    pr_top = scbc_params.get('PR_main_cycle_pressure_ratio')
    eta_mc = scbc_params.get('eta_C_compressor')
    P2_Pa = state1.P * pr_top

    state2, W_mc_J_kg = model_compressor_MC(state1, P2_Pa, eta_mc)
    if not state2:
        print("错误: 主压缩机MC计算失败。")
        return None, None, None
    W_mc_total_J_s = W_mc_J_kg * state1.m_dot if state1.m_dot else 0

    # --- SCBC高温侧迭代计算 (HTR, ER, Turbine T, LTR, RC) ---
    max_iter_scbc_regen = scbc_params.get("max_iter_scbc_main_loop", 20)
    tol_scbc_h_kJ_kg = scbc_params.get("tol_scbc_h_kJ_kg", 0.1)

    P_low_cycle_Pa = state1.P  # 透平出口和回热器热侧低压等于主压缩机进口压力

    T6_iter_C_guess = scbc_params.get('T6_HTR_hot_in_C_guess', 455.03)
    state6_iter = StatePoint(scbc_fluid, "P6_Iter_HTR_HotIn_MFLOW_ITER")
    state6_iter.props_from_PT(P_low_cycle_Pa, to_kelvin(T6_iter_C_guess))
    state6_iter.m_dot = current_m_dot_total  # 总流量
    if not state6_iter.h: return None, None, None

    T7_iter_C_guess = scbc_params.get('T7_LTR_hot_in_C_guess', 306.16)
    state7_iter = StatePoint(scbc_fluid, "P7_Iter_LTR_HotIn_MFLOW_ITER")
    state7_iter.props_from_PT(P_low_cycle_Pa, to_kelvin(T7_iter_C_guess))
    state7_iter.m_dot = current_m_dot_total  # 总流量
    if not state7_iter.h: return None, None, None

    state3_calc, state4_htr_cold_out, state5_er_out = None, None, None
    state6_turbine_out, state7_htr_hot_out, state8_calc_ltr = None, None, None
    state_ltr_cold_out, state_rc_out, state8r_rc_in = None, None, None
    W_t_J_kg, W_rc_J_kg, Q_er_calc_J_s = 0, 0, 0

    converged_scbc_regen = False
    for i_scbc_regen in range(max_iter_scbc_regen):
        h6_old_J_kg = state6_iter.h
        h7_old_J_kg = state7_iter.h

        eta_L = scbc_params.get('eta_L_LTR_effectiveness')
        _state8_calc_ltr, _state_ltr_cold_out, _ = model_heat_exchanger_effectiveness(
            state_hot_in=state7_iter, state_cold_in=state2, effectiveness=eta_L,
            hot_fluid_is_C_min_side=True, name_suffix=f"LTR_RegenIter{i_scbc_regen + 1}"
        )
        if not (_state8_calc_ltr and _state_ltr_cold_out): return None, None, None
        state8_calc_ltr, state_ltr_cold_out = _state8_calc_ltr, _state_ltr_cold_out

        m_dot_rc = current_m_dot_total - current_m_dot_mc_branch
        _state8r_rc_in = StatePoint(scbc_fluid, f"P8r_RC_In_RegenIter{i_scbc_regen + 1}")
        _state8r_rc_in.props_from_PH(state8_calc_ltr.P, state8_calc_ltr.h)  # RC进口与LTR热出口同状态
        _state8r_rc_in.m_dot = m_dot_rc
        state8r_rc_in = _state8r_rc_in

        eta_rc = scbc_params.get('eta_C_compressor')
        _state_rc_out, _W_rc_J_kg = model_compressor_MC(state8r_rc_in, state2.P, eta_rc)
        if not _state_rc_out: return None, None, None
        state_rc_out, W_rc_J_kg = _state_rc_out, _W_rc_J_kg

        m_dot_3_calc = state_ltr_cold_out.m_dot + state_rc_out.m_dot
        if abs(m_dot_3_calc) < 1e-6: return None, None, None
        h3_mixed_J_kg = (state_ltr_cold_out.m_dot * state_ltr_cold_out.h + \
                         state_rc_out.m_dot * state_rc_out.h) / m_dot_3_calc
        _state3_calc = StatePoint(scbc_fluid, f"P3_Mixed_RegenIter{i_scbc_regen + 1}")
        _state3_calc.props_from_PH(state2.P, h3_mixed_J_kg)
        _state3_calc.m_dot = m_dot_3_calc
        if not _state3_calc.h: return None, None, None
        state3_calc = _state3_calc
        if abs(state3_calc.m_dot - current_m_dot_total) > 0.01 * current_m_dot_total:  # Check consistency
            print(
                f"  警告 (RegenIter {i_scbc_regen + 1}): 混合点3流量 {state3_calc.m_dot:.2f} 与当前总流量 {current_m_dot_total:.2f} 不符。")
            state3_calc.m_dot = current_m_dot_total

        eta_H = scbc_params.get('eta_H_HTR_effectiveness')
        _state7_htr_hot_out, _state4_htr_cold_out, _ = model_heat_exchanger_effectiveness(
            state_hot_in=state6_iter, state_cold_in=state3_calc, effectiveness=eta_H,
            hot_fluid_is_C_min_side=True, name_suffix=f"HTR_RegenIter{i_scbc_regen + 1}"
        )
        if not (_state7_htr_hot_out and _state4_htr_cold_out): return None, None, None
        state7_htr_hot_out, state4_htr_cold_out = _state7_htr_hot_out, _state4_htr_cold_out

        T5_target_C = scbc_params.get('T5_turbine_inlet_C')
        _state5_er_out, _Q_er_calc_J_s = model_heater_set_T_out(
            state_in=state4_htr_cold_out, T_out_K=to_kelvin(T5_target_C),
            name_suffix=f"ER_RegenIter{i_scbc_regen + 1}"
        )
        if not _state5_er_out: return None, None, None
        state5_er_out, Q_er_calc_J_s = _state5_er_out, _Q_er_calc_J_s

        eta_T = scbc_params.get('eta_T_turbine')
        _state6_turbine_out, _W_t_J_kg = model_turbine_T(state5_er_out, P_low_cycle_Pa, eta_T)
        if not _state6_turbine_out: return None, None, None
        state6_turbine_out, W_t_J_kg = _state6_turbine_out, _W_t_J_kg

        state6_iter = state6_turbine_out
        state7_iter = state7_htr_hot_out

        delta_h6_kJ_kg = abs(state6_iter.h - h6_old_J_kg) / 1000
        delta_h7_kJ_kg = abs(state7_iter.h - h7_old_J_kg) / 1000

        if delta_h6_kJ_kg < tol_scbc_h_kJ_kg and delta_h7_kJ_kg < tol_scbc_h_kJ_kg:
            converged_scbc_regen = True
            # print(f"  SCBC回热器在迭代 {i_scbc_regen + 1} 次后收敛。")
            break

    if not converged_scbc_regen:
        print(f"  警告: SCBC回热器在 {max_iter_scbc_regen} 次迭代后未收敛。")
        # return None, None, None # Or allow to proceed with last values

    W_t_total_J_s = W_t_J_kg * state5_er_out.m_dot if state5_er_out and state5_er_out.m_dot else 0
    W_rc_total_J_s = W_rc_J_kg * state_rc_out.m_dot if state_rc_out and state_rc_out.m_dot else 0
    W_net_scbc_J_s = W_t_total_J_s - W_mc_total_J_s - W_rc_total_J_s

    # Package all state points for returning
    scbc_states = {
        "P1_MC_In": state1, "P2_MC_Out": state2,
        "P8r_RC_In": state8r_rc_in, "P3'_RC_Out": state_rc_out,
        "P3''_LTR_ColdOut": state_ltr_cold_out, "P3_Mixed_HTR_ColdIn": state3_calc,
        "P4_HTR_ColdOut_ER_In": state4_htr_cold_out, "P5_ER_Out_Turbine_In": state5_er_out,
        "P6_Turbine_Out_HTR_HotIn": state6_turbine_out, "P7_HTR_HotOut_LTR_HotIn": state7_htr_hot_out,
        "P8_LTR_HotOut_Total": state8_calc_ltr  # This is before split to GO and RC
    }

    return Q_er_calc_J_s, W_net_scbc_J_s, scbc_states


def simulate_scbc_orc_cycle(params):
    if params is None:
        print("由于参数加载失败，无法开始仿真。")
        return

    print("\n--- 开始SCBC/ORC联合循环仿真 (固定Q_ER, 迭代质量流量) ---")
    # ... (print scbc_params as before) ...
    scbc_params = params.get("scbc_parameters", {})
    orc_params = params.get("orc_parameters", {})
    scbc_fluid = params.get("fluids", {}).get("scbc", "CO2")

    # --- 目标吸热量 ---
    Q_ER_target_MW = params.get("notes", {}).get("phi_ER_MW_heat_input", 600.0)
    Q_ER_target_J_s = Q_ER_target_MW * 1e6
    print(f"目标吸热器热量 Q_ER_target: {Q_ER_target_MW:.2f} MW")

    # --- 初始化SCBC循环起点 (点1) ---
    p1_kpa = scbc_params.get('p1_compressor_inlet_kPa')
    t1_c = scbc_params.get('T1_compressor_inlet_C')
    state1_base = StatePoint(fluid_name=scbc_fluid, name="P1_MC_In_Base")
    state1_base.props_from_PT(to_pascal(p1_kpa, 'kpa'), to_kelvin(t1_c))
    if not state1_base.h:
        print("错误: 初始化SCBC点1基础状态失败。仿真终止。")
        return

    # --- 质量流量迭代 ---
    # Initial guess for mass flow rates based on original fixed parameters
    initial_m_dot_total = scbc_params.get("m_dot_total_main_flow_kg_s", 2600.0)  # Default guess
    initial_m_dot_mc_branch = scbc_params.get("m_dot_mc_branch_kg_s", 1900.0)

    # Maintain the initial ratio of mc_branch to total flow, or rc to total flow
    # m_dot_rc_initial = initial_m_dot_total - initial_m_dot_mc_branch
    # rc_flow_ratio_of_total = m_dot_rc_initial / initial_m_dot_total if initial_m_dot_total > 0 else 0.25 # default 25% to RC

    # Let's use the ratio of mc_branch flow to total flow from original params
    mc_branch_to_total_ratio = initial_m_dot_mc_branch / initial_m_dot_total if initial_m_dot_total > 0 else (
                1945.09 / 2641.42)

    current_m_dot_total_kg_s = initial_m_dot_total  # Start with initial guess from params

    max_iter_mflow = 20  # Max iterations for mass flow
    tol_q_er_relative = 0.001  # Relative tolerance for Q_ER (0.1%)

    Q_er_calc_J_s_final = None
    W_net_scbc_J_s_final = None
    final_scbc_states = None

    print(f"\n--- 开始SCBC质量流量迭代 (目标Q_ER={Q_ER_target_MW:.2f}MW) ---")
    for i_mflow in range(max_iter_mflow):
        print(
            f"质量流量迭代 {i_mflow + 1}/{max_iter_mflow}: 当前总流量 m_dot_total = {current_m_dot_total_kg_s:.2f} kg/s")

        current_m_dot_mc_branch_kg_s = current_m_dot_total_kg_s * mc_branch_to_total_ratio
        # current_m_dot_rc_kg_s = current_m_dot_total_kg_s * rc_flow_ratio_of_total
        # current_m_dot_mc_branch_kg_s = current_m_dot_total_kg_s - current_m_dot_rc_kg_s

        # Create a fresh state1 for MC inlet with current mc_branch flow
        state1_iter_mc_in = StatePoint(fluid_name=scbc_fluid, name="P1_MC_In_MFLOW_ITER")
        state1_iter_mc_in.P = state1_base.P  # Pressure and Temp of point 1 are fixed
        state1_iter_mc_in.T = state1_base.T
        state1_iter_mc_in.h = state1_base.h  # Copy other props
        state1_iter_mc_in.s = state1_base.s
        state1_iter_mc_in.d = state1_base.d
        state1_iter_mc_in.e = state1_base.e
        state1_iter_mc_in.q = state1_base.q
        state1_iter_mc_in.m_dot = current_m_dot_mc_branch_kg_s  # Set current iteration's MC flow

        Q_er_calc_J_s, W_net_scbc_J_s, scbc_states_iter = calculate_scbc_high_temp_loop(
            params, state1_iter_mc_in, current_m_dot_total_kg_s, current_m_dot_mc_branch_kg_s
        )

        if Q_er_calc_J_s is None or W_net_scbc_J_s is None:
            print(f"  质量流量迭代 {i_mflow + 1}: SCBC高温侧计算失败。尝试调整流量。")
            # Simple adjustment: if fails, reduce flow slightly and hope it enters a more stable region
            current_m_dot_total_kg_s *= 0.95
            if current_m_dot_total_kg_s < 100:  # Lower bound to prevent too small flow
                print("  错误: 质量流量过低，迭代中止。")
                break
            continue

        Q_er_calc_J_s_final = Q_er_calc_J_s
        W_net_scbc_J_s_final = W_net_scbc_J_s
        final_scbc_states = scbc_states_iter

        error_q_er = (Q_er_calc_J_s - Q_ER_target_J_s) / Q_ER_target_J_s
        print(f"  计算得到的 Q_ER_calc = {Q_er_calc_J_s / 1e6:.2f} MW, 相对误差 = {error_q_er * 100:.2f}%")

        if abs(error_q_er) < tol_q_er_relative:
            print(f"质量流量迭代在 {i_mflow + 1} 次后收敛。")
            break

        # Simple proportional adjustment for m_dot_total
        # If Q_calc < Q_target, need more m_dot. If Q_calc > Q_target, need less m_dot.
        # Adjust m_dot proportionally to Q_target / Q_calc, with damping
        adjustment_factor = (Q_ER_target_J_s / Q_er_calc_J_s)
        damping = 0.5  # 0 < damping <= 1. Smaller means slower but more stable.
        current_m_dot_total_kg_s *= (1 + damping * (adjustment_factor - 1))

        # Ensure m_dot stays within reasonable bounds (e.g., 100 to 5000 kg/s)
        current_m_dot_total_kg_s = max(100.0, min(current_m_dot_total_kg_s, 5000.0))

        if i_mflow == max_iter_mflow - 1:
            print("警告: 质量流量迭代达到最大次数但未收敛。")

    if Q_er_calc_J_s_final is None or W_net_scbc_J_s_final is None or final_scbc_states is None:
        print("错误: SCBC循环未能成功计算。仿真终止。")
        return

    print("\n--- SCBC质量流量迭代结束 ---")
    # Ensure final_scbc_states and its keys exist before trying to access them
    if final_scbc_states and \
            final_scbc_states.get('P5_ER_Out_Turbine_In') and \
            final_scbc_states.get('P1_MC_In') and \
            final_scbc_states.get("P3'_RC_Out"):  # Check if the problematic key exists

        print(f"  最终总质量流量 m_dot_total: {final_scbc_states['P5_ER_Out_Turbine_In'].m_dot:.2f} kg/s")
        print(f"  最终主压气机支路流量 m_dot_mc_branch: {final_scbc_states['P1_MC_In'].m_dot:.2f} kg/s")

        # FIX APPLIED HERE:
        rc_outlet_key = "P3'_RC_Out"  # Define the key as a variable
        if final_scbc_states.get(rc_outlet_key) and hasattr(final_scbc_states[rc_outlet_key], 'm_dot'):
            print(f"  最终再压气机支路流量 m_dot_rc: {final_scbc_states[rc_outlet_key].m_dot:.2f} kg/s")
        else:
            print(f"  警告: 无法获取最终再压气机支路流量，键 '{rc_outlet_key}' 或其 'm_dot' 属性未找到。")

    else:
        print("  警告: final_scbc_states 中的一个或多个必需键缺失，无法打印所有最终质量流量。")

    # Print final converged SCBC states
    print("\n最终计算得到的SCBC状态点（质量流量和回热器均收敛后）:")
    if final_scbc_states:  # Check if it's not None
        for name, state_obj in final_scbc_states.items():
            print(f"点 {name}:")  # This 'name' is the key from the dictionary
            print(state_obj)
    else:
        print("  未能计算最终SCBC状态点。")

    # --- SCBC低温侧计算 (CS, GO) using converged states and flows ---
    print("\n--- SCBC低温侧计算 (使用最终流量) ---")
    state8_ltr_hot_out_final = final_scbc_states["P8_LTR_HotOut_Total"]
    m_dot_mc_branch_final = final_scbc_states["P1_MC_In"].m_dot  # This is the flow for GO hot side

    state8_go_in = StatePoint(scbc_fluid, "P8_GO_HotIn_Final")
    state8_go_in.props_from_PH(state8_ltr_hot_out_final.P, state8_ltr_hot_out_final.h)
    state8_go_in.m_dot = m_dot_mc_branch_final
    print("\n蒸发器GO SCBC热侧进口状态 (点8m):")
    print(state8_go_in)

    # 使用参数中的T9_precooler_outlet_C替代硬编码值
    T9_target_C = scbc_params.get('T9_precooler_outlet_C', 84.26)  # 从参数中读取预冷器出口温度，默认为论文值
    state9_go_hot_out, Q_go_scbc_side_J_s = model_cooler_set_T_out(
        state_in=state8_go_in, T_out_K=to_kelvin(T9_target_C), name_suffix="GO_SCBC_HotSide_Final"
    )
    if not state9_go_hot_out: print("错误: 蒸发器GO SCBC热侧计算失败。"); return
    final_scbc_states["P9_GO_HotOut_CS_In"] = state9_go_hot_out
    print("\n计算得到的蒸发器GO SCBC热侧出口状态 (点9):")
    print(state9_go_hot_out)
    if Q_go_scbc_side_J_s is not None:
        print(f"蒸发器GO SCBC热侧放出热量 Q_GO_SCBC: {abs(Q_go_scbc_side_J_s) / 1e6:.2f} MW")

    state1_cs_out_calc, Q_cs_J_s = model_cooler_set_T_out(
        state_in=state9_go_hot_out, T_out_K=to_kelvin(t1_c), name_suffix="CS_Final"
    )
    if not state1_cs_out_calc: print("错误: 主冷却器CS计算失败。"); return
    final_scbc_states["P1_CS_Out_Final"] = state1_cs_out_calc
    # ... (Print CS details and cycle closure check) ...

    # --- SCBC最终性能 ---
    W_net_scbc_MW_final = W_net_scbc_J_s_final / 1e6
    Q_in_scbc_MW_final = Q_er_calc_J_s_final / 1e6
    eta_scbc_thermal_final = W_net_scbc_MW_final / Q_in_scbc_MW_final if Q_in_scbc_MW_final > 1e-6 else 0
    print(f"\nSCBC净输出功 (最终): {W_net_scbc_MW_final:.2f} MW")
    print(f"SCBC吸热器吸热量 Q_ER (最终): {Q_in_scbc_MW_final:.2f} MW")
    print(f"SCBC热效率 (最终): {eta_scbc_thermal_final * 100:.2f}%")
    
    # 计算SCBC循环的火用效率
    # 使用状态点5的实际温度，而不是参数中的设定值，以更准确反映热力学状态
    T_er_source_K = final_scbc_states["P5_ER_Out_Turbine_In"].T if final_scbc_states and final_scbc_states.get("P5_ER_Out_Turbine_In") else to_kelvin(scbc_params.get('T5_turbine_inlet_C', 600))
    theoretical_exergy_eff = calculate_theoretical_exergy_efficiency(T_er_source_K)
    print(f"基于T5温度 {T_er_source_K-273.15:.2f}°C 的理论火用效率: {theoretical_exergy_eff * 100:.2f}%")
    eta_scbc_exergy = calculate_exergy_efficiency(Q_er_calc_J_s_final, T_er_source_K, W_net_scbc_J_s_final)
    print(f"SCBC火用效率 (最终): {eta_scbc_exergy * 100:.2f}%")
    
    # --- ORC仿真 ---
    W_net_orc_MW = 0
    eta_orc_thermal = 0
    eta_orc_exergy = 0  # 添加ORC火用效率变量
    if Q_go_scbc_side_J_s is not None and abs(Q_go_scbc_side_J_s) > 1e-6:
        # Pass necessary data to ORC simulation
        params["intermediate_results"] = {
            "Q_GO_to_ORC_J_s": abs(Q_go_scbc_side_J_s),
            "T8_GO_HotIn_K": state8_go_in.T,  # SCBC side GO inlet temp
            "T9_GO_HotOut_K": state9_go_hot_out.T  # SCBC side GO outlet temp
        }
        print("\n\n--- 开始ORC独立循环仿真 (使用SCBC最终换热数据) ---")
        orc_results = simulate_orc_standalone(
            orc_params=orc_params,
            common_params=params,  # Pass the main params dict
            intermediate_scbc_data=params["intermediate_results"]
        )
        if orc_results and orc_results.get("W_net_orc_MW") is not None:
            print("\n--- ORC独立循环仿真完成 ---")
            W_net_orc_MW = orc_results.get("W_net_orc_MW", 0)
            eta_orc_thermal = orc_results.get("eta_orc_thermal", 0)
            eta_orc_exergy = orc_results.get("eta_orc_exergy", 0)  # 获取ORC火用效率
            print(f"ORC净输出功: {W_net_orc_MW:.2f} MW")
            print(f"ORC热效率: {eta_orc_thermal * 100:.2f}%")
            print(f"ORC火用效率: {eta_orc_exergy * 100:.2f}%")  # 输出ORC火用效率
        else:
            print("ORC独立循环仿真失败或未返回有效结果。")
    else:
        print("\n由于SCBC到ORC的换热量为零或无效，跳过ORC仿真。")

    # --- 联合循环性能计算 ---
    print("\n\n--- 联合循环总性能 ---")
    W_net_combined_MW = W_net_scbc_MW_final + W_net_orc_MW
    print(f"SCBC净输出功: {W_net_scbc_MW_final:.2f} MW")
    print(f"ORC净输出功: {W_net_orc_MW:.2f} MW")
    print(f"联合循环总净输出功: {W_net_combined_MW:.2f} MW")

    if Q_in_scbc_MW_final > 1e-6:
        eta_combined_thermal = W_net_combined_MW / Q_in_scbc_MW_final
        print(f"总输入热量 (SCBC ER): {Q_in_scbc_MW_final:.2f} MW")
        print(f"联合循环总热效率: {eta_combined_thermal * 100:.2f}%")
        
        # 计算联合循环的火用效率
        W_net_combined_J_s = W_net_combined_MW * 1e6
        eta_combined_exergy = calculate_exergy_efficiency(Q_er_calc_J_s_final, T_er_source_K, W_net_combined_J_s)
        print(f"联合循环总火用效率: {eta_combined_exergy * 100:.2f}%")
        print(f"联合循环火用效率/理论火用效率: {(eta_combined_exergy/theoretical_exergy_eff) * 100:.2f}%")
    else:
        print("无法计算联合循环总热效率和火用效率，因SCBC总输入热量未知或为零。")

    print("\n--- SCBC/ORC联合循环仿真结束 ---")


# (simulate_orc_standalone function remains largely the same as your provided version,
# ensure it correctly uses intermediate_scbc_data for Q_GO_to_ORC_J_s, T8_GO_HotIn_K, T9_GO_HotOut_K)

def simulate_orc_standalone(orc_params, common_params, intermediate_scbc_data):
    """
    模拟独立的ORC循环。
    接收来自SCBC的热量进行蒸发。
    """
    orc_fluid = common_params.get("fluids", {}).get("orc", "R245fa")  # Changed default to R245fa
    print(f"ORC工质: {orc_fluid}")

    Q_from_scbc_J_s = intermediate_scbc_data.get("Q_GO_to_ORC_J_s")
    T_scbc_go_hot_in_K = intermediate_scbc_data.get("T8_GO_HotIn_K")
    T_scbc_go_hot_out_K = intermediate_scbc_data.get("T9_GO_HotOut_K")

    if not Q_from_scbc_J_s or not T_scbc_go_hot_in_K or not T_scbc_go_hot_out_K:
        print("错误: ORC仿真缺少来自SCBC的关键换热数据 (热量或温度)。")
        return None

    print(f"接收来自SCBC的热量 Q_eva_orc: {Q_from_scbc_J_s / 1e6:.2f} MW")
    print(
        f"SCBC侧GO热源温度范围: {T_scbc_go_hot_in_K - 273.15:.2f}°C (进口) to {T_scbc_go_hot_out_K - 273.15:.2f}°C (出口)")

    # ORC参数提取 from orc_params (passed into this function)
    # 使用新的参数结构
    P_eva_orc_kPa = orc_params.get('P_eva_kPa_orc')  # 蒸发压力
    
    # 使用target_pr_orc_expansion_ratio计算冷凝压力
    target_pr_orc = orc_params.get('target_pr_orc_expansion_ratio')
    P_cond_kPa_orc = P_eva_orc_kPa / target_pr_orc if target_pr_orc else None
    
    T_pump_in_C_orc = orc_params.get('T_pump_in_C_orc')  # 泵入口温度
    
    # 使用target_theta_w_orc_turbine_inlet_C计算过热度
    target_theta_w_C = orc_params.get('target_theta_w_orc_turbine_inlet_C')
    
    # 计算饱和温度以确定过热度
    _temp_sat_eva_orc_for_dT = StatePoint(orc_fluid, "_temp_sat_eva_orc_for_dT")
    _temp_sat_eva_orc_for_dT.props_from_PQ(to_pascal(P_eva_orc_kPa, 'kpa'), 1.0)  # Q=1 for saturated vapor
    
    if _temp_sat_eva_orc_for_dT.T is not None and target_theta_w_C is not None:
        T_sat_eva_C = _temp_sat_eva_orc_for_dT.T - 273.15
        delta_T_superheat_orc_K = target_theta_w_C - T_sat_eva_C
    else:
        delta_T_superheat_orc_K = None

    eta_P_orc = orc_params.get('eta_PO_pump', 0.75)  # Use eta_PO_pump as per params file
    eta_T_orc = orc_params.get('eta_TO_turbine', 0.8)  # Use eta_TO_turbine

    approach_temp_eva_K_orc = common_params.get("heat_exchangers_common", {}).get('approach_temp_eva_K_orc', 5.0)
    m_dot_orc_kg_s_initial_guess = orc_params.get('m_dot_orc_initial_guess_kg_s', 100.0)

    if any(v is None for v in [P_eva_orc_kPa, P_cond_kPa_orc, T_pump_in_C_orc, delta_T_superheat_orc_K]):
        print("错误: ORC 的一个或多个关键参数 (P_eva, P_cond, T_pump_in, delta_T_superheat) 未在参数中定义。")
        print(
            f"  P_eva: {P_eva_orc_kPa}, P_cond: {P_cond_kPa_orc}, T_pump_in: {T_pump_in_C_orc}, dT_superheat: {delta_T_superheat_orc_K}")
        return None

    print(f"\nORC主要参数 (从参数文件中读取或计算):")
    print(f"  蒸发压力 P_eva: {P_eva_orc_kPa:.2f} kPa")
    print(f"  冷凝压力 P_cond: {P_cond_kPa_orc:.2f} kPa")
    print(f"  泵进口温度 T_pump_in: {T_pump_in_C_orc:.2f} °C")
    print(f"  目标过热度 delta_T_superheat: {delta_T_superheat_orc_K:.2f} K")
    print(f"  泵效率 η_PO_pump: {eta_P_orc}")
    print(f"  透平效率 η_TO_turbine: {eta_T_orc}")
    # ... (rest of ORC simulation logic using these parameters - largely unchanged from your provided script) ...
    # Make sure point names are unique, e.g., by prefixing with "ORC_"
    orc_states = {}

    # 点o1: 泵进口 (冷凝器出口)
    state_o1_pump_in = StatePoint(orc_fluid, "ORC_P_o1_PumpIn")
    P_o1_Pa = to_pascal(P_cond_kPa_orc, 'kpa')
    # T_o1_K_param = to_kelvin(T_pump_in_C_orc) # This is the target from modify_params

    # Set pump inlet to saturated liquid at P_cond_kPa_orc, T_pump_in_C_orc should match this.
    print(f"信息: 将ORC泵进口 (点o1) 设置为在压力 {P_cond_kPa_orc:.2f} kPa下的饱和液体状态 (Q=0)。")
    state_o1_pump_in.props_from_PQ(P_o1_Pa, 0)

    if state_o1_pump_in.T is not None:
        # print(f"  计算得到的该压力下饱和温度为: {state_o1_pump_in.T - 273.15:.2f} °C (参数中T_pump_in_C_orc目标值: {T_pump_in_C_orc:.2f} °C)")
        # Check if the T_pump_in_C_orc from params (which should be Tsat at P_cond) matches the calculated Tsat
        if abs((state_o1_pump_in.T - 273.15) - T_pump_in_C_orc) > 0.1:
            print(
                f"  警告: 泵进口温度 ({T_pump_in_C_orc:.2f}°C) 与在P_cond ({P_cond_kPa_orc:.2f}kPa)下计算的饱和温度 ({state_o1_pump_in.T - 273.15:.2f}°C) 不符。将使用计算的饱和状态。")
            # This usually means P_cond from pr_orc led to a Tsat different from what T_pump_in_C was set to by modify_params
            # For consistency, it's better if modify_params sets T_pump_in_C_orc *after* P_cond is known.

    state_o1_pump_in.m_dot = m_dot_orc_kg_s_initial_guess

    if not state_o1_pump_in.h: print("错误: 初始化ORC点o1失败。"); return None
    orc_states["ORC_P_o1_PumpIn"] = state_o1_pump_in
    # print("\nORC状态点o1 (泵进口):")
    # print(state_o1_pump_in)

    P_o2_pump_out_Pa = to_pascal(P_eva_orc_kPa, 'kpa')
    state_o2_pump_out, W_p_orc_J_kg = model_pump_ORC(state_o1_pump_in, P_o2_pump_out_Pa, eta_P_orc)
    if not state_o2_pump_out: print("错误: ORC泵计算失败。"); return None
    orc_states["ORC_P_o2_PumpOut_EvaIn"] = state_o2_pump_out
    W_p_orc_total_MW = (W_p_orc_J_kg * state_o1_pump_in.m_dot) / 1e6 if state_o1_pump_in.m_dot else 0

    # ... (ORC Evaporator Iteration logic from your script - unchanged ) ...
    #   It calculates state_o3_eva_out and updated W_p_orc_total_MW
    #   Important: T_o3_final_target_K must be calculated based on delta_T_superheat_orc_K and P_eva_orc_kPa's Tsat
    # Calculate Tsat at P_eva for ORC
    _temp_sat_eva_orc = StatePoint(orc_fluid, "_temp_sat_eva_orc_calc")
    _temp_sat_eva_orc.props_from_PQ(P_o2_pump_out_Pa, 1.0)  # Q=1 for saturated vapor temp
    T_sat_orc_eva_K = _temp_sat_eva_orc.T
    if T_sat_orc_eva_K is None: print("错误: ORC无法获取蒸发饱和温度。"); return None

    T_o3_target_superheated_K = T_sat_orc_eva_K + delta_T_superheat_orc_K
    T_o3_limit_from_source_K = T_scbc_go_hot_in_K - approach_temp_eva_K_orc
    T_o3_final_target_K = min(T_o3_target_superheated_K, T_o3_limit_from_source_K)
    # Ensure it's still superheated after limit
    if T_o3_final_target_K < T_sat_orc_eva_K + 0.1:  # Small margin for superheat
        T_o3_final_target_K = T_sat_orc_eva_K + delta_T_superheat_orc_K  # Prioritize superheat
        if T_o3_final_target_K >= T_scbc_go_hot_in_K - approach_temp_eva_K_orc:
            T_o3_final_target_K = T_scbc_go_hot_in_K - approach_temp_eva_K_orc
            # print(f"  ORC警告: 过热目标可能导致违反与热源的最小温差，目标温度被限制为 {T_o3_final_target_K-273.15:.2f}°C")
            if T_o3_final_target_K <= T_sat_orc_eva_K:
                T_o3_final_target_K = T_sat_orc_eva_K + 0.1  # Force minimal superheat
                # print(f"  ORC错误: 限制后的ORC出口温度不高于饱和温度。强制微小过热。")

    # print(f"  ORC蒸发器 (GO) 计算 - 目标出口温度: {T_o3_final_target_K-273.15:.2f}°C")
    # Iteration for m_dot_orc_current_kg_s to achieve T_o3_final_target_K with Q_from_scbc_J_s
    # (This is the complex ORC evaporator iteration from your existing script)
    # Start copy of ORC evaporator iteration logic
    max_iter_orc_mdot = orc_params.get("max_iter_orc_mdot", 40)
    tol_orc_T_approach = orc_params.get("tol_orc_T_approach_K", 0.1)  # Make it tighter
    m_dot_adj_factor_high = 1.02  # Slower adjustment
    m_dot_adj_factor_low = 0.98  # Slower adjustment
    m_dot_min_kg_s = orc_params.get("m_dot_orc_min_kg_s", 1.0)
    m_dot_max_kg_s = orc_params.get("m_dot_orc_max_kg_s",
                                    Q_from_scbc_J_s / 10e3 if Q_from_scbc_J_s else 1000.0)  # Max based on min sensible enthalpy change

    m_dot_orc_current_kg_s = m_dot_orc_kg_s_initial_guess
    # Recalculate initial guess based on target T_o3
    _state_o3_guess = StatePoint(orc_fluid, "ORC_P_o3_Guess")
    _state_o3_guess.props_from_PT(P_o2_pump_out_Pa, T_o3_final_target_K)
    if _state_o3_guess.h and state_o2_pump_out.h and (_state_o3_guess.h - state_o2_pump_out.h) > 1e3:
        m_dot_orc_current_kg_s = Q_from_scbc_J_s / (_state_o3_guess.h - state_o2_pump_out.h)
        m_dot_orc_current_kg_s = max(m_dot_min_kg_s, min(m_dot_orc_current_kg_s, m_dot_max_kg_s))
        # print(f"  ORC迭代: 基于目标T计算的初始流量猜测值 m_dot={m_dot_orc_current_kg_s:.2f} kg/s")
    else:
        # print(f"  ORC迭代: 使用参数文件中的初始流量猜测值 m_dot={m_dot_orc_current_kg_s:.2f} kg/s")
        pass

    state_o3_eva_out = None
    converged_orc_mdot = False
    for i_mdot_orc in range(max_iter_orc_mdot):
        h_o3_calc_J_kg = state_o2_pump_out.h + Q_from_scbc_J_s / m_dot_orc_current_kg_s
        _temp_state_o3 = StatePoint(orc_fluid, f"ORC_P_o3_Iter{i_mdot_orc + 1}")
        _temp_state_o3.props_from_PH(state_o2_pump_out.P, h_o3_calc_J_kg)
        _temp_state_o3.m_dot = m_dot_orc_current_kg_s

        if not (_temp_state_o3.h and _temp_state_o3.T):
            # print(f"  ORC警告: 蒸发器出口状态计算失败 (Iter {i_mdot_orc+1}). 尝试调整流量。")
            m_dot_orc_current_kg_s *= (
                m_dot_adj_factor_high if error_T_K < 0 else m_dot_adj_factor_low)  # Heuristic adjustment
            m_dot_orc_current_kg_s = max(m_dot_min_kg_s, min(m_dot_max_kg_s, m_dot_orc_current_kg_s))
            continue

        T_o3_current_K = _temp_state_o3.T
        error_T_K = T_o3_current_K - T_o3_final_target_K

        is_proper_outlet_state = (_temp_state_o3.q is None or _temp_state_o3.q < 0 or _temp_state_o3.q >= 1.0) and \
                                 (
                                             T_sat_orc_eva_K is None or T_o3_current_K > T_sat_orc_eva_K - 0.01)  # Allow slight undershoot from sat if target is sat

        # print(f"  ORC Iter {i_mdot_orc+1}: m={m_dot_orc_current_kg_s:.2f}, T={T_o3_current_K-273.15:.2f}C (Tar:{T_o3_final_target_K-273.15:.2f}C), Err={error_T_K:.2f}K, Q={_temp_state_o3.q:.2f if _temp_state_o3.q is not None else 'N/A'}")

        if abs(error_T_K) < tol_orc_T_approach and is_proper_outlet_state:
            state_o3_eva_out = _temp_state_o3
            converged_orc_mdot = True
            # print(f"  ORC流量迭代收敛。")
            break

        if error_T_K > 0:
            m_dot_orc_current_kg_s *= m_dot_adj_factor_high
        else:
            m_dot_orc_current_kg_s *= m_dot_adj_factor_low
        m_dot_orc_current_kg_s = max(m_dot_min_kg_s, min(m_dot_max_kg_s, m_dot_orc_current_kg_s))
        state_o3_eva_out = _temp_state_o3  # Store last attempt

    if not converged_orc_mdot: print(f"  警告: ORC流量迭代未收敛。使用最后计算值。")
    if not state_o3_eva_out or not state_o3_eva_out.h: print(f"错误: ORC蒸发器出口最终无效。"); return None

    # Update pump outlet state and power with final m_dot
    state_o1_pump_in.m_dot = state_o3_eva_out.m_dot  # Update pump inlet m_dot
    state_o2_pump_out, W_p_orc_J_kg = model_pump_ORC(state_o1_pump_in, P_o2_pump_out_Pa, eta_P_orc)
    if not state_o2_pump_out: print("错误: ORC泵(流量更新后)计算失败。"); return None
    W_p_orc_total_MW = (W_p_orc_J_kg * state_o2_pump_out.m_dot) / 1e6 if state_o2_pump_out.m_dot else 0
    orc_states["ORC_P_o2_PumpOut_EvaIn"] = state_o2_pump_out  # Update state in dict

    # (End copy of ORC evaporator iteration logic)
    if hasattr(state_o3_eva_out,
               'q') and state_o3_eva_out.q is not None and state_o3_eva_out.q < 1.0 and state_o3_eva_out.q >= 0:
        print(
            f"  ORC最终警告: 蒸发器出口为两相流 (Q={state_o3_eva_out.q:.3f})，T={(state_o3_eva_out.T - 273.15):.2f}°C。")
    orc_states["ORC_P_o3_EvaOut_TurbineIn"] = state_o3_eva_out
    # print("\nORC状态点o3 (透平进口):")
    # print(state_o3_eva_out)
    # Q_eva_orc_calc_MW = ... (recalculate for verification if needed)

    state_o4_turbine_out, W_t_orc_J_kg = model_turbine_T(state_o3_eva_out, P_o1_Pa, eta_T_orc)
    if not state_o4_turbine_out: print("错误: ORC透平计算失败。"); return None
    orc_states["ORC_P_o4_TurbineOut_CondIn"] = state_o4_turbine_out
    W_t_orc_total_MW = (W_t_orc_J_kg * state_o3_eva_out.m_dot) / 1e6 if state_o3_eva_out.m_dot else 0

    _final_o1_cond_out = StatePoint(orc_fluid, "ORC_P_o1_CondOut_Final")  # Renamed from _final_o1
    _final_o1_cond_out.props_from_PQ(P_o1_Pa, 0)
    _final_o1_cond_out.m_dot = state_o4_turbine_out.m_dot
    orc_states["ORC_P_o1_CondOut_Calc"] = _final_o1_cond_out

    Q_cond_orc_J_s_recalc = (
                                        _final_o1_cond_out.h - state_o4_turbine_out.h) * _final_o1_cond_out.m_dot if _final_o1_cond_out.h and state_o4_turbine_out.h and _final_o1_cond_out.m_dot else None

    W_net_orc_MW_val = W_t_orc_total_MW - W_p_orc_total_MW
    eta_orc_thermal_val = W_net_orc_MW_val / (Q_from_scbc_J_s / 1e6) if (Q_from_scbc_J_s / 1e6) > 1e-6 else 0
    
    # 计算ORC的火用效率
    T_orc_source_K = T_scbc_go_hot_in_K  # 使用SCBC侧GO的入口温度作为热源温度
    W_net_orc_J_s = W_net_orc_MW_val * 1e6
    eta_orc_exergy = calculate_exergy_efficiency(Q_from_scbc_J_s, T_orc_source_K, W_net_orc_J_s)

    return {
        "orc_states": orc_states,
        "W_net_orc_MW": W_net_orc_MW_val,
        "eta_orc_thermal": eta_orc_thermal_val,
        "eta_orc_exergy": eta_orc_exergy,
        "Q_cond_orc_MW": abs(Q_cond_orc_J_s_recalc / 1e6) if Q_cond_orc_J_s_recalc else None
    }


# output_to_file and main remain the same
import sys


def output_to_file(filename, code_to_run, *args_for_code):  # Modified to accept arguments
    original_stdout = sys.stdout
    with open(filename, 'w', encoding='utf-8') as f:
        sys.stdout = f
        try:
            code_to_run(*args_for_code)  # Pass arguments here
        finally:
            sys.stdout = original_stdout


if __name__ == '__main__':
    def main_simulation_runner():  # Renamed to avoid conflict if you import this script
        cycle_params_loaded = load_cycle_parameters()  # Default filename
        if cycle_params_loaded:
            simulate_scbc_orc_cycle(cycle_params_loaded)


    # To run directly and produce the output file:
    # output_to_file("full_cycle_simulator_output.txt", main_simulation_runner)
    # print("Simulation run complete. Output redirected to full_cycle_simulator_output.txt")

    # Or for testing just the simulation logic directly:
    main_simulation_runner()