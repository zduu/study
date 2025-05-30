import json
from state_point_calculator import StatePoint, to_pascal, to_kelvin

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
    try:
        with open(params_filepath, 'r', encoding='utf-8') as f:
            params = json.load(f)
    except FileNotFoundError:
        print(f"错误: 参数文件 {params_filepath} 未找到。")
        return
    except json.JSONDecodeError:
        print(f"错误: 参数文件 {params_filepath} 格式不正确。")
        return

    # 1. 更新 SCBC 参数
    params["scbc_parameters"]["T5_turbine_inlet_C"] = new_t5_c
    params["scbc_parameters"]["PR_main_cycle_pressure_ratio"] = new_pr_scbc
    print(f"已更新 SCBC: T5_turbine_inlet_C = {new_t5_c}°C, PR_main_cycle_pressure_ratio = {new_pr_scbc}")

    # 2. 更新 ORC 参数
    orc_fluid = params["fluids"]["orc"]
    p_eva_kpa_orc = params["orc_parameters"]["P_eva_kPa_orc"]

    # 2a. 根据新的 pr_orc 计算并更新 P_cond_kPa_orc
    if new_pr_orc <= 0:
        print("错误: ORC膨胀比 pr_orc 必须大于0。")
        return
    new_p_cond_kpa_orc = p_eva_kpa_orc / new_pr_orc
    params["orc_parameters"]["P_cond_kPa_orc"] = new_p_cond_kpa_orc
    print(f"已更新 ORC: P_cond_kPa_orc = {new_p_cond_kpa_orc:.2f} kPa (基于 P_eva={p_eva_kpa_orc} kPa 和 pr_orc={new_pr_orc})")

    # 2b. 根据新的 theta_w_orc_c 计算并更新 delta_T_superheat_orc_K
    #     需要计算 P_eva_kPa_orc 下的饱和温度
    state_sat_eva_orc = StatePoint(orc_fluid, "temp_sat_eva_orc_for_delta_T")
    state_sat_eva_orc.props_from_PQ(to_pascal(p_eva_kpa_orc, 'kpa'), 1.0) # Q=1.0 表示饱和蒸汽

    if state_sat_eva_orc.T is None:
        print(f"错误: 无法获取工质 {orc_fluid} 在 {p_eva_kpa_orc} kPa 下的饱和温度。无法计算过热度。")
        return
    
    t_sat_eva_c = state_sat_eva_orc.T - 273.15
    new_delta_t_superheat_k = new_theta_w_orc_c - t_sat_eva_c
    params["orc_parameters"]["delta_T_superheat_orc_K"] = new_delta_t_superheat_k
    print(f"已更新 ORC: delta_T_superheat_orc_K = {new_delta_t_superheat_k:.2f} K (基于 theta_w={new_theta_w_orc_c}°C 和 Tsat_eva={t_sat_eva_c:.2f}°C)")

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
        with open(params_filepath, 'w', encoding='utf-8') as f:
            json.dump(params, f, indent=4, ensure_ascii=False)
        print(f"参数已成功更新并写回到 {params_filepath}")
    except IOError:
        print(f"错误: 无法写入参数文件 {params_filepath}。")

if __name__ == "__main__":
    # 示例用法：
    # 您可以修改这些值，或者从命令行参数、用户输入等方式获取
    example_new_t5_c = 599.85  # 新的SCBC透平入口温度 (°C)
    example_new_pr_scbc = 3.27   # 新的SCBC主循环压比
    example_new_pr_orc = 3.37    # 新的ORC透平膨胀比
    example_new_theta_w_orc_c = 127.76 # 新的ORC透平入口温度 (°C)

    print("开始修改循环参数...")
    update_cycle_parameters(
        new_t5_c=example_new_t5_c,
        new_pr_scbc=example_new_pr_scbc,
        new_pr_orc=example_new_pr_orc,
        new_theta_w_orc_c=example_new_theta_w_orc_c
    )
    print("参数修改脚本执行完毕。")