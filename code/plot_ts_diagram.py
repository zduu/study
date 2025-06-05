#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
T-s图绘制脚本
绘制ORC（有机朗肯循环）和SCBC（超临界CO2布雷顿循环）的温度-熵图
实现首尾相连的闭合循环图

作者: AI Assistant
日期: 2024
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
from matplotlib import rcParams
from CoolProp.CoolProp import PropsSI

# 设置中文字体支持
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

def load_state_points_data(csv_file_path):
    """
    从CSV文件加载状态点数据
    
    Args:
        csv_file_path (str): CSV文件路径
        
    Returns:
        pd.DataFrame: 状态点数据
    """
    try:
        df = pd.read_csv(csv_file_path)
        print(f"成功加载数据，共 {len(df)} 个状态点")
        return df
    except Exception as e:
        print(f"加载数据文件时出错: {e}")
        return None

def separate_cycles(df):
    """
    分离ORC和SCBC循环数据

    Args:
        df (pd.DataFrame): 状态点数据

    Returns:
        tuple: (orc_data, scbc_data)
    """
    orc_data = df[df['PointName'].str.contains('ORC', na=False)].copy()
    scbc_data = df[df['PointName'].str.contains('SCBC', na=False)].copy()

    print(f"ORC状态点数量: {len(orc_data)}")
    print(f"SCBC状态点数量: {len(scbc_data)}")

    return orc_data, scbc_data

def analyze_and_sort_cycle_points(data, cycle_type):
    """
    智能分析并按照热力循环的正确顺序排列状态点，形成闭合循环

    Args:
        data (pd.DataFrame): 状态点数据
        cycle_type (str): 循环类型 ('ORC' 或 'SCBC')

    Returns:
        pd.DataFrame: 排序后的数据
    """
    if data.empty:
        return pd.DataFrame()

    print(f"\n=== {cycle_type}循环状态点分析 ===")
    for _, row in data.iterrows():
        print(f"{row['PointName']}: P={row['P_kPa_input']:.0f}kPa, T={row['T_C_input']:.1f}°C, s={row['s_J_kgK_calc']/1000:.3f}kJ/kgK")

    if cycle_type == 'ORC':
        # ORC循环：朗肯循环
        # 根据实际数据分析最佳循环路径
        # 09: 1500kPa, 127.8°C, 1.866 kJ/kgK (高温高压)
        # 010: 445kPa, 94.7°C, 1.879 kJ/kgK (中温低压)
        # 011: 445kPa, 58.7°C, 1.260 kJ/kgK (低温低压)
        # 012: 1500kPa, 59.4°C, 1.261 kJ/kgK (低温高压)
        order = ['ORC 012', 'ORC 09', 'ORC 010', 'ORC 011']  # 形成合理的朗肯循环
    elif cycle_type == 'SCBC':
        # SCBC循环：超临界CO2布雷顿循环
        # 根据压力和温度分析，形成合理的布雷顿循环路径
        # 低压侧：1->9->8->7->6 (温度递增)
        # 高压侧：2->3->4->5 (温度递增)
        # 合理循环：1->2->3->4->5->6->7->8->9->1
        order = ['SCBC 1', 'SCBC 2', 'SCBC 3', 'SCBC 4', 'SCBC 5',
                'SCBC 6', 'SCBC 7', 'SCBC 8', 'SCBC 9']

    # 按指定顺序排列
    sorted_data = []
    for point_name in order:
        point_data = data[data['PointName'] == point_name]
        if not point_data.empty:
            sorted_data.append(point_data.iloc[0])

    result_df = pd.DataFrame(sorted_data) if sorted_data else pd.DataFrame()
    print(f"循环路径: {' -> '.join(order)} -> {order[0]}")
    return result_df

def generate_saturation_curve(fluid_name, T_min=None, T_max=None, num_points=100):
    """
    生成工质的饱和液相线和饱和气相线数据

    Args:
        fluid_name (str): 工质名称
        T_min (float): 最低温度 (K)
        T_max (float): 最高温度 (K)
        num_points (int): 数据点数量

    Returns:
        tuple: (T_sat, s_liquid, s_vapor) 温度和对应的液相、气相熵值
    """
    try:
        # 获取临界温度
        T_crit = PropsSI('Tcrit', fluid_name)
        T_triple = PropsSI('Ttriple', fluid_name)

        # 设置温度范围
        if T_min is None:
            T_min = T_triple + 5  # 避免三相点附近的数值问题
        if T_max is None:
            T_max = T_crit - 5    # 避免临界点附近的数值问题

        # 生成温度数组
        T_sat = np.linspace(T_min, T_max, num_points)

        s_liquid = []
        s_vapor = []
        T_valid = []

        for T in T_sat:
            try:
                # 计算饱和液相和气相的熵
                s_l = PropsSI('S', 'T', T, 'Q', 0, fluid_name) / 1000  # 转换为kJ/kgK
                s_v = PropsSI('S', 'T', T, 'Q', 1, fluid_name) / 1000  # 转换为kJ/kgK

                s_liquid.append(s_l)
                s_vapor.append(s_v)
                T_valid.append(T - 273.15)  # 转换为摄氏度

            except Exception:
                continue  # 跳过计算失败的点

        return np.array(T_valid), np.array(s_liquid), np.array(s_vapor)

    except Exception as e:
        print(f"生成{fluid_name}饱和曲线时出错: {e}")
        return np.array([]), np.array([]), np.array([])

def plot_ts_diagram(orc_data, scbc_data, output_path):
    """
    绘制T-s图（首尾相连的闭合循环图）

    Args:
        orc_data (pd.DataFrame): ORC循环数据
        scbc_data (pd.DataFrame): SCBC循环数据
        output_path (str): 输出图像路径
    """
    # 创建图形和坐标轴
    fig, ax = plt.subplots(figsize=(14, 10))

    # 绘制R245fa的饱和曲线（相变包络线）
    print("正在生成R245fa饱和曲线...")
    T_sat, s_liquid, s_vapor = generate_saturation_curve('R245fa', T_min=273.15+20, T_max=273.15+150)

    if len(T_sat) > 0:
        # 绘制饱和液相线
        ax.plot(s_liquid, T_sat, '--', linewidth=2, color='gray', alpha=0.7, label='R245fa饱和液相线')
        # 绘制饱和气相线
        ax.plot(s_vapor, T_sat, '--', linewidth=2, color='gray', alpha=0.7, label='R245fa饱和气相线')

        # 连接液相线和气相线形成完整的相变包络线
        # 在最低温度处连接
        if len(s_liquid) > 0 and len(s_vapor) > 0:
            ax.plot([s_liquid[0], s_vapor[0]], [T_sat[0], T_sat[0]], '--',
                   linewidth=2, color='gray', alpha=0.7)
            # 在最高温度处连接
            ax.plot([s_liquid[-1], s_vapor[-1]], [T_sat[-1], T_sat[-1]], '--',
                   linewidth=2, color='gray', alpha=0.7)

    # 绘制ORC循环
    if not orc_data.empty:
        orc_sorted = analyze_and_sort_cycle_points(orc_data, 'ORC')
        if not orc_sorted.empty:
            orc_T = orc_sorted['T_C_input'].values
            orc_s = orc_sorted['s_J_kgK_calc'].values / 1000  # 转换为kJ/kgK

            # 首尾相连：添加第一个点到末尾形成闭合循环
            orc_T_closed = np.append(orc_T, orc_T[0])
            orc_s_closed = np.append(orc_s, orc_s[0])

            # 绘制ORC循环线条
            ax.plot(orc_s_closed, orc_T_closed, 'o-', linewidth=4, markersize=12,
                    label='ORC (R245fa)', color='red', alpha=0.9, zorder=5)

            # 添加状态点标签
            for s, t, name in zip(orc_s, orc_T, orc_sorted['PointName']):
                # 为011和012使用特殊的标签位置避免重叠
                if name == 'ORC 011':
                    xytext = (-25, -15)  # 向左下偏移
                    ha = 'right'
                elif name == 'ORC 012':
                    xytext = (15, 15)   # 向右上偏移
                    ha = 'left'
                else:
                    xytext = (10, 10)    # 默认偏移
                    ha = 'left'

                ax.annotate(name, (s, t), xytext=xytext, textcoords='offset points',
                           fontsize=12, ha=ha, va='bottom', color='darkred',
                           fontweight='bold', bbox=dict(boxstyle='round,pad=0.4',
                           facecolor='white', alpha=0.9, edgecolor='red', linewidth=1.5),
                           zorder=6)

    # 绘制SCBC循环
    if not scbc_data.empty:
        scbc_sorted = analyze_and_sort_cycle_points(scbc_data, 'SCBC')
        if not scbc_sorted.empty:
            scbc_T = scbc_sorted['T_C_input'].values
            scbc_s = scbc_sorted['s_J_kgK_calc'].values / 1000  # 转换为kJ/kgK

            # 首尾相连：添加第一个点到末尾形成闭合循环
            scbc_T_closed = np.append(scbc_T, scbc_T[0])
            scbc_s_closed = np.append(scbc_s, scbc_s[0])

            # 绘制SCBC循环线条
            ax.plot(scbc_s_closed, scbc_T_closed, 's-', linewidth=3, markersize=10,
                    label='SCBC (CO2)', color='blue', alpha=0.8)

            # 添加状态点标签
            for s, t, name in zip(scbc_s, scbc_T, scbc_sorted['PointName']):
                ax.annotate(name, (s, t), xytext=(8, 8), textcoords='offset points',
                           fontsize=11, ha='left', va='bottom', color='darkblue',
                           fontweight='bold', bbox=dict(boxstyle='round,pad=0.3',
                           facecolor='white', alpha=0.8, edgecolor='blue'))
    
    # 设置坐标轴标签和标题
    ax.set_xlabel('比熵 s (kJ/kg·K)', fontsize=14, fontweight='bold')
    ax.set_ylabel('温度 T (°C)', fontsize=14, fontweight='bold')
    ax.set_title('ORC和SCBC循环的T-s图', fontsize=16, fontweight='bold', pad=20)
    
    # 添加网格
    ax.grid(True, alpha=0.3, linestyle='--')
    
    # 添加图例
    ax.legend(fontsize=12, loc='best', framealpha=0.9)
    
    # 设置坐标轴范围（根据数据自动调整）
    ax.margins(0.05)
    
    # 美化图表
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_linewidth(1.5)
    ax.spines['bottom'].set_linewidth(1.5)
    
    # 调整布局
    plt.tight_layout()
    
    # 保存图像
    try:
        plt.savefig(output_path, dpi=300, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        print(f"T-s图已保存到: {output_path}")
    except Exception as e:
        print(f"保存图像时出错: {e}")
    
    # 显示图像
    plt.show()

def main():
    """主函数"""
    print("=== ORC和SCBC循环T-s图绘制程序 ===")
    
    # 获取文件路径
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    
    # 输入文件路径
    csv_file_path = os.path.join(project_root, "output", "calculated_state_points_from_table10.csv")
    
    # 输出文件路径
    output_dir = os.path.join(project_root, "output")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "ts_diagram_orc_scbc.png")
    
    # 检查输入文件是否存在
    if not os.path.exists(csv_file_path):
        print(f"错误: 找不到数据文件 {csv_file_path}")
        print("请先运行 state_point_calculator.py 生成状态点数据")
        return
    
    # 加载数据
    df = load_state_points_data(csv_file_path)
    if df is None:
        return
    
    # 分离循环数据
    orc_data, scbc_data = separate_cycles(df)
    
    # 检查数据
    if orc_data.empty and scbc_data.empty:
        print("错误: 没有找到有效的循环数据")
        return
    
    # 绘制T-s图
    plot_ts_diagram(orc_data, scbc_data, output_path)
    
    print("=== 程序执行完成 ===")

if __name__ == "__main__":
    main()
