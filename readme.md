# SCBC-ORC联合循环系统

## 项目概述

本项目实现了一个SCBC-ORC联合循环系统的模拟和优化。系统结合了超临界CO2布雷顿循环(SCBC)和有机朗肯循环(ORC)的优点，通过遗传算法优化关键参数，实现了系统性能的提升。项目旨在提供高效、可靠的能源转换解决方案，适用于工业余热回收、分布式能源系统和大型发电厂等应用场景。

### 最新优化结果

| 参数 | 优化值 | 范围 |
|------|--------|------|
| SCBC透平入口温度 | 599.99°C | 500-600°C |
| SCBC主循环压比 | 3.25 | 2.2-4.0 |
| ORC透平膨胀比 | 4.00 | 2.0-4.0 |
| ORC透平入口温度 | 117.44°C | 100-130°C |

### [genetic_algorithm_optimizer.py](code/genetic_algorithm_optimizer.py)代码运行输出结果（部分）
```
第 100 代最优: Fitness = 0.5257
历史最优: Fitness = 0.5257
  基因: theta_5_c=600.00, pr_scbc=3.24, theta_w_c=114.12, pr_orc=4.00
  对应指标: η_t=44.12%, η_e=65.25%
第 100 代耗时: 51.90 秒

--- 遗传算法结束 ---
总耗时: 5320.70 秒

找到的最优个体:
  基因 (决策变量):
    theta_5_c: 599.9931
    pr_scbc: 3.2474
    theta_w_c: 117.4406
    pr_orc: 3.9994
  适应度值: 0.525720

使用最优基因重新运行模拟以获取详细指标 (这些指标已在优化过程中记录):

最优参数下的性能指标 (来自优化过程中的最佳记录):
  总热效率 η_t: 44.12%
  总㶲效率 η_e: 65.25%
```

### 性能指标

| 指标 | 优化值 | 基准值 | 提升 |
|------|--------|--------|------|
| 总热效率 | 44.12% | 43.87% | +0.25% |
| 总火用效率 | 65.25% | 65.79% | -0.54% |
| 火用效率/卡诺效率比 | 98.7% | 98.5% | +0.2% |

### 参数敏感性分析结果

| THETA_W_C | PR_ORC | 总热效率(%) | 总火用效率(%) |
|-----------|--------|------------|--------------|
| 110°C     | 2.2    | 43.25      | 63.97        |
| 110°C     | 4.0    | 44.10      | 65.23        |
| 120°C     | 2.2    | 43.39      | 64.17        |
| 120°C     | 4.0    | 44.10      | 65.22        |
| 130°C     | 2.2    | 43.51      | 64.35        |
| 130°C     | 4.0    | 44.09      | 65.21        |

## 功能特点

1. **参数优化**：
   - 使用遗传算法优化系统关键参数
   - 支持多目标优化（热效率和火用效率）
   - 考虑实际工程约束条件
   - 自适应变异率和交叉率

2. **性能分析**：
   - 计算系统总热效率
   - 计算系统总火用效率
   - 分析火用效率/卡诺效率比
   - 评估各组件性能

3. **敏感性分析**：
   - 分析关键参数敏感性
   - 生成参数影响矩阵
   - 绘制参数-性能曲线
   - 计算最优参数区间

4. **可视化**：
   - 生成循环性能图表
   - 绘制优化过程收敛曲线
   - 绘制参数敏感性热图
   - 生成系统状态T-s图

## 安装说明

### 系统要求

- Python 3.8+
- 操作系统：Windows/Linux/MacOS
- 内存：8GB+
- 存储：1GB+
- CPU：推荐多核处理器以加速优化过程

### 安装步骤

1. **下载代码**：
   ```bash
   git clone https://github.com/zduu/study.git
   cd study
   ```

2. **创建虚拟环境**：
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/MacOS
   venv\Scripts\activate     # Windows
   ```

3. **安装依赖**：
   ```bash
   pip install -r requirements.txt
   ```

## 使用指南

### 基本操作

1. **运行系统优化（遗传算法）**：
   ```bash
   python code/genetic_algorithm_optimizer.py
   ```

2. **运行循环系统全模拟**：
   ```bash
   python code/full_cycle_simulator.py
   ```

3. **计算系统状态点**：
   ```bash
   python code/state_point_calculator.py
   ```

4. **修改循环参数**：
   ```bash
   python code/modify_cycle_parameters.py
   ```

5. **生成循环参数**：
   ```bash
   python code/generate_cycle_parameters.py
   ```

6. **运行压力比敏感性分析**：
   ```bash
   python code/run_pr_sensitivity_analysis.py
   ```

7. **运行ORC压力比敏感性分析**：
   ```bash
   python code/run_pr_orc_sensitivity_analysis.py
   ```

8. **绘制压力比敏感性图表**：
   ```bash
   python code/plot_pr_sensitivity.py
   ```

9. **绘制中文版压力比敏感性图表**：
   ```bash
   python code/plot_pr_sensitivity_cn.py
   ```

10. **循环组件分析**：
    ```bash
    python code/cycle_components.py
    ```

### 参数配置

1. **关键变量**：
   - `theta_5_c`：SCBC透平入口温度（℃）
   - `pr_scbc`：SCBC主循环压比
   - `pr_orc`：ORC透平膨胀比
   - `theta_w_c`：ORC透平入口温度（℃）

2. **计算参数**：
   - `t9`：预冷器出口温度（℃）
   - `p_orc`：ORC蒸发压力（kPa）
   - `t_orc`：ORC泵入口温度（℃）

3. **性能指标**：
   - `eta_t`：总热效率（%）
   - `eta_e`：总火用效率（%）
   - `eta_e_ratio`：火用效率/卡诺效率比（%）

4. **遗传算法参数**：
   - `pop_size`：种群大小
   - `max_gen`：最大代数
   - `crossover_rate`：交叉率
   - `mutation_rate`：变异率
   - `elite_size`：精英保留数量

## 项目结构

```
study/
├── code/                                # 源代码目录
│   ├── cycle_components.py              # 循环组件定义与分析
│   ├── full_cycle_simulator.py          # 完整循环系统模拟器
│   ├── genetic_algorithm_optimizer.py   # 遗传算法优化器
│   ├── generate_cycle_parameters.py     # 循环参数生成工具
│   ├── modify_cycle_parameters.py       # 循环参数修改工具
│   ├── plot_pr_sensitivity.py           # 压力比敏感性分析绘图
│   ├── plot_pr_sensitivity_cn.py        # 中文版压力比敏感性分析绘图
│   ├── run_pr_orc_sensitivity_analysis.py  # ORC压力比敏感性分析
│   ├── run_pr_sensitivity_analysis.py   # 压力比敏感性分析
│   ├── state_point_calculator.py        # 系统状态点计算器
│   └── requirements.txt                 # 代码依赖文件
├── md/                                  # 文档目录
│   ├── cycle_setup_parameters.md        # 循环参数设置文档
│   ├── system_overview.md               # 系统概述文档
│   └── replication_overview.md          # 论文复现工作概述
├── output/                              # 输出目录
│   ├── figures/                         # 图表输出
│   ├── data/                            # 数据输出
│   └── reports/                         # 报告输出
├── 资料/                                # 参考资料
├── .gitignore                           # Git忽略文件
├── readme.md                            # 项目说明文档
└── requirements.txt                     # 项目依赖文件
```

## 技术细节

### 循环模型

系统包含两个主要循环：SCBC循环和ORC循环。这两个循环通过热交换器耦合，形成联合循环系统。

1. **SCBC循环**：
   - 工质：超临界CO2
   - 主要状态点：9个（从透平入口到预冷器出口）
   - 设备模型：包括压缩机、透平、回热器、加热器和预冷器
   - 热力学模型：基于热力学物性库

2. **ORC循环**：
   - 工质：R245fa
   - 主要状态点：4个（泵入口、蒸发器入口、透平入口、冷凝器入口）
   - 设备模型：包括泵、蒸发器、透平和冷凝器
   - 热力学模型：基于热力学物性库

### 优化算法

采用改进的遗传算法进行多目标优化：

1. **编码**：实数编码，直接表示决策变量
2. **选择**：锦标赛选择和精英保留策略
3. **交叉**：模拟二进制交叉（SBX）
4. **变异**：多项式变异，带自适应变异率
5. **适应度函数**：加权总热效率和总火用效率
6. **约束处理**：惩罚函数法处理约束条件

### 敏感性分析

采用参数扫描方法进行敏感性分析：

1. **参数选择**：ORC透平入口温度和ORC透平膨胀比
2. **水平设置**：每个参数3个水平
3. **结果分析**：热效率和火用效率变化分析

## 相关文档

本项目包含以下文档，详细说明系统的各个方面：

- [系统概述](md/system_overview.md) - 描述SCBC-ORC联合循环系统的基本原理和组成
- [循环参数设置](md/cycle_setup_parameters.md) - 详细说明系统参数设置和约束条件
- [论文复现工作概述](md/replication_overview.md) - 对《超临界CO₂布雷顿循环余热回收系统性能分析与优化》论文的复现报告