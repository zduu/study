# SCBC-ORC联合循环系统使用指南

## 1. 系统要求

### 1.1 硬件要求
- 处理器：Intel i5或同等性能
- 内存：8GB以上
- 存储空间：1GB以上
- 操作系统：Windows/Linux/MacOS

### 1.2 软件要求
- Python 3.8+
- 依赖包：
  - CoolProp
  - NumPy
  - Pandas
  - Matplotlib
  - SciPy

## 2. 安装步骤

### 2.1 环境准备
1. 创建虚拟环境：
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/MacOS
   venv\Scripts\activate     # Windows
   ```

2. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```

### 2.2 验证安装
```bash
python -c "import scbc_orc_system; print('安装成功')"
```

## 3. 基本操作

### 3.1 初始化系统
1. 初始化参数：
   ```bash
   python state_point_calculator.py
   ```

2. 执行单次模拟：
   ```bash
   python full_cycle_simulator.py
   ```

### 3.2 参数调整
1. 修改关键参数：
   ```bash
   python modify_cycle_parameters.py --t5_c 599.99 --pr_scbc 3.25 --pr_orc 4.00 --theta_w_c 117.44
   ```

2. 参数说明：
   - t5_c：SCBC透平入口温度(°C)
   - pr_scbc：SCBC主循环压比
   - pr_orc：ORC透平膨胀比
   - theta_w_c：ORC透平入口温度(°C)

### 3.3 性能分析
1. 执行参数敏感性分析：
   ```bash
   python run_pr_orc_sensitivity_analysis.py
   ```

2. 生成分析图表：
   ```bash
   python plot_pr_sensitivity.py
   ```

3. 执行系统优化：
   ```bash
   python genetic_algorithm_optimizer.py
   ```

## 4. 输出文件说明

### 4.1 参数文件
- `cycle_setup_parameters.json`：系统参数配置
- `calculated_state_points_from_table10.csv`：状态点计算结果

### 4.2 分析结果
- `pr_orc_sensitivity_results.csv`：参数敏感性分析结果
- `pr_orc_sensitivity_plot.png`：热效率与功率曲线图
- `pr_exergy_efficiency_plot.png`：火用效率分析图

## 5. 常见问题

### 5.1 参数设置
- 确保参数在合理范围内
- 注意参数之间的相互影响
- 建议使用参数敏感性分析工具评估参数变化

### 5.2 运行问题
- 检查Python环境和依赖包是否正确安装
- 确保输入参数格式正确
- 查看错误日志了解详细信息

### 5.3 性能优化
- 使用参数敏感性分析确定关键参数
- 通过系统优化寻找最优参数组合
- 注意平衡热效率和火用效率 