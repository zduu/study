# state_point_calculator.py
import numpy as np
from CoolProp.CoolProp import PropsSI
import json
import scipy.optimize

# --- 环境参考状态 (用于㶲计算) ---
# These need to be defined for StatePoint if exergy calculation is active
T0_CELSIUS = 9.56
P0_KPA = 101.382

T0_K = T0_CELSIUS + 273.15
P0_PA = P0_KPA * 1000


# --- 辅助函数 ---
def to_kelvin(T_celsius):
    """将摄氏度转换为开尔文温度"""
    return T_celsius + 273.15


def to_pascal(P_bar_or_kpa, unit='kpa'):
    """将不同单位的压力转换为帕斯卡"""
    if unit.lower() == 'kpa':
        return P_bar_or_kpa * 1000
    elif unit.lower() == 'mpa':
        return P_bar_or_kpa * 1e6
    elif unit.lower() == 'bar':
        return P_bar_or_kpa * 1e5
    return P_bar_or_kpa


# --- 核心物性计算类 ---
class StatePoint:
    def __init__(self, fluid_name, name=""):
        self.fluid = fluid_name
        self.name = name
        self.P = None;
        self.T = None;
        self.h = None;
        self.s = None
        self.d = None;
        self.e = None;
        self.q = None;
        self.m_dot = None
        try:
            self._h0 = PropsSI('H', 'T', T0_K, 'P', P0_PA, self.fluid)
            self._s0 = PropsSI('S', 'T', T0_K, 'P', P0_PA, self.fluid)
        except ValueError:
            # This can happen if T0,P0 is outside the valid range for the fluid in CoolProp
            # print(f"Warning: Could not calculate reference h0/s0 for {self.fluid} with T0={T0_K-273.15:.2f}C, P0={P0_PA/1000:.2f}kPa for StatePoint '{self.name}'. Exergy will be None.")
            self._h0 = None
            self._s0 = None
        except Exception as e_ref:  # Catch any other CoolProp or general exceptions
            # print(f"Warning: Exception during reference h0/s0 calculation for {self.fluid} (StatePoint '{self.name}'): {e_ref}. Exergy will be None.")
            self._h0 = None
            self._s0 = None

    def _calculate_exergy(self):
        if self.h is not None and self.s is not None and self._h0 is not None and self._s0 is not None:
            self.e = (self.h - self._h0) - T0_K * (self.s - self._s0)
        else:
            self.e = None

    def props_from_PT(self, P_Pa, T_K):
        self.P = P_Pa;
        self.T = T_K
        try:
            self.h = PropsSI('H', 'P', self.P, 'T', self.T, self.fluid)
            self.s = PropsSI('S', 'P', self.P, 'T', self.T, self.fluid)
            self.d = PropsSI('D', 'P', self.P, 'T', self.T, self.fluid)
            self._calculate_exergy()
        except Exception as err:
            # print(f"计算P,T物性时出错 {self.name} ({self.fluid}): {err}")
            self.h, self.s, self.d, self.e = None, None, None, None
        return self

    def props_from_PH(self, P_Pa, h_J_kg):
        self.P = P_Pa;
        self.h = h_J_kg
        try:
            self.T = PropsSI('T', 'P', self.P, 'H', self.h, self.fluid)
            self.s = PropsSI('S', 'P', self.P, 'H', self.h, self.fluid)
            self.d = PropsSI('D', 'P', self.P, 'H', self.h, self.fluid)
            try:
                self.q = PropsSI('Q', 'P', self.P, 'H', self.h, self.fluid)
            except:
                self.q = None  # Set q to None if it fails
            self._calculate_exergy()
        except Exception as err:
            # print(f"计算P,H物性时出错 {self.name} ({self.fluid}): {err}")
            self.T, self.s, self.d, self.e, self.q = None, None, None, None, None
        return self

    def props_from_PS(self, P_Pa, s_J_kgK):
        self.P = P_Pa;
        self.s = s_J_kgK
        try:
            self.T = PropsSI('T', 'P', self.P, 'S', self.s, self.fluid)
            self.h = PropsSI('H', 'P', self.P, 'S', self.s, self.fluid)
            self.d = PropsSI('D', 'P', self.P, 'S', self.s, self.fluid)
            try:
                self.q = PropsSI('Q', 'P', self.P, 'S', self.s, self.fluid)
            except:
                self.q = None  # Set q to None if it fails
            self._calculate_exergy()
        except Exception as err:
            # print(f"计算P,S物性时出错 {self.name} ({self.fluid}): {err}")
            self.T, self.h, self.d, self.e, self.q = None, None, None, None, None
        return self

    def props_from_PQ(self, P_Pa, Q_frac):
        self.P = P_Pa;
        self.q = Q_frac
        try:
            self.T = PropsSI('T', 'P', self.P, 'Q', self.q, self.fluid)
            self.h = PropsSI('H', 'P', self.P, 'Q', self.q, self.fluid)
            self.s = PropsSI('S', 'P', self.P, 'Q', self.q, self.fluid)
            self.d = PropsSI('D', 'P', self.P, 'Q', self.q, self.fluid)
            self._calculate_exergy()
        except Exception as err:
            # print(f"计算P,Q物性时出错 {self.name} ({self.fluid}): {err}")
            self.T, self.h, self.s, self.d, self.e = None, None, None, None, None
        return self

    def __str__(self):
        P_str = f"{self.P / 1e6:.3f}" if self.P is not None else "N/A"
        T_str = f"{self.T - 273.15:.2f}" if self.T is not None else "N/A"
        h_str = f"{self.h / 1e3:.2f}" if self.h is not None else "N/A"
        s_str = f"{self.s / 1e3:.4f}" if self.s is not None else "N/A"
        # MODIFIED LINE: Replaced 'kg/m³' with 'kg/m^3' for GBK compatibility
        d_str = f"{self.d:.2f} kg/m^3" if self.d is not None else "N/A kg/m^3"
        e_str = f"{self.e / 1e3:.2f}" if self.e is not None else "N/A"
        # CoolProp returns Q=-1 for single phase regions.
        # For two-phase region, Q is between 0 and 1.
        q_val_display = "N/A"
        if self.q is not None:
            if self.q < 0 or self.q > 1:  # Typically indicates single phase (supercritical, subcooled, superheated)
                q_val_display = "过热/超临界"  # These Chinese characters should be fine with GBK console
            else:  # Two-phase
                q_val_display = f"{self.q:.4f}"

        m_dot_str = f"{self.m_dot:.2f}" if self.m_dot is not None else "N/A"

        return (f"状态点: {self.name} ({self.fluid})\n"
                f"  P = {P_str} MPa\n"
                f"  T = {T_str} °C\n"
                f"  h = {h_str} kJ/kg\n"
                f"  s = {s_str} kJ/kgK\n"
                f"  d = {d_str}\n"  # Removed unit here, already in d_str
                f"  e = {e_str} kJ/kg\n"
                f"  Q = {q_val_display}\n"
                f"  m_dot = {m_dot_str} kg/s")


# --- T0/P0反推相关函数定义 (全局作用域) ---
# (The rest of the file remains the same as your uploaded version)
# ... (table10_data_for_fitting, exergy_error_func, run_t0_p0_fitting) ...
# ... (if __name__ == "__main__": block) ...

table10_data_for_fitting = [
    ("SCBC 1", "CO2", 7400.00, 35.00, 402.40, 1.66, 200.84),
    ("SCBC 2", "CO2", 24198.00, 121.73, 453.36, 1.68, 246.29),
    ("SCBC 3", "CO2", 24198.00, 281.92, 696.46, 2.21, 341.30),
    ("SCBC 4", "CO2", 24198.00, 417.94, 867.76, 2.48, 434.43),
    ("SCBC 5", "CO2", 24198.00, 599.85, 1094.91, 2.77, 579.03),
    ("SCBC 6", "CO2", 7400.00, 455.03, 932.38, 2.80, 409.40),
    ("SCBC 7", "CO2", 7400.00, 306.16, 761.08, 2.54, 312.52),
    ("SCBC 8", "CO2", 7400.00, 147.55, 582.06, 2.17, 235.75),
    ("SCBC 9", "CO2", 7400.00, 84.26, 503.44, 1.97, 214.69),
    ("ORC 09", "R245fa", 1500.00, 127.76, 505.35, 1.86, 61.21),
    ("ORC 010", "R245fa", 445.10, 94.67, 485.51, 1.88, 37.52),
    ("ORC 011", "R245fa", 445.10, 58.66, 278.39, 1.26, 5.40),
    ("ORC 012", "R245fa", 1500.00, 59.37, 279.52, 1.26, 6.29),
]


def exergy_error_func(params_T0_P0, data_points):
    T0_K_fit, P0_Pa_fit = params_T0_P0
    errors = []
    if T0_K_fit <= 0 or P0_Pa_fit <= 0: return [1e6] * len(data_points)  # Invalid parameters
    for _, fluid, _, _, h_kJ_kg, s_kJ_kgK, e_kJ_kg_paper in data_points:
        try:
            _h0 = PropsSI('H', 'T', T0_K_fit, 'P', P0_Pa_fit, fluid)
            _s0 = PropsSI('S', 'T', T0_K_fit, 'P', P0_Pa_fit, fluid)
            h_J_paper = h_kJ_kg * 1000
            s_J_paper = s_kJ_kgK * 1000
            e_calc_J = (h_J_paper - _h0) - T0_K_fit * (s_J_paper - _s0)
            errors.append(e_calc_J / 1000 - e_kJ_kg_paper)
        except Exception:
            errors.append(1e6)  # Penalize if CoolProp fails for these T0, P0
    return errors


def run_t0_p0_fitting():
    print("\n--- 开始反推参考状态 T0 和 P0 ---")
    initial_params = [298.15, 101325.0]  # Initial guess: 25°C, 1 atm
    # Bounds for T0 (e.g., 0°C to 50°C) and P0 (e.g., 80 kPa to 120 kPa)
    bounds = ([273.15, 80000.0], [323.15, 120000.0])
    try:
        result = scipy.optimize.least_squares(
            exergy_error_func, initial_params, args=(table10_data_for_fitting,), bounds=bounds, verbose=0
        )
        if result.success:
            T0_fit_K, P0_fit_Pa = result.x
            print(f"  优化成功! 反推 T0 = {T0_fit_K - 273.15:.2f} °C, P0 = {P0_fit_Pa / 1000:.3f} kPa")
            print(f"  (请注意，脚本顶部的全局 T0_K, P0_PA 仍在使用固定值进行实际计算)")
            print(f"  如需使用此反推值，请手动更新脚本顶部的 T0_CELSIUS 和 P0_KPA。")
        else:
            print(f"  优化未成功: {result.message}")
    except Exception as e_fit:
        print(f"  运行反推时发生错误: {e_fit}")


# --- 主程序块 ---
if __name__ == "__main__":
    print("--- 脚本 state_point_calculator.py 开始执行 ---")
    print(f"当前使用的全局参考状态: T0 = {T0_CELSIUS:.2f} °C ({T0_K:.2f} K), P0 = {P0_KPA:.3f} kPa ({P0_PA:.0f} Pa)")
    print("--- 正在验证表10中的所有状态点 (基于论文给定的P,T) ---")

    validation_data_from_paper_table10 = [
        # ("PointName", "Fluid", P_kPa, T_C, h_kJ_kg_paper, s_kJ_kgK_paper, e_kJ_kg_paper, m_dot_kg_s)
        ("SCBC 1", "CO2", 7400.00, 35.00, 402.40, 1.66, 200.84, 1945.09),
        ("SCBC 2", "CO2", 24198.00, 121.73, 453.36, 1.68, 246.29, 1945.09),
        ("SCBC 3", "CO2", 24198.00, 281.92, 696.46, 2.21, 341.30, 2641.42),
        ("SCBC 4", "CO2", 24198.00, 417.94, 867.76, 2.48, 434.43, 2641.42),
        ("SCBC 5", "CO2", 24198.00, 599.85, 1094.91, 2.77, 579.03, 2641.42),
        ("SCBC 6", "CO2", 7400.00, 455.03, 932.38, 2.80, 409.40, 2641.42),
        ("SCBC 7", "CO2", 7400.00, 306.16, 761.08, 2.54, 312.52, 2641.42),
        ("SCBC 8", "CO2", 7400.00, 147.55, 582.06, 2.17, 235.75, 1945.09),
        # Note: m_dot for point 8 depends on split if it's 8r or 8m
        ("SCBC 9", "CO2", 7400.00, 84.26, 503.44, 1.97, 214.69, 1945.09),
        ("ORC 09", "R245fa", 1500.00, 127.76, 505.35, 1.86, 61.21, 677.22),
        ("ORC 010", "R245fa", 445.10, 94.67, 485.51, 1.88, 37.52, 677.22),
        ("ORC 011", "R245fa", 445.10, 58.66, 278.39, 1.26, 5.40, 677.22),
        ("ORC 012", "R245fa", 1500.00, 59.37, 279.52, 1.26, 6.29, 677.22),
    ]

    output_csv_data = []
    csv_header = [
        "PointName", "Fluid", "P_kPa_input", "T_C_input", "h_kJ_kg_paper",
        "s_kJ_kgK_paper", "e_kJ_kg_paper", "m_dot_kg_s", "h_J_kg_calc", "s_J_kgK_calc",
        "d_kg_m3_calc", "T_C_calc", "e_J_kg_calc", "e_kJ_kg_calc", "e_diff_kJ_kg", "q_calc"
    ]
    output_csv_data.append(csv_header)

    print("\n详细状态点验证 (㶲对比):")
    print("=" * 140)  # Adjusted width
    print(
        f"{'状态点名':<18} {'流体':<6} {'P(kPa)':>8} {'T_in(C)':>8} {'h_calc(kJ/kg)':>13} {'s_calc(kJ/kgK)':>14} {'m_dot(kg/s)':>12} {'e_calc(kJ/kg)':>14} {'e_paper(kJ/kg)':>14} {'e_diff(kJ/kg)':>14} {'Q_calc':>10}")
    print("-" * 140)  # Adjusted width

    for name, fluid, p_kpa, t_c_input, h_kj_kg_paper, s_kj_kgk_paper, e_kj_kg_paper, m_dot_kg_s in validation_data_from_paper_table10:
        P_Pa = to_pascal(p_kpa, 'kpa')
        T_K_input = to_kelvin(t_c_input)  # Input temperature from paper

        current_state = StatePoint(fluid_name=fluid, name=name)
        current_state.props_from_PT(P_Pa, T_K_input)  # Calculate props based on P, T from paper
        current_state.m_dot = m_dot_kg_s

        h_calc_kj = current_state.h / 1000 if current_state.h is not None else float('nan')
        s_calc_kjkgk = current_state.s / 1000 if current_state.s is not None else float('nan')
        e_calc_kj = current_state.e / 1000 if current_state.e is not None else float('nan')
        e_diff_kj = e_calc_kj - e_kj_kg_paper if current_state.e is not None else float('nan')
        t_c_calc = current_state.T - 273.15 if current_state.T is not None else float('nan')

        q_display_calc = "N/A"
        if current_state.q is not None:
            if current_state.q < 0 or current_state.q > 1:
                q_display_calc = "1ph"  # Single Phase
            else:
                q_display_calc = f"{current_state.q:.2f}"

        print(
            f"{name:<18} {fluid:<6} {p_kpa:>8.2f} {t_c_input:>8.2f} {h_calc_kj:>13.2f} {s_calc_kjkgk:>14.4f} {m_dot_kg_s:>12.2f} {e_calc_kj:>14.2f} {e_kj_kg_paper:>14.2f} {e_diff_kj:>14.2f} {q_display_calc:>10}")

        csv_row = [
            name, fluid, p_kpa, t_c_input, h_kj_kg_paper, s_kj_kgk_paper, e_kj_kg_paper, m_dot_kg_s,
            current_state.h, current_state.s, current_state.d, t_c_calc,
            current_state.e, e_calc_kj, e_diff_kj, current_state.q
        ]
        output_csv_data.append(csv_row)
    print("=" * 140)

    csv_filename = "calculated_state_points_from_table10.csv"
    try:
        import csv

        with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:  # Ensure UTF-8 for CSV
            writer = csv.writer(csvfile)
            writer.writerows(output_csv_data)
        print(f"\n状态点数据已成功导出到: {csv_filename}")
    except Exception as e_csv:
        print(f"\n导出到CSV文件时出错: {e_csv}")

    print("\n尝试执行T0/P0反推 (如果需要)...")
    # run_t0_p0_fitting() # Uncomment to run fitting

    print("\n--- 正在输出循环设定参数到 cycle_setup_parameters.json ---")
    # Parameters used for the GA optimization as per paper's Table 8 (optimized values)
    # SCBC/ORC system: PR=3.27, θ5=599.85°C, θw=127.76°C, pr=3.37
    cycle_parameters = {
        "fluids": {"scbc": "CO2", "orc": "R245fa"},
        "reference_conditions": {"T0_C": T0_CELSIUS, "P0_kPa": P0_KPA},
        "scbc_parameters": {
            "p1_compressor_inlet_kPa": 7400.0,  # Base value from paper Table 10
            "T1_compressor_inlet_C": 35.0,  # Base value
            # These will be varied by the GA, but we need initial/default values.
            # Let's use the optimized values from paper Table 8 for SCBC/ORC as defaults.
            "T5_turbine_inlet_C": 599.85,  # θ5 from Table 8
            "PR_main_cycle_pressure_ratio": 3.27,  # PR from Table 8
            "eta_T_turbine": 0.9,  # From paper Table 6
            "eta_C_compressor": 0.85,  # From paper Table 6 (assumed for MC and RC)
            "eta_H_HTR_effectiveness": 0.86,  # From paper Table 6
            "eta_L_LTR_effectiveness": 0.86,  # From paper Table 6
            # Parameters for iteration control in full_cycle_simulator
            "max_iter_scbc_main_loop": 20,
            "tol_scbc_h_kJ_kg": 0.1,
            "m_dot_total_main_flow_kg_s": 2641.42,  # From paper Table 10 (e.g. point 3)
            "m_dot_mc_branch_kg_s": 1945.09,  # From paper Table 10 (e.g. point 1)
        },
        "orc_parameters": {
            # These will also be varied. Using Table 8 (SCBC/ORC) as defaults.
            # P_eva_kPa_orc: From paper Table 10, point 09 (1500.0 kPa)
            # P_cond_kPa_orc: From paper Table 10, point 010/011 (445.10 kPa)
            # pr_orc = P_eva / P_cond = 1500.0 / 445.10 = 3.369... ~ 3.37 (matches Table 8)
            "P_eva_kPa_orc": 1500.0,
            # "P_cond_kPa_orc": 445.10, # This will be calculated from P_eva and pr_orc by modify_cycle_parameters
            "T_pump_in_C_orc": 58.66,  # From paper Table 10, point 011 (saturated liquid at P_cond)
            # This will also be re-calculated by modify_cycle_parameters
            # delta_T_superheat_orc_K : calculated from theta_w_c and P_eva_orc's Tsat
            # theta_w_c (ORC turbine inlet T): 127.76 °C from Table 8
            # pr_orc (ORC expansion ratio): 3.37 from Table 8
            "target_theta_w_orc_turbine_inlet_C": 127.76,  # This is the GA variable theta_w
            "target_pr_orc_expansion_ratio": 3.37,  # This is the GA variable pr
            "eta_TO_turbine": 0.8,  # From paper Table 6
            "eta_PO_pump": 0.75,  # Common assumption, paper Table 6 doesn't list ORC pump eff. Value from readme.
            # Iteration control for ORC
            "max_iter_orc_mdot": 40,
            "tol_orc_T_approach_K": 0.1,  # Tighter tolerance for ORC outlet temp
            "m_dot_orc_initial_guess_kg_s": 100.0  # Initial guess for ORC mass flow
        },
        "heat_exchangers_common": {
            "min_temp_diff_pinch_C": 10.0,  # General pinch point, from paper assumptions
            "approach_temp_eva_K_orc": 5.0  # For GO, ORC outlet vs SCBC hot inlet, from readme
        },
        "notes": {
            "phi_ER_MW_heat_input": 600.0,  # From paper Table 6
            "cost_fuel_cQ_dollar_per_MWh": 7.4  # From paper Table 6
        }
    }
    params_filename = "cycle_setup_parameters.json"
    try:
        with open(params_filename, 'w', encoding='utf-8') as f:
            json.dump(cycle_parameters, f, ensure_ascii=False, indent=4)
        print(f"循环设定参数已成功导出到: {params_filename}")
    except Exception as e_json:
        print(f"\n导出循环设定参数到JSON文件时出错: {e_json}")

    print("\n--- 脚本 state_point_calculator.py 执行完毕 ---")
