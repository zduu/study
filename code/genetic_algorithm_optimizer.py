# genetic_algorithm_optimizer.py
import random
import subprocess
import re
import json
import os
import numpy as np
import time
import csv  # 确保导入csv模块

# --- Configuration ---
# GA Parameters
POPULATION_SIZE = 50
MAX_GENERATIONS = 100  # 算法迭代步数 T
CROSSOVER_PROBABILITY = 0.9  # 交叉概率 Pc
MUTATION_PROBABILITY = 0.25  # 变异概率 Pm = 1/n, n=4
TOURNAMENT_SIZE = 3

# Decision Variable Boundaries (from paper Table 7)
VAR_BOUNDS = {
    "theta_5_c": (500.0, 600.0),
    "pr_scbc": (2.2, 4.0),
    "theta_w_c": (100.0, 130.0),
    "pr_orc": (2.2, 4.0)
}
VAR_NAMES = ["theta_5_c", "pr_scbc", "theta_w_c", "pr_orc"]

# Paths to your existing scripts
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODIFY_PARAMS_SCRIPT = os.path.join(SCRIPT_DIR, "modify_cycle_parameters.py")
SIMULATOR_SCRIPT = os.path.join(SCRIPT_DIR, "full_cycle_simulator.py")

# 获取项目根目录和output文件夹路径
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
PARAMS_JSON_FILE = os.path.join(OUTPUT_DIR, "cycle_setup_parameters.json")

# 如果output文件夹不存在，则尝试使用当前目录中的文件
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
if not os.path.exists(PARAMS_JSON_FILE):
    PARAMS_JSON_FILE = os.path.join(SCRIPT_DIR, "cycle_setup_parameters.json")

# Fitness function weights: F(x) = alpha*eta_t + beta*eta_e - gamma*C(x)
# Setting alpha and beta for thermal and exergy efficiency, gamma for cost (currently 0)
ALPHA = 0.6  # 权重 for 热效率 (eta_t)
BETA = 0.4  # 权重 for 㶲效率 (eta_e)
GAMMA = 0.0  # 权重 for 成本 (C(x)) - 保持为0，因为成本项未实现

if abs((ALPHA + BETA) - 1.0) > 1e-6 and GAMMA == 0.0 and (ALPHA > 0 or BETA > 0):
    print(f"注意: 当只考虑热效率和㶲效率时，通常建议 ALPHA + BETA = 1.0。当前 ALPHA={ALPHA}, BETA={BETA}")
    # 可以选择规范化 ALPHA 和 BETA，或者按原样使用
    # total_eff_weight = ALPHA + BETA
    # if total_eff_weight > 0:
    #     ALPHA /= total_eff_weight
    #     BETA /= total_eff_weight
    #     print(f"  已规范化权重: ALPHA={ALPHA:.2f}, BETA={BETA:.2f}")


# --- Helper Functions ---
def check_scripts_exist():
    """Checks if the required Python scripts exist."""
    if not os.path.exists(MODIFY_PARAMS_SCRIPT):
        print(f"错误: 脚本 '{MODIFY_PARAMS_SCRIPT}' 未找到。")
        return False
    if not os.path.exists(SIMULATOR_SCRIPT):
        print(f"错误: 脚本 '{SIMULATOR_SCRIPT}' 未找到。")
        return False
    return True


def decode_subprocess_output(byte_string):
    """Decodes byte string from subprocess, trying utf-8 then gbk."""
    if byte_string is None:
        return ""
    try:
        return byte_string.decode('utf-8')
    except UnicodeDecodeError:
        return byte_string.decode('gbk', errors='replace')


def parse_simulator_output(output_text):
    """
    Parses the output of full_cycle_simulator.py to extract performance metrics.
    Returns a dictionary with 'thermal_efficiency', 'exergy_efficiency', 'cost'.
    """
    results = {
        "thermal_efficiency": None,
        "exergy_efficiency": None,
        "cost": None  # Placeholder for cost if ever implemented
    }
    if output_text is None:
        output_text = ""

    try:
        # 解析总热效率
        eff_match = re.search(r"联合循环总热效率:\s*([\d\.]+)\s*%", output_text)
        if eff_match:
            results["thermal_efficiency"] = float(eff_match.group(1)) / 100.0

        # 解析总㶲效率 (MODIFIED)
        exergy_eff_match = re.search(r"联合循环总㶲效率:\s*([\d\.]+)\s*%", output_text)  # 假设的输出格式
        if exergy_eff_match:
            results["exergy_efficiency"] = float(exergy_eff_match.group(1)) / 100.0
        else:
            # Fallback: Try to parse SCBC exergy efficiency if combined is not available
            # This is just an example, adjust if your output is different
            scbc_exergy_match = re.search(r"SCBC㶲效率 \(最终\):\s*([\d\.]+)\s*%", output_text)
            if scbc_exergy_match and BETA > 0:  # Only parse if BETA is set
                print("    警告: 未找到联合循环总㶲效率，尝试使用 SCBC 㶲效率作为替代。")
                # results["exergy_efficiency"] = float(scbc_exergy_match.group(1)) / 100.0
                # For now, let's be strict: if combined exergy efficiency is not found, it's None for the combined fitness.
                # If you want to use SCBC exergy efficiency as a proxy, uncomment the line above.

        # (Future: Parse cost if implemented)
        # cost_match = re.search(r"系统单位㶲成本:\s*([\d\.]+)\s*\$/GJ", output_text)
        # if cost_match:
        #     results["cost"] = float(cost_match.group(1))

    except Exception as e:
        error_output_display = output_text if isinstance(output_text, str) else "N/A (output_text was not a string)"
        print(f"解析模拟器输出时出错: {e}\n输出内容 (前500字符):\n{error_output_display[:500]}...")
    return results


# --- Genetic Algorithm Core Functions ---
def create_individual():
    """Creates a single individual with random genes within bounds."""
    individual = {
        "genes": {
            VAR_NAMES[0]: random.uniform(VAR_BOUNDS[VAR_NAMES[0]][0], VAR_BOUNDS[VAR_NAMES[0]][1]),
            VAR_NAMES[1]: random.uniform(VAR_BOUNDS[VAR_NAMES[1]][0], VAR_BOUNDS[VAR_NAMES[1]][1]),
            VAR_NAMES[2]: random.uniform(VAR_BOUNDS[VAR_NAMES[2]][0], VAR_BOUNDS[VAR_NAMES[2]][1]),
            VAR_NAMES[3]: random.uniform(VAR_BOUNDS[VAR_NAMES[3]][0], VAR_BOUNDS[VAR_NAMES[3]][1]),
        },
        "fitness": -float('inf'),
        "metrics": {"eta_t": None, "eta_e": None, "cost_c": None}  # To store individual metrics
    }
    return individual


def initialize_population():
    """Initializes the population with random individuals."""
    return [create_individual() for _ in range(POPULATION_SIZE)]


def calculate_fitness(individual, generation_num, individual_num):
    """
    Calculates the fitness of an individual by running the simulation.
    Now returns a tuple: (fitness, eta_t, eta_e, cost_c)
    """
    genes = individual["genes"]
    # ... (print statement for evaluating individual - unchanged) ...
    print(f"  Gen {generation_num}, Ind {individual_num}: 评估个体 - "
          f"θ5={genes[VAR_NAMES[0]]:.2f}°C, PR_scbc={genes[VAR_NAMES[1]]:.2f}, "
          f"θw={genes[VAR_NAMES[2]]:.2f}°C, PR_orc={genes[VAR_NAMES[3]]:.2f}")

    # 1. Modify cycle parameters
    cmd_modify = [
        "python", MODIFY_PARAMS_SCRIPT,
        "--t5_c", str(genes[VAR_NAMES[0]]),
        "--pr_scbc", str(genes[VAR_NAMES[1]]),
        "--theta_w_c", str(genes[VAR_NAMES[2]]),
        "--pr_orc", str(genes[VAR_NAMES[3]])
    ]
    try:
        subprocess.run(cmd_modify, capture_output=True, check=True, timeout=60)
    except subprocess.CalledProcessError as e:
        stdout_str = decode_subprocess_output(e.stdout)
        stderr_str = decode_subprocess_output(e.stderr)
        print(
            f"    错误: 执行 '{MODIFY_PARAMS_SCRIPT}' 失败. 返回码: {e.returncode}\n    stdout: {stdout_str}\n    stderr: {stderr_str}")
        return -float('inf'), None, None, None
    # ... (other exception handling for modify_proc - unchanged) ...
    except subprocess.TimeoutExpired:
        print(f"    错误: 执行 '{MODIFY_PARAMS_SCRIPT}' 超时。")
        return -float('inf'), None, None, None
    except FileNotFoundError:
        print(f"    错误: 脚本 '{MODIFY_PARAMS_SCRIPT}' 或 python 解释器未找到。")
        return -float('inf'), None, None, None
    except Exception as e:
        print(f"    运行 '{MODIFY_PARAMS_SCRIPT}' 时发生意外的子流程错误: {e}")
        return -float('inf'), None, None, None

    # 2. Run full cycle simulator
    cmd_simulate = ["python", SIMULATOR_SCRIPT]
    output_text, stderr_text_sim = "", ""
    try:
        simulate_proc = subprocess.run(cmd_simulate, capture_output=True, timeout=300)
        if simulate_proc.stdout: output_text = decode_subprocess_output(simulate_proc.stdout)
        if simulate_proc.stderr: stderr_text_sim = decode_subprocess_output(simulate_proc.stderr)
        if simulate_proc.returncode != 0:
            print(f"    警告: '{SIMULATOR_SCRIPT}' 返回码: {simulate_proc.returncode}")
            if stderr_text_sim: print(f"    模拟器错误输出 (部分): {stderr_text_sim[:500]}...")
    # ... (other exception handling for simulate_proc - unchanged) ...
    except subprocess.TimeoutExpired:
        print(f"    错误: 执行 '{SIMULATOR_SCRIPT}' 超时。")
        return -float('inf'), None, None, None
    except FileNotFoundError:
        print(f"    错误: 脚本 '{SIMULATOR_SCRIPT}' 或 python 解释器未找到。")
        return -float('inf'), None, None, None
    except Exception as e:
        print(f"    运行 '{SIMULATOR_SCRIPT}' 时发生意外的子流程错误: {e}")
        return -float('inf'), None, None, None

    # 3. Parse output and calculate fitness
    sim_results = parse_simulator_output(output_text)
    eta_t = sim_results["thermal_efficiency"]
    eta_e = sim_results["exergy_efficiency"]
    cost_c = sim_results["cost"]  # Remains None if not parsed

    current_fitness = -float('inf')  # Default to very low fitness

    if eta_t is None and BETA > 0 and eta_e is None:  # If primary metrics for fitness are missing
        print(f"    警告: 热效率和㶲效率均未能解析。将赋一个非常低的适应度。")
    elif eta_t is None and ALPHA > 0:
        print(f"    警告: 热效率未能解析 (ALPHA={ALPHA}>0)。将赋一个非常低的适应度。")
    elif eta_e is None and BETA > 0:
        print(f"    警告: 㶲效率未能解析 (BETA={BETA}>0)。将赋一个非常低的适应度。")
    else:
        # Calculate fitness based on available metrics and weights
        calculated_fitness_value = 0
        if ALPHA > 0 and eta_t is not None:
            calculated_fitness_value += ALPHA * eta_t
        if BETA > 0 and eta_e is not None:
            calculated_fitness_value += BETA * eta_e
        if GAMMA > 0 and cost_c is not None:  # Assuming cost should be minimized
            # If cost_c is large, this term can dominate. Normalization or careful GAMMA selection needed.
            # For now, simple subtraction. If cost is to be maximized (e.g. profit), then add.
            calculated_fitness_value -= GAMMA * cost_c

            # If no weighted terms contributed (e.g. all relevant metrics were None, or weights were zero)
        # but at least one desired metric WAS parsed, use a default logic (e.g. just eta_t if available)
        if calculated_fitness_value == 0 and ((ALPHA > 0 and eta_t is not None) or (BETA > 0 and eta_e is not None)):
            # This case means weights might be zero or metrics summed to zero.
            # If ALPHA=0.5, BETA=0.5, this shouldn't happen if eta_t or eta_e is positive.
            pass  # It's possible to have zero fitness if efficiencies are zero.
        elif calculated_fitness_value == 0 and not (
                (ALPHA > 0 and eta_t is not None) or (BETA > 0 and eta_e is not None)):
            # This means no relevant metric (eta_t or eta_e, if their weights are >0) was parsed.
            # This case is already handled by the None checks above.
            pass

        current_fitness = calculated_fitness_value

    eta_t_str = f"{eta_t * 100:.2f}%" if eta_t is not None else "N/A"
    eta_e_str = f"{eta_e * 100:.2f}%" if eta_e is not None else "N/A"
    cost_c_str = f"{cost_c:.2f}" if cost_c is not None else "N/A"
    print(f"    模拟结果: η_t={eta_t_str}, η_e={eta_e_str}, C={cost_c_str}. Fitness={current_fitness:.4f}")

    return current_fitness, eta_t, eta_e, cost_c


# ... (tournament_selection, crossover, mutate functions remain unchanged) ...
def tournament_selection(population):
    """Selects an individual using tournament selection."""
    tournament = random.sample(population, TOURNAMENT_SIZE)
    return max(tournament, key=lambda ind: ind["fitness"])


def crossover(parent1, parent2):
    """Performs simple arithmetic crossover."""
    child1_genes = {}
    child2_genes = {}
    alpha_blend = 0.5  # Blend factor, can be tuned

    for var_name in VAR_NAMES:
        p1_gene = parent1["genes"][var_name]
        p2_gene = parent2["genes"][var_name]

        child1_genes[var_name] = alpha_blend * p1_gene + (1 - alpha_blend) * p2_gene
        child2_genes[var_name] = (1 - alpha_blend) * p1_gene + alpha_blend * p2_gene

        child1_genes[var_name] = max(VAR_BOUNDS[var_name][0], min(child1_genes[var_name], VAR_BOUNDS[var_name][1]))
        child2_genes[var_name] = max(VAR_BOUNDS[var_name][0], min(child2_genes[var_name], VAR_BOUNDS[var_name][1]))

    # Children inherit -inf fitness; to be recalculated
    # Also create the metrics structure
    return {"genes": child1_genes, "fitness": -float('inf'), "metrics": {"eta_t": None, "eta_e": None, "cost_c": None}}, \
        {"genes": child2_genes, "fitness": -float('inf'), "metrics": {"eta_t": None, "eta_e": None, "cost_c": None}}


def mutate(individual):
    """Performs mutation on an individual's genes."""
    mutated_genes = individual["genes"].copy()
    for var_name in VAR_NAMES:
        if random.random() < MUTATION_PROBABILITY:
            bound_min, bound_max = VAR_BOUNDS[var_name]
            range_width = bound_max - bound_min

            perturbation = random.gauss(0, range_width * 0.1)
            mutated_genes[var_name] += perturbation

            mutated_genes[var_name] = max(bound_min, min(mutated_genes[var_name], bound_max))
    # Mutated individual needs fitness recalculation
    return {"genes": mutated_genes, "fitness": -float('inf'), "metrics": {"eta_t": None, "eta_e": None, "cost_c": None}}


# --- Main GA Loop ---
def run_genetic_algorithm():
    if not check_scripts_exist(): return None
    start_time = time.time()
    population = initialize_population()
    best_overall_individual = None

    # 设置日志文件路径到output文件夹
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    log_filename = os.path.join(OUTPUT_DIR, "ga_optimization_log.csv")
    
    with open(log_filename, 'w', encoding='utf-8', newline='') as log_file:
        log_writer = csv.writer(log_file)
        log_writer.writerow(["Generation", "Individual", "theta_5_c", "pr_scbc", "theta_w_c", "pr_orc",
                             "Fitness", "ThermalEfficiency", "ExergyEfficiency", "Cost"])

        print(f"遗传算法开始。种群大小: {POPULATION_SIZE}, 最大代数: {MAX_GENERATIONS}")
        print(f"决策变量: {VAR_NAMES}, 边界: {VAR_BOUNDS}")
        print(f"适应度权重: α(η_t)={ALPHA}, β(η_e)={BETA}, γ(C)={GAMMA}")
        print(f"详细日志将保存在: {log_filename}")

        for generation in range(MAX_GENERATIONS):
            print(f"\n--- 第 {generation + 1} 代 ---")
            gen_start_time = time.time()

            for i, ind in enumerate(population):
                # calculate_fitness now returns (fitness, eta_t, eta_e, cost_c)
                fitness_val, eta_t_val, eta_e_val, cost_c_val = calculate_fitness(ind, generation + 1, i + 1)
                ind["fitness"] = fitness_val
                ind["metrics"]["eta_t"] = eta_t_val
                ind["metrics"]["eta_e"] = eta_e_val
                ind["metrics"]["cost_c"] = cost_c_val

                genes = ind["genes"]
                log_writer.writerow([
                    generation + 1, i + 1,
                    f"{genes[VAR_NAMES[0]]:.4f}", f"{genes[VAR_NAMES[1]]:.4f}",
                    f"{genes[VAR_NAMES[2]]:.4f}", f"{genes[VAR_NAMES[3]]:.4f}",
                    f"{ind['fitness']:.6f}",
                    f"{ind['metrics']['eta_t']:.6f}" if ind['metrics']['eta_t'] is not None else "N/A",
                    f"{ind['metrics']['eta_e']:.6f}" if ind['metrics']['eta_e'] is not None else "N/A",
                    f"{ind['metrics']['cost_c']:.4f}" if ind['metrics']['cost_c'] is not None else "N/A"
                ])
                log_file.flush()

                if best_overall_individual is None or ind["fitness"] > best_overall_individual["fitness"]:
                    best_overall_individual = ind.copy()  # Deep copy
                    print(
                        f"  ** 新的最优个体 (第 {generation + 1} 代, 个体 {i + 1}): Fitness = {best_overall_individual['fitness']:.4f} **")
                    print(f"     基因: {best_overall_individual['genes']}")
                    eta_t_disp = f"{best_overall_individual['metrics']['eta_t'] * 100:.2f}%" if \
                    best_overall_individual['metrics']['eta_t'] is not None else "N/A"
                    eta_e_disp = f"{best_overall_individual['metrics']['eta_e'] * 100:.2f}%" if \
                    best_overall_individual['metrics']['eta_e'] is not None else "N/A"
                    print(f"     对应指标: η_t={eta_t_disp}, η_e={eta_e_disp}")

            population.sort(key=lambda ind: ind["fitness"], reverse=True)
            if not population: print("错误: 种群为空!"); break

            current_best_in_gen = population[0]
            print(f"第 {generation + 1} 代最优: Fitness = {current_best_in_gen['fitness']:.4f}")
            # ... (rest of generation summary prints unchanged) ...
            if best_overall_individual:
                print(f"历史最优: Fitness = {best_overall_individual['fitness']:.4f}")
                best_genes_str = ", ".join([f"{k}={v:.2f}" for k, v in best_overall_individual['genes'].items()])
                print(f"  基因: {best_genes_str}")
                best_eta_t_str = f"{best_overall_individual['metrics']['eta_t'] * 100:.2f}%" if \
                best_overall_individual['metrics']['eta_t'] is not None else "N/A"
                best_eta_e_str = f"{best_overall_individual['metrics']['eta_e'] * 100:.2f}%" if \
                best_overall_individual['metrics']['eta_e'] is not None else "N/A"
                print(f"  对应指标: η_t={best_eta_t_str}, η_e={best_eta_e_str}")

            next_population = [population[0].copy()] if population else []  # Elitism

            while len(next_population) < POPULATION_SIZE:
                parent1 = tournament_selection(population)
                parent2 = tournament_selection(population)
                child1, child2 = parent1.copy(), parent2.copy()
                if random.random() < CROSSOVER_PROBABILITY:
                    child1_co, child2_co = crossover(parent1, parent2)
                    child1, child2 = child1_co, child2_co
                next_population.append(mutate(child1))
                if len(next_population) < POPULATION_SIZE:
                    next_population.append(mutate(child2))
            population = next_population
            gen_end_time = time.time()
            print(f"第 {generation + 1} 代耗时: {gen_end_time - gen_start_time:.2f} 秒")

    # ... (Final print section for best_overall_individual - unchanged, but will now benefit from metrics stored in best_overall_individual) ...
    total_end_time = time.time()
    print("\n--- 遗传算法结束 ---")
    print(f"总耗时: {total_end_time - start_time:.2f} 秒")

    if best_overall_individual:
        print("\n找到的最优个体:")
        print(f"  基因 (决策变量):")
        for var_name, value in best_overall_individual["genes"].items():
            print(f"    {var_name}: {value:.4f}")
        print(f"  适应度值: {best_overall_individual['fitness']:.6f}")

        print("\n使用最优基因重新运行模拟以获取详细指标 (这些指标已在优化过程中记录):")
        final_metrics = best_overall_individual["metrics"]  # Use stored metrics

        print("\n最优参数下的性能指标 (来自优化过程中的最佳记录):")
        final_eta_t_str = f"{final_metrics['eta_t'] * 100:.2f}%" if final_metrics['eta_t'] is not None else "未能解析"
        final_eta_e_str = f"{final_metrics['eta_e'] * 100:.2f}%" if final_metrics['eta_e'] is not None else "N/A"
        final_cost_c_str = f"{final_metrics['cost_c']:.2f}" if final_metrics['cost_c'] is not None else "N/A"

        print(f"  总热效率 η_t: {final_eta_t_str}")
        if BETA > 0 or final_metrics['eta_e'] is not None:
            print(f"  总㶲效率 η_e: {final_eta_e_str}")  # Changed from 㶲效率 to 总㶲效率 for clarity
        if GAMMA > 0 or final_metrics['cost_c'] is not None:
            print(f"  成本 C: {final_cost_c_str}")

        # Optional: Still re-run simulation if you want the full text output for the absolute best
        # This is useful if calculate_fitness simplified or didn't store all details
        # For now, we rely on the stored metrics.
        # print("\n(为获取完整输出文本，将再次运行最优模拟...)")
        # ... (code to re-run simulation as before, if needed for full text log) ...

    else:
        print("未能找到最优个体。")

    return best_overall_individual


if __name__ == "__main__":
    best_solution = run_genetic_algorithm()

