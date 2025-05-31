# genetic_algorithm_optimizer.py
import random
import subprocess
import re
import json
import os
import numpy as np
import time

# --- Configuration ---
# GA Parameters (based on paper and flowchart)
POPULATION_SIZE = 50  # Typical population size
MAX_GENERATIONS = 100  # Max iterations T from paper
CROSSOVER_PROBABILITY = 0.9  # Pc from paper
MUTATION_PROBABILITY = 0.25  # Pm = 1/n, where n=4 decision variables (from paper)
TOURNAMENT_SIZE = 3  # For tournament selection

# Decision Variable Boundaries (from paper Table 7)
# Gene 0: theta_5_scbc_turbine_inlet_temp_c (SCBC透平入口温度 °C)
# Gene 1: pr_scbc_pressure_ratio (SCBC主循环压比)
# Gene 2: theta_w_orc_turbine_inlet_temp_c (ORC透平入口温度 °C)
# Gene 3: pr_orc_expansion_ratio (ORC透平膨胀比)
VAR_BOUNDS = {
    "theta_5_c": (500.0, 600.0),
    "pr_scbc": (2.2, 4.0),
    "theta_w_c": (100.0, 130.0),
    "pr_orc": (2.2, 4.0)
}
VAR_NAMES = ["theta_5_c", "pr_scbc", "theta_w_c", "pr_orc"]

# Paths to your existing scripts
MODIFY_PARAMS_SCRIPT = "modify_cycle_parameters.py"
SIMULATOR_SCRIPT = "full_cycle_simulator.py"
PARAMS_JSON_FILE = "cycle_setup_parameters.json"  # Default params file used by modify_cycle_parameters.py

# Fitness function weights (from flowchart: F(x) = alpha*eta_t + beta*eta_e - gamma*C(x))
# For now, as simulator only reliably gives eta_t, we'll set:
ALPHA = 1.0  # Weight for thermal efficiency
BETA = 0.0  # Weight for exergy efficiency (set to 0 if not available)
GAMMA = 0.0  # Weight for cost (set to 0 if not available)


# Ensure alpha + beta = 1 if both are used and gamma is for penalty/cost minimization

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
        # print("    警告: Subprocess output was not UTF-8, trying GBK...")
        return byte_string.decode('gbk', errors='replace')  # 'replace' to avoid crashing on further errors


def parse_simulator_output(output_text):
    """
    Parses the output of full_cycle_simulator.py to extract performance metrics.
    Returns a dictionary with 'thermal_efficiency', 'exergy_efficiency', 'cost'.
    If a metric is not found, its value will be None.
    """
    results = {
        "thermal_efficiency": None,
        "exergy_efficiency": None,  # Placeholder
        "cost": None  # Placeholder
    }
    if output_text is None:  # Ensure output_text is a string
        output_text = ""

    try:
        # Example: "联合循环总热效率: 42.44%"
        eff_match = re.search(r"联合循环总热效率:\s*([\d\.]+)\s*%", output_text)
        if eff_match:
            results["thermal_efficiency"] = float(eff_match.group(1)) / 100.0  # Convert to fraction

        # Add parsing for exergy efficiency and cost if your simulator outputs them
        # For example:
        # exergy_eff_match = re.search(r"联合循环㶲效率:\s*([\d\.]+)\s*%", output_text)
        # if exergy_eff_match:
        #     results["exergy_efficiency"] = float(exergy_eff_match.group(1)) / 100.0
        #
        # cost_match = re.search(r"系统单位㶲成本:\s*([\d\.]+)\s*\$/GJ", output_text) # Or similar
        # if cost_match:
        #     results["cost"] = float(cost_match.group(1))

    except Exception as e:
        # Ensure output_text is a string for slicing in the error message
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
        "fitness": -float('inf')  # Initialize with a very low fitness
    }
    return individual


def initialize_population():
    """Initializes the population with random individuals."""
    return [create_individual() for _ in range(POPULATION_SIZE)]


def calculate_fitness(individual, generation_num, individual_num):
    """
    Calculates the fitness of an individual by running the simulation.
    """
    genes = individual["genes"]

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
        modify_proc = subprocess.run(cmd_modify, capture_output=True, check=True, timeout=60)
        # modify_stdout_str = decode_subprocess_output(modify_proc.stdout)
        # print(f"    修改参数成功: {modify_stdout_str.strip()}")
    except subprocess.CalledProcessError as e:
        stdout_str = decode_subprocess_output(e.stdout)
        stderr_str = decode_subprocess_output(e.stderr)
        print(f"    错误: 执行 '{MODIFY_PARAMS_SCRIPT}' 失败. 返回码: {e.returncode}")
        print(f"    错误输出: {stderr_str.strip()}")
        print(f"    标准输出: {stdout_str.strip()}")
        return -float('inf')
    except subprocess.TimeoutExpired:
        print(f"    错误: 执行 '{MODIFY_PARAMS_SCRIPT}' 超时。")
        return -float('inf')
    except FileNotFoundError:
        print(f"    错误: 脚本 '{MODIFY_PARAMS_SCRIPT}' 或 python 解释器未找到。")
        return -float('inf')
    except Exception as e:
        print(f"    运行 '{MODIFY_PARAMS_SCRIPT}' 时发生意外的子流程错误: {e}")
        return -float('inf')

    # 2. Run full cycle simulator
    cmd_simulate = ["python", SIMULATOR_SCRIPT]
    output_text = ""  # Initialize to empty string
    stderr_text_sim = ""
    try:
        simulate_proc = subprocess.run(cmd_simulate, capture_output=True, timeout=300)  # No check=True

        if simulate_proc.stdout:
            output_text = decode_subprocess_output(simulate_proc.stdout)
        if simulate_proc.stderr:
            stderr_text_sim = decode_subprocess_output(simulate_proc.stderr)

        if simulate_proc.returncode != 0:
            print(f"    警告: 执行 '{SIMULATOR_SCRIPT}' 完成但返回码: {simulate_proc.returncode}")
            if stderr_text_sim:
                print(f"    模拟器错误输出 (部分): {stderr_text_sim[:500]}...")
            # Proceed to parse output_text, it might contain info or Python tracebacks

    except subprocess.TimeoutExpired:
        print(f"    错误: 执行 '{SIMULATOR_SCRIPT}' 超时。")
        return -float('inf')
    except FileNotFoundError:
        print(f"    错误: 脚本 '{SIMULATOR_SCRIPT}' 或 python 解释器未找到。")
        return -float('inf')
    except Exception as e:
        print(f"    运行 '{SIMULATOR_SCRIPT}' 时发生意外的子流程错误: {e}")
        return -float('inf')

    # 3. Parse output and calculate fitness
    sim_results = parse_simulator_output(output_text)
    eta_t = sim_results["thermal_efficiency"]
    eta_e = sim_results["exergy_efficiency"]
    cost_c = sim_results["cost"]

    if eta_t is None:
        print(f"    警告: 未能从模拟结果中解析出热效率。将赋一个非常低的适应度。")
        if not output_text.strip() and stderr_text_sim.strip():  # If stdout is empty but stderr has content
            print(f"    模拟器可能仅在stderr中输出了错误: {stderr_text_sim[:500]}...")
        elif not output_text.strip() and not stderr_text_sim.strip():
            print(f"    模拟器未产生任何输出 (stdout/stderr)。")

        return -float('inf')

    fitness = 0.0
    valid_metrics = 0
    if ALPHA > 0 and eta_t is not None:
        fitness += ALPHA * eta_t
        valid_metrics += 1
    if BETA > 0 and eta_e is not None:
        fitness += BETA * eta_e
        valid_metrics += 1
    if GAMMA > 0 and cost_c is not None:
        fitness -= GAMMA * cost_c
        valid_metrics += 1

    if valid_metrics == 0:
        print(f"    警告: 没有任何指标可用于计算适应度。")
        return -float('inf')

    # MODIFIED PRINT STATEMENT
    eta_t_str = f"{eta_t * 100:.2f}%" if eta_t is not None else "N/A"
    eta_e_str = f"{eta_e * 100:.2f}%" if eta_e is not None else "N/A"
    cost_c_str = f"{cost_c:.2f}" if cost_c is not None else "N/A"  # Assuming cost doesn't need *100
    print(f"    模拟结果: η_t={eta_t_str}, η_e={eta_e_str}, C={cost_c_str}. Fitness={fitness:.4f}")
    return fitness


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

    return {"genes": child1_genes, "fitness": -float('inf')}, {"genes": child2_genes, "fitness": -float('inf')}


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
    return {"genes": mutated_genes, "fitness": -float('inf')}


# --- Main GA Loop ---
def run_genetic_algorithm():
    """Runs the genetic algorithm."""
    if not check_scripts_exist():
        return None

    start_time = time.time()
    population = initialize_population()
    best_overall_individual = None

    # Log file for all individuals and their fitness
    log_filename = "ga_optimization_log.csv"
    with open(log_filename, 'w', encoding='utf-8') as log_file:
        log_file.write(
            "Generation,Individual,theta_5_c,pr_scbc,theta_w_c,pr_orc,Fitness,ThermalEfficiency,ExergyEfficiency,Cost\n")

        print(f"遗传算法开始。种群大小: {POPULATION_SIZE}, 最大代数: {MAX_GENERATIONS}")
        print(f"决策变量顺序: {VAR_NAMES}")
        print(f"边界条件: {VAR_BOUNDS}")
        print(f"适应度函数权重: α(η_t)={ALPHA}, β(η_e)={BETA}, γ(C)={GAMMA}")
        print(f"详细日志将保存在: {log_filename}")

        for generation in range(MAX_GENERATIONS):
            print(f"\n--- 第 {generation + 1} 代 ---")
            gen_start_time = time.time()

            for i, ind in enumerate(population):
                ind["fitness"] = calculate_fitness(ind, generation + 1, i + 1)

                genes = ind["genes"]
                # For robust logging of individual metrics, calculate_fitness should ideally return them.
                # As a workaround, we'll assume that if fitness is not -inf, parsing was successful.
                # This is not perfect, as a valid simulation might still have low (but not -inf) fitness.
                # A better approach is for calculate_fitness to return a dict: {'fitness': val, 'eta_t': ..., ...}

                # Attempt to get metrics for logging if fitness is not -inf (implies some parsing might have occurred)
                # This is still a simplification.
                log_eta_t, log_eta_e, log_cost_c = "N/A", "N/A", "N/A"
                if ind["fitness"] > -float('inf'):  # A very basic check
                    # This part is tricky: we don't have direct access to the parsed sim_results here
                    # without re-running or modifying calculate_fitness to return more.
                    # For now, we can only reliably log the combined fitness.
                    # To log individual metrics, calculate_fitness would need to return them.
                    # The print statement inside calculate_fitness already shows them if parsed.
                    pass  # Cannot reliably get individual metrics here without changing calculate_fitness

                log_file.write(f"{generation + 1},{i + 1},"
                               f"{genes[VAR_NAMES[0]]:.4f},{genes[VAR_NAMES[1]]:.4f},"
                               f"{genes[VAR_NAMES[2]]:.4f},{genes[VAR_NAMES[3]]:.4f},"
                               f"{ind['fitness']:.6f},"
                               f"{log_eta_t},{log_eta_e},{log_cost_c}\n")  # Placeholder for metrics
                log_file.flush()

                if best_overall_individual is None or ind["fitness"] > best_overall_individual["fitness"]:
                    best_overall_individual = ind.copy()
                    print(
                        f"  ** 新的最优个体 (第 {generation + 1} 代, 个体 {i + 1}): Fitness = {best_overall_individual['fitness']:.4f} **")
                    print(f"     基因: {best_overall_individual['genes']}")

            population.sort(key=lambda ind: ind["fitness"], reverse=True)

            if not population:  # Should not happen if POPULATION_SIZE > 0
                print("错误: 种群为空，终止算法。")
                break

            current_best_in_gen = population[0]
            print(f"第 {generation + 1} 代最优: Fitness = {current_best_in_gen['fitness']:.4f}")
            print(f"  基因: {current_best_in_gen['genes']}")
            if best_overall_individual:
                print(f"历史最优: Fitness = {best_overall_individual['fitness']:.4f}")
                print(f"  基因: {best_overall_individual['genes']}")

            next_population = []
            # Elitism: Carry over the best individual
            if population:  # Ensure population is not empty
                next_population.append(population[0].copy())

            while len(next_population) < POPULATION_SIZE:
                parent1 = tournament_selection(population)
                parent2 = tournament_selection(population)
                child1, child2 = (parent1.copy(), parent2.copy())  # Default to parents

                if random.random() < CROSSOVER_PROBABILITY:
                    child1_co, child2_co = crossover(parent1, parent2)
                    child1 = child1_co  # Assign crossed-over children
                    child2 = child2_co

                next_population.append(mutate(child1))
                if len(next_population) < POPULATION_SIZE:
                    next_population.append(mutate(child2))

            population = next_population
            gen_end_time = time.time()
            print(f"第 {generation + 1} 代耗时: {gen_end_time - gen_start_time:.2f} 秒")

    total_end_time = time.time()
    print("\n--- 遗传算法结束 ---")
    print(f"总耗时: {total_end_time - start_time:.2f} 秒")

    if best_overall_individual:
        print("\n找到的最优个体:")
        print(f"  基因 (决策变量):")
        for var_name, value in best_overall_individual["genes"].items():
            print(f"    {var_name}: {value:.4f}")
        print(f"  适应度值: {best_overall_individual['fitness']:.6f}")

        print("\n使用最优基因重新运行模拟以获取详细指标:")

        cmd_modify_final = [
            "python", MODIFY_PARAMS_SCRIPT,
            "--t5_c", str(best_overall_individual["genes"][VAR_NAMES[0]]),
            "--pr_scbc", str(best_overall_individual["genes"][VAR_NAMES[1]]),
            "--theta_w_c", str(best_overall_individual["genes"][VAR_NAMES[2]]),
            "--pr_orc", str(best_overall_individual["genes"][VAR_NAMES[3]])
        ]
        try:
            subprocess.run(cmd_modify_final, capture_output=True, check=True, timeout=60)
            print(f"参数已更新为最优值 (使用默认 '{PARAMS_JSON_FILE}')。")

            cmd_simulate_final = ["python", SIMULATOR_SCRIPT]
            final_sim_proc = subprocess.run(cmd_simulate_final, capture_output=True, timeout=300)

            final_sim_stdout_str = decode_subprocess_output(final_sim_proc.stdout)
            final_sim_stderr_str = decode_subprocess_output(final_sim_proc.stderr)

            print("\n最优参数下的模拟器输出:")
            print("-" * 30)
            print(final_sim_stdout_str)
            print("-" * 30)
            if final_sim_proc.returncode != 0:
                print(f"警告: 最优参数模拟返回码: {final_sim_proc.returncode}")
                if final_sim_stderr_str:
                    print(f"最优参数模拟器错误输出: {final_sim_stderr_str}")

            final_metrics = parse_simulator_output(final_sim_stdout_str)
            print("\n最优参数下的性能指标:")

            # MODIFIED PRINT STATEMENTS for final metrics
            final_eta_t_str = f"{final_metrics['thermal_efficiency'] * 100:.2f}%" if final_metrics[
                                                                                         'thermal_efficiency'] is not None else "未能解析"
            final_eta_e_str = f"{final_metrics['exergy_efficiency'] * 100:.2f}%" if final_metrics[
                                                                                        'exergy_efficiency'] is not None else "N/A"
            final_cost_c_str = f"{final_metrics['cost']:.2f}" if final_metrics['cost'] is not None else "N/A"

            print(f"  总热效率 η_t: {final_eta_t_str}")
            if BETA > 0 or final_metrics['exergy_efficiency'] is not None:  # Only print if relevant or available
                print(f"  㶲效率 η_e: {final_eta_e_str}")
            if GAMMA > 0 or final_metrics['cost'] is not None:  # Only print if relevant or available
                print(f"  成本 C: {final_cost_c_str}")

        except Exception as e:
            print(f"使用最优基因重新运行模拟时出错: {e}")
    else:
        print("未能找到最优个体。")

    return best_overall_individual


if __name__ == "__main__":
    best_solution = run_genetic_algorithm()

