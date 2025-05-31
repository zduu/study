# SCBC-ORC联合循环系统代码说明文档

## 1. 系统概述

本文档详细说明超临界CO2布雷顿循环(SCBC)与有机朗肯循环(ORC)耦合系统的代码架构、功能模块及使用方法。该系统通过回收SCBC循环的废热来提高整体热效率，实现能源的高效利用。本文档涵盖了所有核心源代码文件及其功能。

## 2. 核心代码文件结构

### 2.1 基础物性计算模块

#### `state_point_calculator.py`
* **核心功能**：提供热力学状态点的物性计算功能
* **主要组件**：
  * `StatePoint`类：封装工质状态点的所有热力学参数(P, T, h, s, d, e等)
  * 㶲计算模块：基于环境参考态计算物理㶲
  * 参数文件生成器：创建系统配置文件`cycle_setup_parameters.json`
* **验证功能**：对比计算值与论文数据，输出到`calculated_state_points_from_table10.csv`
* **环境参考态**：使用T0=9.56°C, P0=101.382 kPa作为㶲计算参考点

### 2.2 循环组件模型库

#### `cycle_components.py`
* **核心功能**：定义循环中各组件的数学模型
* **主要组件模型**：
  * 压缩机模型：`model_compressor_MC`（SCBC主压缩机和再压缩机）
  * 透平模型：`model_turbine_T`（SCBC透平和ORC透平）
  * 泵模型：`model_pump_ORC`（ORC泵）
  * 换热器模型：`model_heat_exchanger_effectiveness`（HTR和LTR）
  * 蒸发器模型：`model_evaporator_GO`（SCBC-ORC耦合蒸发器）
  * 冷却器模型：`model_cooler_set_T_out`（主冷却器和ORC冷凝器）
  * 加热器模型：`model_heater_set_T_out`（SCBC吸热器）
* **依赖关系**：依赖`state_point_calculator.py`中的`StatePoint`类
* **输出文件**：组件测试结果输出到`cycle_components_output.txt`

### 2.3 完整循环模拟器

#### `full_cycle_simulator.py`
* **核心功能**：模拟完整的SCBC-ORC联合循环系统
* **主要功能模块**：
  * 参数加载：从`cycle_setup_parameters.json`加载系统参数
  * SCBC循环模拟：计算SCBC循环各点状态及性能
  * ORC循环模拟：计算ORC循环各点状态及性能
  * 联合循环性能评估：计算总热效率、㶲效率等指标
  * 结果输出：打印详细的状态点参数和性能指标
* **迭代算法**：包含针对回热器的迭代求解和ORC流量的迭代匹配
* **依赖关系**：依赖`cycle_components.py`和`state_point_calculator.py`

### 2.4 参数修改工具

#### `modify_cycle_parameters.py`
* **核心功能**：修改循环系统的关键参数
* **主要功能**：
  * 读取现有参数文件：加载`cycle_setup_parameters.json`
  * 修改关键参数：透平入口温度、压比、ORC膨胀比等
  * T9温度计算：根据压比动态调整预冷器出口温度
  * 参数写回：将修改后的参数保存回JSON文件
* **命令行接口**：支持通过命令行参数直接修改系统配置
* **依赖关系**：独立工具，仅依赖系统参数文件

### 2.5 参数敏感性分析工具

#### `run_pr_sensitivity_analysis.py`
* **核心功能**：执行系统参数的敏感性分析
* **主要功能**：
  * 参数扫描：在设定范围内扫描压比(PR)值
  * 系统性能评估：对每个参数点执行完整循环模拟
  * 结果收集：记录总热效率、净功率、T9温度等指标
  * 数据输出：将分析结果保存到`pr_sensitivity_results.csv`
* **执行流程**：调用`modify_cycle_parameters.py`和`full_cycle_simulator.py`
* **依赖关系**：依赖参数修改工具和完整循环模拟器

### 2.6 结果可视化工具

#### `plot_pr_sensitivity.py`
* **核心功能**：绘制参数敏感性分析的结果图表
* **主要功能**：
  * 数据读取：从`pr_sensitivity_results.csv`读取分析结果
  * 多轴图表：创建双Y轴图表显示效率和功率
  * 数据可视化：生成压比与系统性能的关系曲线
  * 图像保存：将图表保存为`pr_sensitivity_plot.png`
* **图表内容**：显示总热效率、SCBC净功率、ORC净功率与压比的关系
* **依赖关系**：依赖matplotlib、pandas等库，不依赖其他项目文件

### 2.7 优化算法模块

#### `genetic_algorithm_optimizer.py`
* **核心功能**：使用遗传算法优化系统参数
* **主要功能**：
  * 多目标优化：同时优化热效率、㶲效率和系统成本
  * 参数编码：将系统参数编码为基因序列
  * 适应度评估：评估每组参数的系统性能
  * Pareto前沿：生成非支配解集
* **决策变量**：包括透平入口温度、压比、ORC参数等
* **约束条件**：实现物理和工程约束
* **依赖关系**：依赖完整循环模拟器评估系统性能

## 3. 数据文件说明

### 3.1 参数配置文件

#### `cycle_setup_parameters.json`
* **功能**：存储系统的完整参数配置
* **主要参数**：
  * 工质定义：SCBC使用CO2，ORC使用R245fa
  * 环境参考条件：T0_C和P0_kPa
  * SCBC参数：压缩机入口条件、透平入口温度、压比、部件效率等
  * ORC参数：蒸发压力、膨胀比、部件效率等
  * 换热器参数：最小温差、效能值等
* **使用方式**：被循环模拟器和参数修改工具读取和修改

### 3.2 结果数据文件

#### `calculated_state_points_from_table10.csv`
* **功能**：存储状态点计算结果与论文数据的对比
* **内容**：包含各状态点的P, T, h, s, e等参数的计算值和论文值
* **用途**：验证物性计算的准确性，分析误差来源

#### `pr_sensitivity_results.csv`
* **功能**：存储参数敏感性分析的结果数据
* **内容**：不同压比下的总热效率、SCBC净功率、ORC净功率、T9温度等
* **用途**：用于结果分析和可视化绘图

#### `pr_sensitivity_plot.png`
* **功能**：参数敏感性分析的可视化图表
* **内容**：展示压比与系统性能指标的关系曲线
* **用途**：直观展示系统优化点和性能趋势

## 4. 系统运行流程

### 4.1 基本使用流程

1. **初始化参数**
   ```bash
   python state_point_calculator.py
   ```
   生成`cycle_setup_parameters.json`文件，设置系统初始参数

2. **执行单次模拟**
   ```bash
   python full_cycle_simulator.py
   ```
   使用当前参数执行完整循环模拟

3. **修改系统参数**
   ```bash
   python modify_cycle_parameters.py --t5_c 599.85 --pr_scbc 3.2 --pr_orc 3.37 --theta_w_c 127.76
   ```
   更新系统关键参数

4. **执行参数敏感性分析**
   ```bash
   python run_pr_sensitivity_analysis.py
   ```
   扫描压比范围，分析系统性能变化

5. **绘制结果图表**
   ```bash
   python plot_pr_sensitivity.py
   ```
   生成参数敏感性分析的可视化图表

6. **执行系统优化**
   ```bash
   python genetic_algorithm_optimizer.py
   ```
   使用遗传算法寻找最优系统参数

### 4.2 数据流向

```
state_point_calculator.py  ────┐
                               │
                               ▼
cycle_components.py ────> full_cycle_simulator.py <──── cycle_setup_parameters.json
                               │
                               ▼
                         Simulation Results
                               │
                               ▼
modify_cycle_parameters.py <─> run_pr_sensitivity_analysis.py ──> pr_sensitivity_results.csv
                                                                       │
                                                                       ▼
                                                               plot_pr_sensitivity.py
                                                                       │
                                                                       ▼
                                                              pr_sensitivity_plot.png
                               │
                               ▼
                    genetic_algorithm_optimizer.py
                               │
                               ▼
                       Optimized Parameters
```

## 5. 关键参数说明

### 5.1 SCBC循环参数

* **T5_turbine_inlet_C**：SCBC透平入口温度(°C)
  * 影响循环效率和功率输出
  * 优化值：599.85°C
  * 范围：500-600°C

* **PR_main_cycle_pressure_ratio**：SCBC主循环压比
  * 影响循环效率和功率输出
  * 优化值：3.27
  * 范围：2.2-4.0

* **T9_precooler_outlet_C**：预冷器出口温度(°C)
  * 随压比动态变化
  * 基准值：84.38°C (对应压比3.27)
  * 变化关系：T9 = base_T9 + sensitivity_factor * (PR - base_PR)

### 5.2 ORC循环参数

* **target_theta_w_orc_turbine_inlet_C**：ORC透平入口温度(°C)
  * 影响ORC效率和可用能
  * 优化值：127.76°C
  * 范围：100-130°C

* **target_pr_orc_expansion_ratio**：ORC透平膨胀比
  * 影响ORC功率输出
  * 优化值：3.37
  * 范围：2.0-4.0

* **P_eva_kPa_orc**：ORC蒸发压力(kPa)
  * 固定值：1500.0 kPa

## 6. 系统性能指标

### 6.1 最新分析结果

根据参数敏感性分析，系统在不同压比下的性能如下：

| PR_scbc | 总热效率(%) | SCBC净功率(MW) | ORC净功率(MW) | T9温度(°C) |
|---------|------------|--------------|-------------|----------|
| 2.2     | 42.12      | 242.02       | 10.48       | 79.03    |
| 2.6     | 43.33      | 248.27       | 11.48       | 81.03    |
| 3.0     | 43.80      | 250.40       | 12.24       | 83.03    |
| 3.2     | 43.87      | 250.49       | 12.55       | 84.03    |
| 3.6     | 43.78      | 249.77       | 13.10       | 86.03    |
| 4.0     | 43.52      | 247.75       | 13.56       | 88.03    |

