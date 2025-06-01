## 目录结构
```
study/
├── code/                      # 源代码目录
│   ├── state_point_calculator.py    # 状态点计算与物性模块
│   ├── cycle_components.py          # 循环组件模型库
│   ├── full_cycle_simulator.py      # 完整循环模拟器
│   ├── modify_cycle_parameters.py   # 参数修改工具
│   ├── run_pr_sensitivity_analysis.py # 敏感性分析工具
│   ├── plot_pr_sensitivity.py       # 结果可视化工具
│   ├── plot_pr_sensitivity_cn.py    # 中文版结果可视化工具
│   ├── genetic_algorithm_optimizer.py # 多目标优化模块
│   └── generate_cycle_parameters.py  # 参数生成工具
├── output/                    # 输出文件目录
│   ├── cycle_setup_parameters.json  # 系统参数配置
│   ├── calculated_state_points_from_table10.csv # 状态点计算结果
│   ├── pr_sensitivity_results.csv   # 参数敏感性分析结果
│   ├── pr_sensitivity_plot.png      # 热效率与功率曲线图
│   └── pr_exergy_efficiency_plot.png # 火用效率分析图
├── md/                       # 文档目录
│   ├── readme1.md           # 项目详细说明
│   ├── system_overview.md   # 系统架构说明
│   └── cycle_setup_parameters.md # 参数文件说明
└── requirements.txt         # Python依赖包列表
```

## 代码功能说明

### 核心模块
1. **状态点计算模块** (`state_point_calculator.py`)
   - 提供工质热力学性质计算
   - 实现㶲值计算功能
   - 验证计算结果准确性

2. **循环组件模型库** (`cycle_components.py`)
   - 定义压缩机、透平、泵等组件模型
   - 实现换热器、蒸发器等热力设备模型
   - 提供组件性能计算方法

3. **完整循环模拟器** (`full_cycle_simulator.py`)
   - 集成SCBC和ORC循环模拟
   - 计算系统整体性能指标
   - 实现迭代求解算法

4. **参数管理工具**
   - `modify_cycle_parameters.py`: 修改系统关键变量
   - `generate_cycle_parameters.py`: 生成系统参数配置
   - 支持基于四个关键变量的参数计算

5. **分析工具**
   - `run_pr_sensitivity_analysis.py`: 执行参数敏感性分析
   - `plot_pr_sensitivity.py`: 绘制性能分析图表
   - `genetic_algorithm_optimizer.py`: 实现多目标优化

### 关键功能
1. **参数化设计**
   - 基于四个关键变量的系统设计
   - 动态调整预冷器出口温度
   - 自动计算相关参数

2. **性能分析**
   - 压比敏感性分析
   - 热效率和火用效率计算
   - 与卡诺效率对比分析

3. **优化功能**
   - 多目标参数优化
   - 遗传算法实现
   - Pareto前沿生成

4. **可视化功能**
   - 性能曲线绘制
   - 多Y轴图表展示
   - 最高点标注功能

## 下一步：
- 文档说明请看readme1.md
- 代码说明请看system_overview.md
- 安装python环境指令`pip install -r requirements.txt`
- 寻优算法结果
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