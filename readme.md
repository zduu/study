# SCBC-ORC联合循环系统

## 项目概述

本项目实现了一个SCBC-ORC联合循环系统的模拟和优化。系统通过遗传算法优化关键参数，实现了系统性能的提升。

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
   - 使用遗传算法优化系统参数
   - 支持多目标优化
   - 考虑实际约束条件

2. **性能分析**：
   - 计算系统热效率
   - 计算系统火用效率
   - 分析系统性能

3. **敏感性分析**：
   - 分析参数敏感性
   - 生成分析报告
   - 绘制分析图表

4. **可视化**：
   - 生成性能图表
   - 绘制参数曲线
   - 展示优化结果

## 安装说明

### 系统要求

- Python 3.8+
- 操作系统：Windows/Linux/MacOS
- 内存：8GB+
- 存储：1GB+

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

1. **初始化参数**：
   ```bash
   python state_point_calculator.py
   ```

2. **执行单次模拟**：
   ```bash
   python full_cycle_simulator.py
   ```

3. **重新生成参数文件**：
   ```bash
   python modify_cycle_parameters.py --t5_c 599.99 --pr_scbc 3.25 --pr_orc 4.00 --theta_w_c 117.44
   ```

4. **执行参数敏感性分析**：
   ```bash
   python run_pr_orc_sensitivity_analysis.py
   ```

5. **绘制结果图表**：
   ```bash
   python plot_pr_sensitivity.py
   ```

6. **执行系统优化**：
   ```bash
   python genetic_algorithm_optimizer.py
   ```

### 参数配置

1. **关键变量**：
   - T5：SCBC透平入口温度
   - PR：SCBC主循环压比
   - PR_ORC：ORC透平膨胀比
   - THETA_W_C：ORC透平入口温度

2. **计算参数**：
   - T9：预冷器出口温度
   - P_ORC：ORC蒸发压力
   - T_ORC：ORC泵入口温度

3. **性能指标**：
   - 总热效率
   - 总火用效率
   - 火用效率/卡诺效率比

## 项目结构

```
study/
├── src/
│   ├── state_point_calculator.py
│   ├── full_cycle_simulator.py
│   ├── modify_cycle_parameters.py
│   ├── run_pr_orc_sensitivity_analysis.py
│   ├── plot_pr_sensitivity.py
│   └── genetic_algorithm_optimizer.py
├── data/
│   ├── cycle_setup_parameters.json
│   ├── calculated_state_points_from_table10.csv
│   └── pr_orc_sensitivity_results.csv
├── results/
│   ├── pr_orc_sensitivity_plot.png
│   ├── pr_exergy_efficiency_plot.png
│   └── optimization_results.csv
├── docs/
│   ├── implementation_guide.md
│   ├── troubleshooting.md
│   └── user_guide.md
├── tests/
│   └── test_*.py
├── requirements.txt
└── README.md
```

## [具体查看文档](/md/readme.md)
