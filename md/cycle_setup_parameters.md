# SCBC-ORC联合循环系统参数设置详解

本文档详细阐述了SCBC-ORC联合循环系统的完整参数体系，包括设计参数的选择依据、计算方法和工程约束。所有参数通过`generate_cycle_parameters.py`脚本自动生成，并以JSON格式保存在`cycle_setup_parameters.json`文件中，为系统仿真和优化提供基础数据。

**参数设置原则**：
- **理论基础**：基于热力学第一、第二定律和传热传质理论
- **工程实践**：结合实际设备性能和运行经验
- **优化结果**：采用遗传算法优化得到的最优参数组合
- **安全裕度**：考虑设备安全运行和性能衰减因素

## 1. 核心设计参数

### 1.1 SCBC循环关键参数

**优化变量（遗传算法优化得到）**：

| 参数名称 | 符号 | 数值 | 单位 | 设计范围 | 选择依据 |
|----------|------|------|------|----------|----------|
| 透平入口温度 | T₅ | 599.99 | °C | 500-600 | 材料耐温极限与循环效率平衡 |
| 主循环压比 | PR_SCBC | 3.25 | - | 2.2-4.0 | 压缩功与循环效率的最优平衡点 |

**固定设计参数**：

| 参数名称 | 符号 | 数值 | 单位 | 选择依据 |
|----------|------|------|------|----------|
| 压缩机入口压力 | P₁ | 7400 | kPa | 接近CO₂临界压力，确保超临界状态 |
| 压缩机入口温度 | T₁ | 35.0 | °C | 高于临界温度，保证超临界压缩 |
| 环境参考温度 | T₀ | 9.56 | °C | 标准环境条件，㶲计算基准 |
| 环境参考压力 | P₀ | 101.325 | kPa | 标准大气压力 |

**计算参数**：

| 参数名称 | 计算公式 | 当前值 | 单位 | 说明 |
|----------|----------|--------|------|------|
| 预冷器出口温度 | T₉ = 84.38 + 5.0×(PR-3.27) | 84.28 | °C | 基于压比的线性关系 |
| 主循环质量流量 | 基于600MW热输入计算 | 2641.42 | kg/s | 满足设计热功率要求 |
| 压缩机出口压力 | P₂ = P₁ × PR_SCBC | 24050 | kPa | 由压比和入口压力确定 |

### 1.2 ORC循环关键参数

**优化变量**：

| 参数名称 | 符号 | 数值 | 单位 | 设计范围 | 选择依据 |
|----------|------|------|------|----------|----------|
| 透平入口温度 | θ_w | 117.44 | °C | 100-130 | R245fa热稳定性与传热温差 |
| 透平膨胀比 | PR_ORC | 4.00 | - | 2.0-4.0 | 透平效率与系统复杂性平衡 |

**计算参数**：

| 参数名称 | 计算方法 | 当前值 | 单位 | 说明 |
|----------|----------|--------|------|------|
| 蒸发压力 | 基于θ_w的饱和压力 | 1478.70 | kPa | R245fa在117.44°C的饱和压力 |
| 冷凝压力 | P_evap / PR_ORC | 369.68 | kPa | 由膨胀比确定 |
| 泵入口温度 | 冷凝压力对应饱和温度 | 52.35 | °C | 饱和液体状态 |
| 质量流量初值 | 迭代计算起始值 | 100.0 | kg/s | 后续通过热平衡迭代确定 |

## 2. 设备效率与性能参数

### 2.1 SCBC循环设备效率

**压缩设备**：

| 设备名称 | 效率类型 | 数值 | 参数名 | 技术水平 | 选择依据 |
|----------|----------|------|--------|----------|----------|
| 主压缩机(MC) | 等熵效率 | 0.85 | eta_C_compressor | 先进水平 | 超临界CO₂离心压缩机技术 |
| 再压缩机(RC) | 等熵效率 | 0.85 | eta_RC_compressor | 先进水平 | 与主压缩机采用相同技术 |

**膨胀设备**：

| 设备名称 | 效率类型 | 数值 | 参数名 | 技术水平 | 选择依据 |
|----------|----------|------|--------|----------|----------|
| 透平(T) | 等熵效率 | 0.90 | eta_T_turbine | 国际先进 | 高温透平叶片和冷却技术 |

**换热设备**：

| 设备名称 | 效率类型 | 数值 | 参数名 | 技术水平 | 选择依据 |
|----------|----------|------|--------|----------|----------|
| 高温回热器(HTR) | 热效能 | 0.86 | eta_H_HTR_effectiveness | 工业标准 | 考虑高温下的传热损失 |
| 低温回热器(LTR) | 热效能 | 0.86 | eta_L_LTR_effectiveness | 工业标准 | 考虑温差和压降损失 |

### 2.2 ORC循环设备效率

**流体机械**：

| 设备名称 | 效率类型 | 数值 | 参数名 | 技术水平 | 选择依据 |
|----------|----------|------|--------|----------|----------|
| 泵(PO) | 等熵效率 | 0.75 | eta_PO_pump | 常规水平 | 液体泵的典型效率水平 |
| 透平(TO) | 等熵效率 | 0.80 | eta_TO_turbine | 良好水平 | 有机工质透平技术限制 |

**传热设备**：

| 设备名称 | 参数类型 | 数值 | 参数名 | 工程意义 | 设计考虑 |
|----------|----------|------|--------|----------|----------|
| 蒸发器(GO) | 最小温差 | 10.0°C | min_temp_diff_pinch_C | 夹点温差 | 平衡传热面积与传热效果 |
| 冷凝器(CO) | 最小温差 | 10.0°C | - | 夹点温差 | 确保充分的传热推动力 |

### 2.3 效率参数的工程背景

**SCBC设备效率分析**：
- **压缩机效率0.85**：超临界CO₂的高密度特性使压缩机设计更紧凑，但也带来了叶轮强度和密封的挑战
- **透平效率0.90**：高温透平技术成熟，采用先进的叶片冷却和耐高温材料
- **回热器效能0.86**：受限于传热面积和压降的平衡，实际工程中的典型水平

**ORC设备效率分析**：
- **泵效率0.75**：液体泵效率相对较低，主要受机械损失和容积损失影响
- **透平效率0.80**：有机工质的物性特点使透平设计复杂，效率略低于蒸汽透平
- **最小温差10°C**：在传热面积经济性和传热效果之间的工程平衡点

## 3. 工质选择与特性分析

### 3.1 SCBC循环工质 - 超临界CO₂

**基本物性参数**：

| 物性参数 | 数值 | 单位 | 参数名 | 工程意义 |
|----------|------|------|--------|----------|
| 临界温度 | 31.1 | °C | T_crit | 超临界状态的温度下限 |
| 临界压力 | 7.38 | MPa | P_crit | 超临界状态的压力下限 |
| 临界密度 | 467.6 | kg/m³ | rho_crit | 临界点密度 |
| 分子量 | 44.01 | g/mol | M | 影响气体常数和物性 |

**工质选择优势**：
- **环保特性**：GWP=1，ODP=0，完全无毒无害，符合环保要求
- **热力学优势**：在临界点附近比热容急剧增大，传热性能优异
- **物理特性**：高密度（接近液体）和低粘度（接近气体）的独特组合
- **化学稳定性**：化学性质稳定，不腐蚀设备，使用寿命长
- **经济性**：工质成本低，易于获得和回收

**超临界状态特点**：
- **工作区域**：T > 31.1°C 且 P > 7.38 MPa
- **密度特性**：密度是常压气体的100-200倍，减小设备尺寸
- **压缩特性**：压缩功比理想气体低30-50%
- **传热特性**：传热系数高，换热器面积小

### 3.2 ORC循环工质 - R245fa

**基本物性参数**：

| 物性参数 | 数值 | 单位 | 参数名 | 工程意义 |
|----------|------|------|--------|----------|
| 临界温度 | 154.0 | °C | T_crit | 工作温度上限 |
| 临界压力 | 3.65 | MPa | P_crit | 工作压力上限 |
| 沸点(1 atm) | 15.1 | °C | T_boil | 常压沸点 |
| 分子量 | 134.05 | g/mol | M | 重质有机工质 |

**工质选择理由**：
- **温度匹配**：沸点和临界温度适合中低温热源(100-150°C)
- **热稳定性**：在工作温度范围内化学稳定，不分解
- **传热特性**：良好的传热和流动特性，适合紧凑换热器
- **安全性**：不燃不爆，操作安全性高
- **技术成熟**：ORC系统中广泛应用，技术成熟可靠

**环保考虑**：
- **当前状态**：GWP=1030，属于中等温室效应潜能
- **发展趋势**：正在向更环保的工质(如R1233zd、R1336mzz)过渡
- **过渡方案**：现有系统可通过工质替换实现环保升级

### 3.3 工质物性对比分析

| 对比项目 | CO₂ | R245fa | 影响分析 |
|----------|-----|--------|----------|
| 临界温度 | 31.1°C | 154.0°C | CO₂适合高温循环，R245fa适合中温循环 |
| 临界压力 | 7.38 MPa | 3.65 MPa | CO₂需要高压设备，R245fa压力适中 |
| 密度比 | 高(超临界) | 中等(亚临界) | CO₂设备更紧凑 |
| 粘度 | 低 | 中等 | CO₂流动阻力小 |
| 传热系数 | 高 | 中等 | CO₂换热器面积小 |
| 环保性 | 优秀 | 一般 | CO₂完全环保 |
| 安全性 | 优秀 | 良好 | 两者都安全可靠 |

## 4. 系统约束条件

### 4.1 温度约束
- **SCBC透平入口温度**：500-600°C（材料温度限制）
- **ORC涡轮机入口温度**：100-130°C（避免工质分解）
- **预冷器出口温度**：随压比动态变化（确保适当的循环效率）
- **最小传热温差**：10.0°C（在`min_temp_diff_pinch_C`参数中指定）

### 4.2 压力约束
- **SCBC主循环压比**：2.2-4.0（平衡效率与机械应力）
- **ORC透平膨胀比**：2.0-4.0（平衡效率与系统复杂性）
- **最小压差**：0.1 MPa（确保足够的流动推动力）
- **最大系统压力**：20 MPa（材料和安全限制）

### 4.3 计算约束
- **SCBC循环最大迭代次数**：20（对应`max_iter_scbc_main_loop`参数）
- **ORC循环最大迭代次数**：40（对应`max_iter_orc_mdot`参数）
- **SCBC焓收敛容差**：0.1 kJ/kg（对应`tol_scbc_h_kJ_kg`参数）
- **ORC温度接近度收敛容差**：0.1 K（对应`tol_orc_T_approach_K`参数）

## 5. 性能目标

### 5.1 效率目标
- **总热效率**：>44%（已达成44.12%，高于传统循环）
- **总火用效率**：>65%（已达成65.25%，表明系统高质量能量利用）
- **火用效率/卡诺效率比**：>98%（已达成98.7%，接近理论极限）

### 5.2 功率目标
- **热输入功率**：600.0 MW（在`notes.phi_ER_MW_heat_input`参数中指定）
- **SCBC净功率**：>200 MW（适合中大型发电应用）
- **ORC净功率**：>10 MW（有效利用余热）
- **总净功率**：>210 MW（满足大型工业和电力需求）

## 6. 参数生成与更新机制

### 6.1 参数生成流程

系统参数通过`generate_cycle_parameters.py`脚本自动生成，遵循以下流程：

**第一步：关键变量输入**
```python
# 四个核心优化变量
key_variables = {
    "new_t5_c": 599.99,        # SCBC透平入口温度 (°C)
    "new_pr_scbc": 3.25,       # SCBC主循环压比
    "new_pr_orc": 4.00,        # ORC透平膨胀比
    "new_theta_w_orc_c": 117.44 # ORC涡轮机入口温度 (°C)
}
```

**第二步：依赖参数计算**
```python
# 基于关键变量计算其他参数
def calculate_dependent_parameters(key_vars):
    # 1. 预冷器出口温度计算
    base_T9_C = 84.38
    base_PR = 3.27
    sensitivity_factor = 5.0
    T9_C = base_T9_C + sensitivity_factor * (key_vars["new_pr_scbc"] - base_PR)

    # 2. ORC蒸发压力计算
    P_evap_kPa = calculate_saturation_pressure("R245fa", key_vars["new_theta_w_orc_c"])

    # 3. ORC冷凝压力计算
    P_cond_kPa = P_evap_kPa / key_vars["new_pr_orc"]

    return T9_C, P_evap_kPa, P_cond_kPa
```

**第三步：约束检查与验证**
```python
def validate_parameters(params):
    # 温度约束检查
    if not (500 <= params["T5_C"] <= 600):
        raise ValueError("SCBC透平入口温度超出范围")

    # 压力约束检查
    if not (2.2 <= params["PR_SCBC"] <= 4.0):
        raise ValueError("SCBC压比超出范围")

    # 物理可行性检查
    if params["T_hot_in"] <= params["T_cold_out"]:
        raise ValueError("传热温差不满足物理约束")

    return True
```

### 6.2 参数更新策略

**实时更新机制**：
- 修改任一关键变量时，系统自动重新计算所有依赖参数
- 保持参数间的物理一致性和工程合理性
- 自动检查并修正违反约束的参数值

**参数关联关系**：

| 主变量 | 影响的从变量 | 关联公式/方法 | 物理意义 |
|--------|--------------|---------------|----------|
| T₅ | 透平功率、循环效率 | W = ṁ(h₅-h₆) | 高温决定循环上限 |
| PR_SCBC | T₉、压缩功 | T₉ = f(PR) | 压比影响预冷温度 |
| θ_w | P_evap、ORC功率 | P = P_sat(T) | 蒸发温度决定压力 |
| PR_ORC | P_cond、ORC效率 | P_cond = P_evap/PR | 膨胀比决定冷凝压力 |

### 6.3 参数文件管理

**JSON格式存储**：
```json
{
  "scbc_cycle": {
    "T5_turbine_inlet_C": 599.99,
    "PR_main_cycle": 3.25,
    "T9_precooler_outlet_C": 84.28,
    "mass_flow_rate_kg_s": 2641.42
  },
  "orc_cycle": {
    "theta_w_turbine_inlet_C": 117.44,
    "PR_expansion_ratio": 4.00,
    "P_evaporation_kPa": 1478.70,
    "P_condensation_kPa": 369.68
  },
  "component_efficiencies": {
    "eta_T_turbine": 0.90,
    "eta_C_compressor": 0.85,
    "eta_TO_turbine": 0.80,
    "eta_PO_pump": 0.75
  }
}
```

**版本控制**：
- 每次参数更新自动生成时间戳
- 保留历史版本用于对比分析
- 提供参数变更日志和影响分析

**参数验证**：
- 加载时自动验证参数完整性
- 检查参数值的物理合理性
- 提供参数异常的诊断信息

### 6.4 使用建议

**参数调整原则**：
1. **单变量调整**：每次只修改一个关键变量，观察系统响应
2. **渐进式优化**：采用小步长逐步调整，避免大幅跳跃
3. **约束优先**：确保所有约束条件得到满足
4. **性能验证**：每次调整后运行完整仿真验证性能

**常见问题处理**：
- **收敛困难**：减小参数调整幅度，增加迭代次数
- **物性计算失败**：检查温度压力是否在工质适用范围内
- **性能异常**：验证参数设置是否符合工程实际

通过这套完整的参数管理机制，用户可以方便地进行系统参数的调整和优化，确保仿真计算的准确性和可靠性。

